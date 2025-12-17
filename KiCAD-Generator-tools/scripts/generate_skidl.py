#!/usr/bin/env python3
"""
Generate SKiDL Python file from validated pin_model.json (Phase 3)

This creates a deterministic SKiDL script that can be executed to produce:
- Netlist (.net file)
- ERC report

Note: SKiDL does not natively generate schematics (.kicad_sch).
For schematic generation, use a separate tool or the existing generate_schematic.py

Usage:
    python generate_skidl.py              # Generate receiver.py
    python generate_skidl.py --run        # Generate and execute
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def generate_skidl_code(model: dict) -> str:
    """Generate SKiDL Python code from pin model."""

    parts = model.get('parts', [])
    nets = model.get('nets', [])
    meta = model.get('_meta', {})

    # Start building the code
    lines = []

    # Header
    lines.append('#!/usr/bin/env python3')
    lines.append('"""')
    lines.append('ESP32-S3 Radio Receiver - SKiDL Schematic')
    lines.append(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'From: {", ".join(meta.get("generated_from", []))}')
    lines.append('')
    lines.append('This file was auto-generated from pin_model.json')
    lines.append('Do not edit manually - regenerate from source YAML files')
    lines.append('"""')
    lines.append('')
    lines.append('from skidl import *')
    lines.append('')
    lines.append('# Set default tool to KiCad')
    lines.append('set_default_tool(KICAD8)')
    lines.append('')

    # Reset function
    lines.append('def create_schematic():')
    lines.append('    """Create the radio receiver schematic."""')
    lines.append('    ')
    lines.append('    # Reset SKiDL state')
    lines.append('    reset()')
    lines.append('    ')

    # Create nets
    lines.append('    # === Create Nets ===')
    for net_name in sorted(nets):
        # Sanitize net name for Python variable
        var_name = net_name.replace('+', 'P').replace('-', 'N').replace('.', '_')
        lines.append(f'    net_{var_name} = Net("{net_name}")')
    lines.append('    ')

    # Create a lookup for net variables
    lines.append('    # Net lookup')
    lines.append('    nets = {')
    for net_name in sorted(nets):
        var_name = net_name.replace('+', 'P').replace('-', 'N').replace('.', '_')
        lines.append(f'        "{net_name}": net_{var_name},')
    lines.append('    }')
    lines.append('    ')

    # Create parts
    lines.append('    # === Create Parts ===')
    lines.append('    parts = {}')
    lines.append('    ')

    for part in parts:
        ref = part.get('ref', 'X?')
        part_id = part.get('id', '')
        value = part.get('value', '')
        lcsc = part.get('lcsc', '')
        footprint = part.get('footprint', '').replace('JLCPCB:', '')
        belongs_to = part.get('belongs_to')

        # Comment with part info
        belongs_str = f" (belongs_to: {belongs_to})" if belongs_to else ""
        lines.append(f'    # {ref}: {value}{belongs_str}')

        # For JLCPCB parts, we'd use a custom library
        # For now, use generic parts with LCSC as reference
        lines.append(f'    parts["{part_id}"] = Part(')
        lines.append(f'        "Device", "R",  # Placeholder - replace with actual symbol')
        lines.append(f'        ref="{ref}",')
        lines.append(f'        value="{value}",')
        if footprint:
            lines.append(f'        footprint="{footprint}",')
        lines.append(f'        # LCSC: {lcsc}')
        lines.append(f'    )')
        lines.append('    ')

    # Connect pins
    lines.append('    # === Connect Pins ===')
    for part in parts:
        ref = part.get('ref', 'X?')
        part_id = part.get('id', '')
        pins = part.get('pins', {})

        if pins:
            lines.append(f'    # {ref} connections')
            for pin_name, net_name in pins.items():
                lines.append(f'    nets["{net_name}"] += parts["{part_id}"]["{pin_name}"]')
            lines.append('    ')

    # ERC and output
    lines.append('    # === Generate Output ===')
    lines.append('    ERC()')
    lines.append('    generate_netlist()')
    lines.append('    ')
    lines.append('    print("Netlist generated successfully")')
    lines.append('    ')
    lines.append('    return parts, nets')
    lines.append('')
    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    create_schematic()')
    lines.append('')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate SKiDL code from pin model')
    parser.add_argument('--run', action='store_true', help='Execute generated code')
    parser.add_argument('--output', default='receiver.py', help='Output filename')
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    model_file = script_dir / "work" / "pin_model.json"
    output_file = script_dir / "output" / args.output

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Reading: {model_file}")

    with open(model_file, 'r', encoding='utf-8') as f:
        model = json.load(f)

    code = generate_skidl_code(model)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"Generated: {output_file}")
    print(f"  Parts: {len(model.get('parts', []))}")
    print(f"  Nets: {len(model.get('nets', []))}")

    if args.run:
        print("\nExecuting generated code...")
        try:
            exec(compile(code, output_file, 'exec'))
        except ImportError:
            print("ERROR: SKiDL not installed. Install with: pip install skidl")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
