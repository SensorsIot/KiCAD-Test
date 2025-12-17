#!/usr/bin/env python3
"""
Generate KiCAD Project from pin_model.json

Creates a complete KiCAD project with:
- .kicad_pro (project file)
- .kicad_sch (schematic with parts and net labels)
- .kicad_pcb (empty PCB)
- sym-lib-table / fp-lib-table (library references)

Parts are placed in a grid layout with net labels on each pin.
Symbol references use JLCPCB:LCSC_CODE format for later library linking.
"""

import json
import uuid
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


def generate_uuid():
    return str(uuid.uuid4())


def generate_project_file(project_name: str) -> str:
    """Generate KiCAD project file content."""
    return f'''{{
  "board": {{
    "3dviewports": [],
    "design_settings": {{}},
    "ipc2581": {{}},
    "layer_presets": [],
    "viewports": []
  }},
  "meta": {{
    "filename": "{project_name}.kicad_pro",
    "version": 1
  }},
  "sheets": [
    ["", ""]
  ]
}}'''


def generate_pcb_file(project_name: str) -> str:
    """Generate empty KiCAD PCB file."""
    return f'''(kicad_pcb
  (version 20240108)
  (generator "python_generator")
  (generator_version "9.0")
  (general (thickness 1.6) (legacy_teardrops no))
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )
  (setup (pad_to_mask_clearance 0))
  (net 0 "")
)'''


def generate_sym_lib_table() -> str:
    """Generate symbol library table with portable paths."""
    return '''(sym_lib_table
  (version 7)
  (lib (name "JLCPCB")(type "KiCad")(uri "${KIPRJMOD}/libs/JLCPCB/symbol/JLCPCB.kicad_sym")(options "")(descr "JLCPCB parts"))
)'''


def generate_fp_lib_table() -> str:
    """Generate footprint library table with portable paths."""
    return '''(fp_lib_table
  (version 7)
  (lib (name "JLCPCB")(type "KiCad")(uri "${KIPRJMOD}/libs/JLCPCB/JLCPCB")(options "")(descr "JLCPCB footprints"))
)'''


def get_symbol_category(ref: str) -> str:
    """Determine symbol category from reference designator."""
    prefix = ''.join(c for c in ref if c.isalpha())
    categories = {
        'U': 'ic',
        'R': 'resistor',
        'C': 'capacitor',
        'D': 'led',
        'J': 'connector',
        'SW': 'switch',
        'ENC': 'encoder',
        'Y': 'crystal',
        'TP': 'testpoint',
    }
    return categories.get(prefix, 'generic')


def generate_symbol_instance(designator: str, lib_id: str, footprint: str,
                            value: str, lcsc: str, x: float, y: float,
                            project_name: str) -> str:
    """Generate a KiCAD symbol instance."""
    sym_uuid = generate_uuid()

    return f'''  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0)
    (uuid "{sym_uuid}")
    (property "Reference" "{designator}" (at {x:.2f} {y - 5:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{value}" (at {x:.2f} {y + 5:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "{footprint}" (at {x:.2f} {y + 7:.2f} 0)
      (effects (font (size 1.27 1.27)) hide))
    (property "LCSC" "{lcsc}" (at {x:.2f} {y + 9:.2f} 0)
      (effects (font (size 1.27 1.27)) hide))
    (instances (project "{project_name}" (path "/" (reference "{designator}") (unit 1))))
  )
'''


def generate_net_label(net_name: str, x: float, y: float, rotation: int = 0) -> str:
    """Generate a net label."""
    justify = "left" if rotation == 0 else "right"
    return f'''  (label "{net_name}" (at {x:.2f} {y:.2f} {rotation}) (fields_autoplaced yes)
    (effects (font (size 1.27 1.27)) (justify {justify}))
    (uuid "{generate_uuid()}"))
'''


def sort_parts_key(part: dict):
    """Sort key for parts - ICs first, then connectors, then passives."""
    ref = part.get('ref', 'X?')
    prefix = ''.join(c for c in ref if c.isalpha())
    num = ''.join(c for c in ref if c.isdigit())
    order = {'U': 0, 'J': 1, 'SW': 2, 'ENC': 3, 'D': 4, 'Y': 5, 'TP': 6, 'R': 7, 'C': 8}
    return (order.get(prefix, 99), int(num) if num else 0)


