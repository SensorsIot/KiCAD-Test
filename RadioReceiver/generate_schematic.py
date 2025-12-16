#!/usr/bin/env python3
"""
Generate KiCAD schematic with net labels on every pin.

Usage:
    python generate_schematic.py

Input:
    parts_with_netlabels.json - Parts with net labels per pin

Output:
    RadioReceiver.kicad_pro - KiCAD project file
    RadioReceiver.kicad_sch - Main schematic with all components and labels
    sym-lib-table - Project symbol library reference
    fp-lib-table - Project footprint library reference
"""
import json
import re
import uuid
import os
import yaml
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PARTS_JSON = SCRIPT_DIR / "parts_with_netlabels.json"
CUSTOM_OVERRIDES = SCRIPT_DIR / "custom_library_overrides.yaml"
KICAD_USER_DIR = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "KiCad"
SYMBOL_LIB = KICAD_USER_DIR / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"

# Output files
PROJECT_NAME = "RadioReceiver"
OUTPUT_SCH = SCRIPT_DIR / f"{PROJECT_NAME}.kicad_sch"
OUTPUT_PRO = SCRIPT_DIR / f"{PROJECT_NAME}.kicad_pro"
OUTPUT_PCB = SCRIPT_DIR / f"{PROJECT_NAME}.kicad_pcb"
SYM_LIB_TABLE = SCRIPT_DIR / "sym-lib-table"
FP_LIB_TABLE = SCRIPT_DIR / "fp-lib-table"

# Symbol/footprint maps are populated at runtime from overrides and part data
LCSC_TO_SYMBOL = {}
LCSC_TO_FOOTPRINT = {}


def generate_uuid():
    return str(uuid.uuid4())


