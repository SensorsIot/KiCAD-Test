#!/usr/bin/env python3
"""
SKiDL to KiCad Schematic Generator

Traverses SKiDL's in-memory circuit objects and generates a modern
KiCad schematic (.kicad_sch) with symbols and net labels.

This bridges SKiDL (electrical truth) → KiCad (visual representation).

Usage:
    from skidl_to_kicad_sch import generate_kicad_schematic

    # After creating SKiDL circuit
    generate_kicad_schematic(
        default_circuit,
        symbol_lib_path="libs/JLCPCB/symbol/JLCPCB.kicad_sym",
        output_path="RadioReceiver.kicad_sch"
    )
"""

import re
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime


@dataclass
class SymbolPin:
    """Pin information from symbol library"""
    name: str
    number: str
    x: float
    y: float
    rotation: int  # 0=right, 90=up, 180=left, 270=down
    length: float


@dataclass
class SymbolDef:
    """Symbol definition from library"""
    name: str
    pins: Dict[str, SymbolPin]  # keyed by pin name
    bbox: Tuple[float, float, float, float]  # minx, miny, maxx, maxy


def parse_symbol_library(lib_path: Path) -> Dict[str, SymbolDef]:
    """Parse KiCad symbol library to extract pin positions."""

    symbols = {}
    content = lib_path.read_text()

    # Find all symbol definitions
    # Pattern: (symbol "NAME" ... ENDSYMBOL)
    symbol_pattern = re.compile(
        r'\(symbol\s+"([^"]+)"\s+\(in_bom[^)]+\)\s+\(on_board[^)]+\)(.*?)\n  \)',
        re.DOTALL
    )

    for match in symbol_pattern.finditer(content):
        sym_name = match.group(1)
        sym_content = match.group(2)

        pins = {}

        # Find pins: (pin TYPE STYLE (at X Y ROT) (length L) (name "NAME"...) (number "NUM"...))
        # Use non-greedy match to skip effects sections with nested parens
        pin_pattern = re.compile(
            r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s+\(length\s+([-\d.]+)\)\s+\(name\s+"([^"]+)".*?\(number\s+"([^"]+)"',
            re.DOTALL
        )

        for pin_match in pin_pattern.finditer(sym_content):
            x = float(pin_match.group(1))
            y = float(pin_match.group(2))
            rot = int(pin_match.group(3))
            length = float(pin_match.group(4))
            name = pin_match.group(5)
            number = pin_match.group(6)

            pins[name] = SymbolPin(
                name=name,
                number=number,
                x=x,
                y=y,
                rotation=rot,
                length=length
            )

        # Calculate bounding box from rectangle if present
        rect_pattern = re.compile(r'\(rectangle\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)')
        rect_match = rect_pattern.search(sym_content)
        if rect_match:
            x1, y1 = float(rect_match.group(1)), float(rect_match.group(2))
            x2, y2 = float(rect_match.group(3)), float(rect_match.group(4))
            bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        else:
            # Estimate from pins
            if pins:
                xs = [p.x for p in pins.values()]
                ys = [p.y for p in pins.values()]
                bbox = (min(xs) - 10, min(ys) - 10, max(xs) + 10, max(ys) + 10)
            else:
                bbox = (-10, -10, 10, 10)

        symbols[sym_name] = SymbolDef(name=sym_name, pins=pins, bbox=bbox)

    return symbols


def get_pin_endpoint(pin: SymbolPin, sym_x: float, sym_y: float) -> Tuple[float, float]:
    """Calculate the endpoint (connection point) of a pin in schematic coordinates.

    Pin position in symbol is where wire connects. Symbol Y is inverted in schematic.
    """
    # In KiCad schematic, Y increases downward, but symbol Y increases upward
    return (sym_x + pin.x, sym_y - pin.y)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_kicad_schematic(
    circuit,
    symbol_lib_path: Path,
    output_path: Path,
    title: str = "SKiDL Generated Schematic",
    lcsc_to_symbol: Dict[str, str] = None
):
    """
    Generate KiCad schematic from SKiDL circuit.

    Args:
        circuit: SKiDL circuit object (default_circuit)
        symbol_lib_path: Path to .kicad_sym library
        output_path: Output .kicad_sch file path
        title: Schematic title
        lcsc_to_symbol: Mapping from LCSC codes to symbol names
    """

    # Parse symbol library
    symbols = parse_symbol_library(symbol_lib_path)
    print(f"Loaded {len(symbols)} symbols from library")

    # Layout configuration
    start_x = 50.0
    start_y = 50.0
    x_spacing = 80.0
    y_spacing = 60.0
    cols = 5

    # Build schematic content
    lines = []

    # Header
    lines.append('(kicad_sch (version 20231120) (generator "skidl_to_kicad_sch")')
    lines.append(f'  (uuid "{generate_uuid()}")')
    lines.append('  (paper "A2")')
    lines.append('  (title_block')
    lines.append(f'    (title "{title}")')
    lines.append(f'    (date "{datetime.now().strftime("%Y-%m-%d")}")')
    lines.append('    (rev "1.0")')
    lines.append('    (comment 1 "Generated from SKiDL circuit")')
    lines.append('    (comment 2 "SKiDL owns electrical truth")')
    lines.append('  )')
    lines.append('')

    # Lib symbols section (empty - KiCad will populate from library)
    lines.append('  (lib_symbols')
    lines.append('  )')
    lines.append('')

    # Track net labels to add
    net_labels = []

    # Place symbols
    col = 0
    row = 0

    for part in circuit.parts:
        # Get symbol name
        sym_name = part.name
        if lcsc_to_symbol and hasattr(part, 'lcsc'):
            sym_name = lcsc_to_symbol.get(part.lcsc, sym_name)

        # Get symbol definition
        sym_def = symbols.get(sym_name)
        if not sym_def:
            print(f"Warning: Symbol '{sym_name}' not found in library, using placeholder")
            sym_def = SymbolDef(name=sym_name, pins={}, bbox=(-10, -10, 10, 10))

        # Calculate position
        x = start_x + col * x_spacing
        y = start_y + row * y_spacing

        # Symbol instance
        sym_uuid = generate_uuid()
        lib_name = "JLCPCB"

        lines.append(f'  (symbol (lib_id "{lib_name}:{sym_name}") (at {x:.2f} {y:.2f} 0)')
        lines.append(f'    (uuid "{sym_uuid}")')
        lines.append(f'    (property "Reference" "{part.ref}" (at {x:.2f} {y - 5:.2f} 0)')
        lines.append('      (effects (font (size 1.27 1.27))))')

        value = getattr(part, 'value', sym_name) or sym_name
        lines.append(f'    (property "Value" "{value}" (at {x:.2f} {y + 5:.2f} 0)')
        lines.append('      (effects (font (size 1.27 1.27))))')

        footprint = getattr(part, 'footprint', '') or ''
        lines.append(f'    (property "Footprint" "{footprint}" (at {x:.2f} {y + 7:.2f} 0)')
        lines.append('      (effects (font (size 1.27 1.27)) hide))')

        lcsc = getattr(part, 'lcsc', '') or ''
        lines.append(f'    (property "LCSC" "{lcsc}" (at {x:.2f} {y + 9:.2f} 0)')
        lines.append('      (effects (font (size 1.27 1.27)) hide))')

        lines.append(f'    (instances (project "RadioReceiver" (path "/" (reference "{part.ref}") (unit 1))))')
        lines.append('  )')

        # Add net labels for each connected pin
        for pin in part.pins:
            if pin.net and pin.net.name:
                net_name = pin.net.name

                # Find pin in symbol definition
                pin_def = sym_def.pins.get(pin.name)
                if pin_def:
                    # Calculate label position at pin endpoint
                    label_x, label_y = get_pin_endpoint(pin_def, x, y)

                    # Determine label rotation based on pin orientation
                    # Pin rotation: 0=right, 90=up, 180=left, 270=down
                    # Label should face outward from symbol
                    if pin_def.rotation == 0:
                        label_rot = 0
                        label_x -= 2  # Offset left of pin
                    elif pin_def.rotation == 180:
                        label_rot = 0
                        label_x += 2  # Offset right of pin
                    elif pin_def.rotation == 90:
                        label_rot = 90
                        label_y += 2
                    else:  # 270
                        label_rot = 90
                        label_y -= 2

                    net_labels.append((net_name, label_x, label_y, label_rot))
                else:
                    # Fallback: place label near symbol
                    net_labels.append((net_name, x + 20, y + row * 2.54, 0))

        # Move to next position
        col += 1
        if col >= cols:
            col = 0
            row += 1

    # Add net labels
    lines.append('')
    lines.append('  ; Net labels for connectivity')
    for net_name, lx, ly, rot in net_labels:
        justify = "left" if rot == 0 else "left"
        lines.append(f'  (label "{net_name}" (at {lx:.2f} {ly:.2f} {rot}) (fields_autoplaced yes)')
        lines.append(f'    (effects (font (size 1.27 1.27)) (justify {justify}))')
        lines.append(f'    (uuid "{generate_uuid()}"))')

    # Power symbols for common nets
    power_nets = {"+3V3", "GND", "VBAT", "VBUS"}
    for net in circuit.nets:
        if net.name in power_nets:
            # Add power port symbols
            pass  # Could add power symbols here

    # Footer
    lines.append('')
    lines.append('  (sheet_instances (path "/" (page "1")))')
    lines.append(')')

    # Write file
    output_path = Path(output_path)
    output_path.write_text('\n'.join(lines))
    print(f"Generated: {output_path}")
    print(f"  Parts: {len(circuit.parts)}")
    print(f"  Nets: {len(circuit.nets)}")
    print(f"  Labels: {len(net_labels)}")

    return output_path


if __name__ == "__main__":
    # Test with a simple circuit
    from skidl import *

    reset()
    set_default_tool(KICAD8)

    lib_path = Path(__file__).parent.parent / "output" / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"

    # Create test circuit
    gnd = Net("GND")
    vcc = Net("+3V3")

    # Would need actual parts here
    print(f"Library path: {lib_path}")
    print(f"Exists: {lib_path.exists()}")

    if lib_path.exists():
        symbols = parse_symbol_library(lib_path)
        print(f"Found {len(symbols)} symbols:")
        for name in symbols:
            print(f"  - {name}: {len(symbols[name].pins)} pins")
