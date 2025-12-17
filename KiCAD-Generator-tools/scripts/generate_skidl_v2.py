#!/usr/bin/env python3
"""
Generate working SKiDL Python file from validated pin_model.json

This is the AUTHORITATIVE source of electrical truth.
SKiDL owns: Parts, Nets, Power, ERC
KiCad owns: Symbol placement, Wire layout, Notes, Sheet structure

Workflow:
    pin_model.json → generate_skidl_v2.py → receiver.py → [netlist + schematic]
"""

import json
from pathlib import Path
from datetime import datetime


# LCSC part number to symbol name mapping
# Maps LCSC codes to our custom symbol library names
LCSC_TO_SYMBOL = {
    # ICs
    "C2913206": "ESP32-S3-MINI-1-N8",
    "C195417": "SI4735-D60-GU",
    "C7971": "TDA1306T",
    "C16581": "TP4056",
    "C6186": "AMS1117-3.3",
    "C7519": "USBLC6-2SC6",
    # Connectors
    "C393939": "TYPE-C-31-M-12",
    "C131337": "S2B-PH-K-S",
    "C145819": "PJ-327A",
    "C124378": "Header-1x04",
    "C238128": "TestPoint",
    # UI components
    "C470747": "EC11E18244A5",
    "C127509": "TS-1102S",
    "C2761795": "WS2812B-B",
    # Passive components
    "C32346": "Crystal-32.768kHz",
    # Resistors - all map to generic "R" symbol
    "C23186": "R",   # 5.1k
    "C22975": "R",   # 2k
    "C25804": "R",   # 10k
    "C25900": "R",   # 4.7k
    "C22775": "R",   # 100R
    # Capacitors - all map to generic "C" symbol
    "C45783": "C",   # 22uF
    "C134760": "C",  # 220uF
    "C15850": "C",   # 10uF
    "C15849": "C",   # 1uF
    "C14663": "C",   # 100nF
    "C1653": "C",    # 22pF
}


