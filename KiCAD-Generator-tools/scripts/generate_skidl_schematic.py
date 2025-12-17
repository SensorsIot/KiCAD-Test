#!/usr/bin/env python3
"""
Generate KiCad 5 schematic using SKiDL's built-in schematic generator.

This script:
1. Loads pin_model.json (parts with pin-to-net mappings)
2. Creates SKiDL parts and connects them via nets
3. Uses SKiDL's gen_schematic() to create a .sch file with proper routing
"""

import json
import os
from pathlib import Path

# Set KiCad tool version before importing skidl
os.environ['KICAD_SYMBOL_DIR'] = ''

from skidl import *

# Use KiCad 5 for schematic generation (it's the only one with full support)
set_default_tool(KICAD5)


def load_pin_model(pin_model_path: Path) -> dict:
    """Load the pin model JSON file."""
    with open(pin_model_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_circuit_from_pin_model(model: dict, symbol_lib_path: Path) -> Circuit:
    """Create a SKiDL circuit from the pin model."""

    # Create a new circuit
    ckt = Circuit()

    # Add the symbol library
    lib_path = str(symbol_lib_path)
    lib = SchLib(lib_path, tool=KICAD5)

    parts_data = model.get('parts', [])

    # LCSC to symbol name mapping
    lcsc_to_symbol = {
        "C2913206": "ESP32-S3-MINI-1-N8",
        "C195417": "SI4735-D60-GU",
        "C7971": "TDA1306T",
        "C16581": "TP4056",
        "C6186": "AMS1117-3.3",
        "C7519": "USBLC6-2SC6",
        "C393939": "TYPE-C-31-M-12",
        "C131337": "S2B-PH-K-S",
        "C145819": "PJ-327A",
        "C124378": "Header-1x04",
        "C238128": "TestPoint",
        "C470747": "EC11E18244A5",
        "C127509": "TS-1102S",
        "C2761795": "WS2812B-B",
        "C32346": "Crystal-32.768kHz",
        "C23186": "R",
        "C22975": "R",
        "C25804": "R",
        "C25900": "R",
        "C22775": "R",
        "C45783": "C",
        "C134760": "C",
        "C15850": "C",
        "C15849": "C",
        "C14663": "C",
        "C1653": "C",
    }

    # Create parts
    skidl_parts = {}
    for part_data in parts_data:
        ref = part_data.get('ref', 'X?')
        value = part_data.get('value', '')
        lcsc = part_data.get('lcsc', '')
        footprint = part_data.get('footprint', '')
        pins = part_data.get('pins', {})

        # Get symbol name
        sym_name = lcsc_to_symbol.get(lcsc, value)

        try:
            # Create the part from the library
            part = Part(lib, sym_name, ref=ref, value=value, footprint=footprint, dest=TEMPLATE)
            part = part()  # Instantiate the template
            part.ref = ref
            skidl_parts[ref] = (part, pins)
            print(f"Created part: {ref} ({sym_name})")
        except Exception as e:
            print(f"Warning: Could not create part {ref} ({sym_name}): {e}")

    # Create nets and connect parts
    nets = {}
    for ref, (part, pin_mappings) in skidl_parts.items():
        for pin_name, net_name in pin_mappings.items():
            if not net_name:
                continue

            # Get or create net
            if net_name not in nets:
                nets[net_name] = Net(net_name)

            # Connect pin to net
            try:
                pin = part[pin_name]
                nets[net_name] += pin
            except Exception as e:
                print(f"Warning: Could not connect {ref}.{pin_name} to {net_name}: {e}")

    print(f"\nCreated {len(skidl_parts)} parts and {len(nets)} nets")
    return ckt


def main():
    base_dir = Path(__file__).parent.parent

    pin_model_path = base_dir / "work" / "pin_model.json"
    symbol_lib_path = base_dir / "output" / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"
    output_dir = base_dir / "output"

    print(f"Loading pin model from: {pin_model_path}")
    model = load_pin_model(pin_model_path)

    print(f"Creating circuit from pin model...")

    # Reset the default circuit
    default_circuit.reset()

    # Set library search path
    lib_search_paths[KICAD5].append(str(symbol_lib_path.parent))

    # Load parts and create connections
    parts_data = model.get('parts', [])

    # LCSC to symbol name mapping
    lcsc_to_symbol = {
        "C2913206": "ESP32-S3-MINI-1-N8",
        "C195417": "SI4735-D60-GU",
        "C7971": "TDA1306T",
        "C16581": "TP4056",
        "C6186": "AMS1117-3.3",
        "C7519": "USBLC6-2SC6",
        "C393939": "TYPE-C-31-M-12",
        "C131337": "S2B-PH-K-S",
        "C145819": "PJ-327A",
        "C124378": "Header-1x04",
        "C238128": "TestPoint",
        "C470747": "EC11E18244A5",
        "C127509": "TS-1102S",
        "C2761795": "WS2812B-B",
        "C32346": "Crystal-32.768kHz",
        "C23186": "R",
        "C22975": "R",
        "C25804": "R",
        "C25900": "R",
        "C22775": "R",
        "C45783": "C",
        "C134760": "C",
        "C15850": "C",
        "C15849": "C",
        "C14663": "C",
        "C1653": "C",
    }

    # Load the library
    lib_path = str(symbol_lib_path)
    print(f"Loading symbol library: {lib_path}")

    # Create parts
    skidl_parts = {}
    for part_data in parts_data:
        ref = part_data.get('ref', 'X?')
        value = part_data.get('value', '')
        lcsc = part_data.get('lcsc', '')
        footprint = part_data.get('footprint', '')
        pins = part_data.get('pins', {})

        # Get symbol name
        sym_name = lcsc_to_symbol.get(lcsc, value)

        try:
            # Create the part from the library
            part = Part(lib_path, sym_name, ref=ref, value=value, footprint=footprint)
            skidl_parts[ref] = (part, pins)
            print(f"Created part: {ref} ({sym_name})")
        except Exception as e:
            print(f"Warning: Could not create part {ref} ({sym_name}): {e}")

    # Create nets and connect parts
    nets = {}
    for ref, (part, pin_mappings) in skidl_parts.items():
        for pin_name, net_name in pin_mappings.items():
            if not net_name:
                continue

            # Get or create net
            if net_name not in nets:
                nets[net_name] = Net(net_name)

            # Connect pin to net
            try:
                pin = part[pin_name]
                nets[net_name] += pin
            except Exception as e:
                print(f"Warning: Could not connect {ref}.{pin_name} to {net_name}: {e}")

    print(f"\nCreated {len(skidl_parts)} parts and {len(nets)} nets")

    # Generate schematic
    print(f"\nGenerating schematic...")
    output_file = output_dir / "Debug"

    try:
        generate_schematic(
            filepath=str(output_dir),
            top_name="Debug",
            title="SKiDL Generated - ENC1 Debug",
            flatness=1.0,  # Flat schematic (no hierarchy)
            retries=3
        )
        print(f"\nSchematic generated: {output_file}.sch")
    except Exception as e:
        print(f"Error generating schematic: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