def generate_schematic(model: dict, project_name: str) -> str:
    """Generate KiCAD schematic from pin model."""

    parts = model.get('parts', [])

    # Header
    content = f'''(kicad_sch (version 20231120) (generator "python_generator")
  (uuid "{generate_uuid()}")
  (paper "A2")
  (title_block
    (title "ESP32-S3 Portable Radio Receiver")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (rev "1.0")
    (comment 1 "Generated from pin_model.json via LLM pipeline")
  )
  (lib_symbols)

'''

    # Layout configuration
    start_x = 50
    start_y = 50
    x_spacing = 80
    y_spacing = 50
    cols = 5

    col = 0
    row = 0

    # Sort parts by category
    sorted_parts = sorted(parts, key=sort_parts_key)

    symbols_content = ""
    labels_content = ""

    for part in sorted_parts:
        ref = part.get('ref', 'X?')
        lcsc = part.get('lcsc', '')
        value = part.get('value', '')
        footprint = part.get('footprint', '')
        pins = part.get('pins', {})

        # Build lib_id using LCSC to symbol mapping
        # This ensures lib_ids match our custom symbol library
        if lcsc and lcsc in LCSC_TO_SYMBOL:
            lib_id = f"JLCPCB:{LCSC_TO_SYMBOL[lcsc]}"
        elif lcsc:
            lib_id = f"JLCPCB:{lcsc}"
        else:
            lib_id = f"JLCPCB:{ref}"

        # Calculate position
        x = start_x + col * x_spacing
        y = start_y + row * y_spacing

        # Generate symbol
        symbols_content += generate_symbol_instance(
            ref, lib_id, footprint, value, lcsc, x, y, project_name
        )

        # Generate net labels for each pin
        pin_offset_y = 0
        for pin_name, net_name in pins.items():
            label_x = x + 30  # Labels to the right of symbol
            label_y = y + pin_offset_y
            labels_content += generate_net_label(net_name, label_x, label_y, 0)
            pin_offset_y += 2.54  # Standard KiCAD pin spacing

        # Move to next grid position
        col += 1
        if col >= cols:
            col = 0
            row += 1

    content += symbols_content
    content += labels_content

    # Footer
    content += '''
  (sheet_instances (path "/" (page "1")))
)
'''

    return content


def main():
    script_dir = Path(__file__).parent.parent
    model_file = script_dir / "work" / "pin_model.json"
    output_dir = script_dir / "output"

    project_name = "RadioReceiver"

    print(f"KiCAD Project Generator")
    print("=" * 60)

    # Load pin model
    print(f"\nLoading: {model_file}")
    with open(model_file, 'r', encoding='utf-8') as f:
        model = json.load(f)

    stats = model.get('statistics', {})
    print(f"  Parts: {stats.get('total_parts', 0)}")
    print(f"  Nets: {stats.get('total_nets', 0)}")
    print(f"  Pin assignments: {stats.get('total_pin_assignments', 0)}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate project files
    print(f"\nGenerating KiCAD project files in: {output_dir}")

    # Project file
    pro_file = output_dir / f"{project_name}.kicad_pro"
    pro_file.write_text(generate_project_file(project_name), encoding='utf-8')
    print(f"  {pro_file.name}")

    # Schematic file
    sch_file = output_dir / f"{project_name}.kicad_sch"
    sch_content = generate_schematic(model, project_name)
    sch_file.write_text(sch_content, encoding='utf-8')
    print(f"  {sch_file.name}")

    # PCB file
    pcb_file = output_dir / f"{project_name}.kicad_pcb"
    pcb_file.write_text(generate_pcb_file(project_name), encoding='utf-8')
    print(f"  {pcb_file.name}")

    # Library tables
    sym_table = output_dir / "sym-lib-table"
    sym_table.write_text(generate_sym_lib_table(), encoding='utf-8')
    print(f"  {sym_table.name}")

    fp_table = output_dir / "fp-lib-table"
    fp_table.write_text(generate_fp_lib_table(), encoding='utf-8')
    print(f"  {fp_table.name}")

    print(f"\n" + "=" * 60)
    print("SUCCESS!")
    print(f"\nTo complete setup:")
    print(f"  1. Copy the project folder to Windows where KiCAD is installed")
    print(f"  2. Run download_jlcpcb_libs.py to fetch symbol/footprint libraries")
    print(f"  3. Copy libraries to: {output_dir}/libs/JLCPCB/")
    print(f"  4. Open {project_name}.kicad_pro in KiCAD")
    print(f"  5. Run: Tools > Update Schematic from Symbol Libraries")
    print("=" * 60)


if __name__ == "__main__":
    main()