def generate_skidl_code(model: dict) -> str:
    """Generate authoritative SKiDL Python code from pin model.

    Args:
        model: The pin_model.json data

    The generated code uses KiCad 7 format and JLCPCB library symbols.
    Requires: JLCPCB symbol library installed in KiCad.
    """

    parts = model.get('parts', [])
    nets = model.get('nets', [])
    meta = model.get('_meta', {})

    lines = []

    # Header
    lines.append('#!/usr/bin/env python3')
    lines.append('"""')
    lines.append('ESP32-S3 Radio Receiver - SKiDL Circuit Definition')
    lines.append(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('')
    lines.append('THIS IS THE AUTHORITATIVE SOURCE OF ELECTRICAL TRUTH.')
    lines.append('')
    lines.append('SKiDL owns: Parts, Nets, Power, ERC')
    lines.append('KiCad owns: Symbol placement, Wire layout, Notes')
    lines.append('')
    lines.append('Do NOT edit electrical connections in KiCad.')
    lines.append('All changes must be made here and regenerated.')
    lines.append('"""')
    lines.append('')
    lines.append('import sys')
    lines.append('from pathlib import Path')
    lines.append('from skidl import *')
    lines.append('')
    lines.append('# Use KiCad 8 format for netlist and ERC')
    lines.append('set_default_tool(KICAD8)')
    lines.append('')
    lines.append('# Import our custom schematic generator')
    lines.append('sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))')
    lines.append('from skidl_to_kicad_sch import generate_kicad_schematic')
    lines.append('')
    lines.append('# Project configuration')
    lines.append('PROJECT_NAME = "RadioReceiver"')
    lines.append(f'TOTAL_PARTS = {len(parts)}')
    lines.append(f'TOTAL_NETS = {len(nets)}')
    lines.append('')

    # Add LCSC to symbol mapping
    lines.append('# LCSC part number to symbol name mapping')
    lines.append('LCSC_TO_SYMBOL = {')
    for lcsc, sym in LCSC_TO_SYMBOL.items():
        lines.append(f'    "{lcsc}": "{sym}",')
    lines.append('}')
    lines.append('')

    lines.append('')
    lines.append('def create_circuit():')
    lines.append('    """')
    lines.append('    Create the radio receiver circuit.')
    lines.append('    ')
    lines.append('    Returns:')
    lines.append('        tuple: (parts_dict, nets_dict) for inspection')
    lines.append('    """')
    lines.append('    ')
    lines.append('    reset()')
    lines.append('    ')

    # Create nets
    lines.append('    # ========== NETS ==========')
    lines.append('    # All nets are defined here. This is the single source of truth.')
    lines.append('    ')
    net_vars = {}
    for net_name in sorted(nets):
        var_name = 'net_' + net_name.replace('+', 'P').replace('-', 'N').replace('.', '_')
        net_vars[net_name] = var_name
        lines.append(f'    {var_name} = Net("{net_name}")')
    lines.append('    ')

    # Create parts
    lines.append('    # ========== PARTS ==========')
    lines.append('    # All parts are defined here. Do not add parts in KiCad.')
    lines.append('    ')

    for part in parts:
        ref = part.get('ref', 'X?')
        part_id = part.get('id', '')
        value = part.get('value', '')
        lcsc = part.get('lcsc', '')
        symbol = part.get('symbol', '')
        footprint = part.get('footprint', '').replace('JLCPCB:', '')
        pins = part.get('pins', {})
        belongs_to = part.get('belongs_to')

        pin_names = list(pins.keys())

        if not pin_names:
            lines.append(f'    # {ref} ({part_id}): No pins connected - skipping')
            continue

        # Comment with part info
        belongs_str = f" [belongs_to: {belongs_to}]" if belongs_to else ""
        lines.append(f'    # {ref}: {value} (LCSC: {lcsc}){belongs_str}')

        # Use JLCPCB library symbol (required for schematic generation)
        # Symbol name comes from mapping (JLC2KiCadLib uses part names, not LCSC numbers)
        lib_name = "JLCPCB"
        sym_name = LCSC_TO_SYMBOL.get(lcsc, value.replace(' ', '_'))

        lines.append(f'    {part_id} = Part("{lib_name}", "{sym_name}",')
        lines.append(f'        ref="{ref}",')
        lines.append(f'        value="{value}",')
        if footprint:
            lines.append(f'        footprint="{footprint}",')
        lines.append(f'    )')
        lines.append('    ')

    # Connect pins to nets
    lines.append('    # ========== CONNECTIONS ==========')
    lines.append('    # All electrical connections. Do NOT modify in KiCad.')
    lines.append('    ')

    for part in parts:
        part_id = part.get('id', '')
        ref = part.get('ref', '')
        pins = part.get('pins', {})

        if not pins:
            continue

        lines.append(f'    # {ref}')
        for pin_name, net_name in pins.items():
            net_var = net_vars.get(net_name, 'NC')
            lines.append(f'    {net_var} += {part_id}["{pin_name}"]')
        lines.append('    ')

    # Return parts and nets for inspection
    lines.append('    # Return for inspection')
    lines.append('    return {')
    for part in parts:
        part_id = part.get('id', '')
        ref = part.get('ref', '')
        if part.get('pins'):
            lines.append(f'        "{ref}": {part_id},')
    lines.append('    }, {')
    for net_name in sorted(nets):
        var_name = net_vars[net_name]
        lines.append(f'        "{net_name}": {var_name},')
    lines.append('    }')
    lines.append('')
    lines.append('')

    # Generate output function
    lines.append('def generate_outputs(output_dir: Path = None):')
    lines.append('    """')
    lines.append('    Generate all outputs from the circuit.')
    lines.append('    ')
    lines.append('    This is the ONLY way to create/update the schematic.')
    lines.append('    Do not edit the schematic directly in KiCad.')
    lines.append('    """')
    lines.append('    ')
    lines.append('    if output_dir is None:')
    lines.append('        output_dir = Path(__file__).parent')
    lines.append('    ')
    lines.append('    print(f"Creating circuit with {TOTAL_PARTS} parts and {TOTAL_NETS} nets...")')
    lines.append('    parts, nets = create_circuit()')
    lines.append('    ')
    lines.append('    # Run ERC')
    lines.append('    print("Running Electrical Rules Check...")')
    lines.append('    ERC()')
    lines.append('    ')
    lines.append('    # Generate netlist (always)')
    lines.append('    netlist_file = output_dir / f"{PROJECT_NAME}.net"')
    lines.append('    generate_netlist(file_=str(netlist_file))')
    lines.append('    print(f"Generated: {netlist_file}")')
    lines.append('    ')
    lines.append('    # Generate schematic using our custom generator')
    lines.append('    # This traverses SKiDL circuit objects and creates KiCad 9 format')
    lines.append('    sch_file = output_dir / f"{PROJECT_NAME}.kicad_sch"')
    lines.append('    lib_path = output_dir / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"')
    lines.append('    generate_kicad_schematic(')
    lines.append('        default_circuit,')
    lines.append('        symbol_lib_path=lib_path,')
    lines.append('        output_path=sch_file,')
    lines.append('        title="ESP32-S3 Portable Radio Receiver",')
    lines.append('        lcsc_to_symbol=LCSC_TO_SYMBOL')
    lines.append('    )')
    lines.append('    ')
    lines.append('    print()')
    lines.append('    print("=" * 60)')
    lines.append('    print("IMPORTANT: SKiDL owns electrical truth.")')
    lines.append('    print("In KiCad you may ONLY:")')
    lines.append('    print("  - Move symbols")')
    lines.append('    print("  - Route wires")')
    lines.append('    print("  - Add notes and frames")')
    lines.append('    print("You may NOT:")')
    lines.append('    print("  - Add/delete components")')
    lines.append('    print("  - Change pin connections")')
    lines.append('    print("  - Rename nets")')
    lines.append('    print("=" * 60)')
    lines.append('    ')
    lines.append('    return True')
    lines.append('')
    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    generate_outputs()')
    lines.append('')

    return '\n'.join(lines)


def main():
    script_dir = Path(__file__).parent.parent
    model_file = script_dir / "work" / "pin_model.json"
    output_file = script_dir / "output" / "receiver_v2.py"

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


if __name__ == "__main__":
    main()