def load_overrides(path: Path) -> dict:
    """Load custom overrides for symbol/footprint mappings."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_symbol_pins(symbol_lib_path):
    """Parse symbol library to get pin positions for each symbol."""
    if not symbol_lib_path.exists():
        raise FileNotFoundError(
            f"Symbol library not found at {symbol_lib_path}. "
            "Ask the LLM to run download_jlcpcb_libs.py to fetch libraries or point SYMBOL_LIB to the correct path."
        )

    content = symbol_lib_path.read_text(encoding='utf-8')
    symbols = {}

    # Split by top-level symbols
    parts = re.split(r'(?=\(symbol "[^"]+"\s+\(in_bom)', content)

    for part in parts:
        if '(in_bom' not in part:
            continue

        # Get symbol name
        match = re.match(r'\(symbol "([^"]+)"', part)
        if not match:
            continue
        symbol_name = match.group(1)

        # Find each pin block
        pin_blocks = re.findall(
            r'\(pin\s+\w+\s+\w+\s*\(at[^)]+\).*?\(number\s+"[^"]+"\s*\([^)]+\)\s*\)',
            part, re.DOTALL
        )

        pins = []
        for pin_block in pin_blocks:
            at_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)', pin_block)
            name_match = re.search(r'\(name\s+"([^"]+)"', pin_block)
            num_match = re.search(r'\(number\s+"([^"]+)"', pin_block)

            if at_match and name_match and num_match:
                pins.append({
                    'number': num_match.group(1),
                    'name': name_match.group(1),
                    'x': float(at_match.group(1)),
                    'y': float(at_match.group(2)),
                    'rotation': int(at_match.group(3))
                })

        if pins:
            symbols[symbol_name] = pins

    return symbols


def get_label_position(pin_x, pin_y, pin_rotation):
    """Calculate label position and rotation based on pin direction."""
    offset = 2.0

    if pin_rotation == 0:      # LEFT pins
        return -offset, 0, 180, "right"
    elif pin_rotation == 180:  # RIGHT pins
        return offset, 0, 0, "left"
    elif pin_rotation == 90:   # BOTTOM pins
        return 0, offset, 270, "right"
    elif pin_rotation == 270:  # TOP pins
        return 0, -offset, 270, "left"
    else:
        return 0, 0, 0, "left"


def generate_symbol(designator, lib_id, footprint, x, y, lcsc=""):
    """Generate a KiCAD symbol."""
    sym_uuid = generate_uuid()

    return f'''  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0)
    (uuid "{sym_uuid}")
    (property "Reference" "{designator}" (at {x:.2f} {y - 10:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "" (at {x:.2f} {y + 10:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "{footprint}" (at {x:.2f} {y + 12:.2f} 0)
      (effects (font (size 1.27 1.27)) hide))
    (property "LCSC" "{lcsc}" (at {x:.2f} {y + 14:.2f} 0)
      (effects (font (size 1.27 1.27)) hide))
    (instances (project "{PROJECT_NAME}" (path "/" (reference "{designator}") (unit 1))))
  )
'''


def generate_label(net_label, x, y, rotation=0, justify="left"):
    """Generate a net label."""
    return f'''  (label "{net_label}" (at {x:.2f} {y:.2f} {rotation}) (fields_autoplaced yes)
    (effects (font (size 1.27 1.27)) (justify {justify}))
    (uuid "{generate_uuid()}"))
'''


def generate_project_file():
    """Generate KiCAD project file."""
    content = '''{
  "board": {
    "3dviewports": [],
    "design_settings": {},
    "ipc2581": {},
    "layer_presets": [],
    "viewports": []
  },
  "meta": {
    "filename": "''' + PROJECT_NAME + '''.kicad_pro",
    "version": 1
  },
  "sheets": [
    ["", ""]
  ]
}'''
    OUTPUT_PRO.write_text(content)


def generate_pcb_file():
    """Generate empty PCB file."""
    content = f'''(kicad_pcb
  (version 20240108)
  (generator "pcbnew")
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
    (50 "User.1" user)
    (51 "User.2" user)
  )
  (setup (pad_to_mask_clearance 0))
  (net 0 "")
)'''
    OUTPUT_PCB.write_text(content, encoding='utf-8')


def generate_lib_tables():
    """Generate project-specific library tables."""
    jlcpcb_sym = KICAD_USER_DIR / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"
    jlcpcb_fp = KICAD_USER_DIR / "JLCPCB" / "JLCPCB"

    sym_path = str(jlcpcb_sym).replace("\\", "/")
    fp_path = str(jlcpcb_fp).replace("\\", "/")

    sym_table = f'''(sym_lib_table
  (version 7)
  (lib (name "JLCPCB")(type "KiCad")(uri "{sym_path}")(options "")(descr "JLCPCB parts"))
)'''

    fp_table = f'''(fp_lib_table
  (version 7)
  (lib (name "JLCPCB")(type "KiCad")(uri "{fp_path}")(options "")(descr "JLCPCB footprints"))
)'''

    SYM_LIB_TABLE.write_text(sym_table, encoding='utf-8')
    FP_LIB_TABLE.write_text(fp_table, encoding='utf-8')


def generate_schematic(parts_data, symbol_pins, overrides):
    """Generate complete schematic."""

    # Header
    content = f'''(kicad_sch (version 20231120) (generator "python_generator")
  (uuid "{generate_uuid()}")
  (paper "A2")
  (title_block
    (title "ESP32-S3 Portable Radio Receiver")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (rev "1.0")
    (comment 1 "Generated from FSD with net labels")
  )
  (lib_symbols)

'''

    # Layout settings
    start_x = 50
    start_y = 50
    x_spacing = 80
    y_spacing = 60
    cols = 5

    col = 0
    row = 0

    # Sort by designator
    def sort_key(item):
        des = item[0]
        prefix = ''.join(c for c in des if c.isalpha())
        num = ''.join(c for c in des if c.isdigit())
        order = {'U': 0, 'J': 1, 'SW': 2, 'ENC': 3, 'D': 4, 'Y': 5, 'R': 6, 'C': 7}
        return (order.get(prefix, 99), int(num) if num else 0)

    sorted_parts = sorted(parts_data.items(), key=sort_key)

    total_labels = 0

    for designator, part_info in sorted_parts:
        lcsc = part_info.get("lcsc", "")
        symbol_name = part_info.get("symbol", "")
        override = overrides.get(lcsc, {}) if overrides else {}

        # Determine lib_id (symbol)
        if override.get("symbol_lib_id"):
            lib_id = override["symbol_lib_id"]
        elif symbol_name:
            lib_id = symbol_name if ":" in symbol_name else f"JLCPCB:{symbol_name}"
        else:
            raise ValueError(
                f"No symbol mapping for {designator} (LCSC={lcsc}). "
                "Ask the LLM to add symbol_lib_id to custom_library_overrides.yaml or ensure parts_with_netlabels.json includes 'symbol'."
            )

        # Determine footprint
        if override.get("footprint_lib_id"):
            footprint = override["footprint_lib_id"]
        else:
            footprint = part_info.get("footprint", "")
            if not footprint:
                print(
                    f"WARNING: No footprint mapping for {designator} (LCSC={lcsc}). "
                    "Ask the LLM to add footprint_lib_id to custom_library_overrides.yaml."
                )
                footprint = ""

        # Position
        x = start_x + col * x_spacing
        y = start_y + row * y_spacing

        # Generate symbol
        content += generate_symbol(designator, lib_id, footprint, x, y, lcsc)

        # Get pin positions from symbol library
        symbol_lookup = symbol_name or (override.get("symbol_lib_id", "").split(":")[-1] if override.get("symbol_lib_id") else "")
        sym_pins = symbol_pins.get(symbol_lookup, [])
        pin_positions = {p['number']: p for p in sym_pins}

        # Generate labels
        pins = part_info.get("pins", {})
        for pin_num, pin_data in pins.items():
            net_label = pin_data.get("net_label", f"{designator}_{pin_num}")

            if pin_num in pin_positions:
                pin_info = pin_positions[pin_num]
                x_off, y_off, label_rot, justify = get_label_position(
                    pin_info['x'], pin_info['y'], pin_info['rotation']
                )
                label_x = x + pin_info['x'] + x_off
                label_y = y - pin_info['y'] + y_off  # Y inverted
            else:
                # Fallback
                label_x = x + 25
                label_y = y + list(pins.keys()).index(pin_num) * 3
                label_rot = 0
                justify = "left"

            content += generate_label(net_label, label_x, label_y, label_rot, justify)
            total_labels += 1

        # Next position
        col += 1
        if col >= cols:
            col = 0
            row += 1

    # Footer
    content += '''
  (sheet_instances (path "/" (page "1")))
)
'''

    OUTPUT_SCH.write_text(content, encoding='utf-8')
    return len(sorted_parts), total_labels


def main():
    print("KiCAD Schematic Generator")
    print("=" * 60)

    if not PARTS_JSON.exists():
        raise FileNotFoundError(
            f"{PARTS_JSON} not found. "
            "Ask the LLM to run map_connections.py after completing selections and pin parsing."
        )

    # Load parts data
    print(f"\nLoading parts from: {PARTS_JSON.name}")
    with open(PARTS_JSON, encoding='utf-8') as f:
        parts_data = json.load(f)
    print(f"  Loaded {len(parts_data)} parts")

    overrides = load_overrides(CUSTOM_OVERRIDES)
    if overrides:
        print(f"  Loaded overrides: {len(overrides)} entries from {CUSTOM_OVERRIDES.name}")
    else:
        print(f"  No overrides loaded (optional): {CUSTOM_OVERRIDES.name} not found or empty")

    # Parse symbol library
    print(f"\nParsing symbol library: {SYMBOL_LIB.name}")
    symbol_pins = parse_symbol_pins(SYMBOL_LIB)
    if not symbol_pins:
        raise ValueError(
            "No symbols parsed from the JLCPCB library. "
            "Ask the LLM to verify the downloaded library or rerun download_jlcpcb_libs.py and parse_library_pins.py."
        )
    print(f"  Found {len(symbol_pins)} symbols")

    # Generate project files
    print("\nGenerating project files...")
    generate_project_file()
    print(f"  {OUTPUT_PRO.name}")

    generate_pcb_file()
    print(f"  {OUTPUT_PCB.name}")

    generate_lib_tables()
    print(f"  {SYM_LIB_TABLE.name}")
    print(f"  {FP_LIB_TABLE.name}")

    # Generate schematic
    print(f"\nGenerating schematic: {OUTPUT_SCH.name}")
    # Warn for parts without symbol mapping
    unmapped = [
        des for des, info in parts_data.items()
        if not LCSC_TO_SYMBOL.get(info.get("lcsc", ""), info.get("symbol", ""))
    ]
    if unmapped:
        print(f"Warning: {len(unmapped)} parts have no symbol mapping; using fallbacks: {unmapped}")
        print("Ask the LLM to update LCSC_TO_SYMBOL or ensure map_connections generated symbol names.")

    num_parts, num_labels = generate_schematic(parts_data, symbol_pins, overrides)

    print(f"\n" + "=" * 60)
    print(f"SUCCESS!")
    print(f"  - {num_parts} components")
    print(f"  - {num_labels} net labels")
    print(f"\nOpen in KiCAD:")
    print(f"  1. File > Open Project > {OUTPUT_PRO}")
    print(f"  2. Tools > Update Schematic from Symbol Libraries")
    print("=" * 60)


if __name__ == "__main__":
    main()
