#!/usr/bin/env python3
"""
KiCAD 9 Schematic Generator

Generates KiCAD 9 schematic files from jlc_parts_enriched.json
Creates hierarchical structure with Radio and Main sheets.

Usage:
    python generate_schematic.py
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Configuration
PARTS_JSON = Path(__file__).parent.parent / "jlcpcb_parts_pipeline" / "jlc_parts_enriched.json"
OUTPUT_DIR = Path(__file__).parent
PROJECT_NAME = "Version2"

# Components for Radio sheet
RADIO_DESIGNATORS = {
    "U4",      # SI4735
    "Y1",      # Crystal
    "J3",      # Audio jack
    "C12",     # SI4735 VDD bypass
    "C13",     # Crystal cap
    "C14",     # Crystal cap
    "C15",     # SI4735 VA bypass
    "C16",     # SI4735 VD bypass
    "R7",      # Audio resistor L
    "R8",      # Audio resistor R
}


def generate_uuid():
    """Generate a KiCAD-compatible UUID."""
    return str(uuid.uuid4())


def load_parts():
    """Load parts from JSON file."""
    with open(PARTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["parts"]


def generate_symbol(part, x, y, rotation=0):
    """Generate a KiCAD symbol S-expression for a part."""
    symbol_lib = part.get("symbol", "Device:R")
    designator = part["designator"]
    value = part.get("value") or part.get("query") or designator
    footprint = part.get("footprint", "")
    lcsc = part.get("selection", {}).get("lcsc") or part.get("known_lcsc", "")
    datasheet = part.get("datasheet", "")

    # Generate unique ID
    sym_uuid = generate_uuid()

    # Calculate property offsets
    ref_y = y - 7.62
    val_y = y + 7.62
    fp_y = y + 10.16
    lcsc_y = y + 12.70
    ds_y = y + 15.24

    symbol = f'''  (symbol (lib_id "{symbol_lib}") (at {x:.2f} {y:.2f} {rotation})
    (uuid "{sym_uuid}")
    (property "Reference" "{designator}" (at {x:.2f} {ref_y:.2f} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{value}" (at {x:.2f} {val_y:.2f} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "{footprint}" (at {x:.2f} {fp_y:.2f} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "{datasheet}" (at {x:.2f} {ds_y:.2f} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "LCSC" "{lcsc}" (at {x:.2f} {lcsc_y:.2f} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (instances
      (project ""
        (path "/" (reference "{designator}") (unit 1))
      )
    )
  )
'''
    return symbol


def generate_text_label(text, x, y, size=2.5):
    """Generate a text label for section headers."""
    text_uuid = generate_uuid()
    return f'''  (text "{text}" (at {x:.2f} {y:.2f} 0)
    (effects (font (size {size} {size}) bold) (justify left))
    (uuid "{text_uuid}")
  )
'''


def generate_sheet_reference(sheet_name, filename, x, y, width=40, height=20):
    """Generate a hierarchical sheet reference."""
    sheet_uuid = generate_uuid()
    return f'''  (sheet (at {x:.2f} {y:.2f}) (size {width:.2f} {height:.2f})
    (fields_autoplaced yes)
    (stroke (width 0.1524) (type solid))
    (fill (color 0 0 0 0.0000))
    (uuid "{sheet_uuid}")
    (property "Sheetname" "{sheet_name}" (at {x:.2f} {y - 2.54:.2f} 0)
      (effects (font (size 1.27 1.27)) (justify left bottom))
    )
    (property "Sheetfile" "{filename}" (at {x:.2f} {y + height + 1.27:.2f} 0)
      (effects (font (size 1.27 1.27)) (justify left top))
    )
  )
'''


def generate_schematic_header(title, paper="A4"):
    """Generate the schematic file header."""
    sch_uuid = generate_uuid()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f'''(kicad_sch (version 20231120) (generator "python_generator")
  (uuid "{sch_uuid}")
  (paper "{paper}")
  (title_block
    (title "{title}")
    (date "{timestamp}")
    (rev "1.0")
    (company "Auto-generated from jlc_parts_enriched.json")
  )
  (lib_symbols)

'''


def generate_schematic_footer():
    """Generate the schematic file footer."""
    return '''  (sheet_instances
    (path "/" (page "1"))
  )
)
'''


def place_components_grid(parts, start_x=30, start_y=40, cols=5, x_spacing=40, y_spacing=35):
    """Place components in a grid layout, return symbols string."""
    symbols = ""

    # Group by type for better organization
    ics = [p for p in parts if p["designator"].startswith("U")]
    connectors = [p for p in parts if p["designator"].startswith("J")]
    switches = [p for p in parts if p["designator"].startswith(("SW", "ENC"))]
    leds = [p for p in parts if p["designator"].startswith("D")]
    caps = [p for p in parts if p["designator"].startswith("C")]
    resistors = [p for p in parts if p["designator"].startswith("R")]
    crystals = [p for p in parts if p["designator"].startswith("Y")]

    # Order for placement
    ordered = ics + connectors + switches + leds + crystals + resistors + caps

    y = start_y
    x = start_x
    col = 0

    # Add section labels
    current_section = None

    for part in ordered:
        designator = part["designator"]

        # Determine section
        if designator.startswith("U"):
            section = "ICs"
        elif designator.startswith("J"):
            section = "CONNECTORS"
        elif designator.startswith(("SW", "ENC")):
            section = "USER INTERFACE"
        elif designator.startswith("D"):
            section = "LEDs"
        elif designator.startswith("Y"):
            section = "CRYSTAL"
        elif designator.startswith("R"):
            section = "RESISTORS"
        elif designator.startswith("C"):
            section = "CAPACITORS"
        else:
            section = "OTHER"

        # Add section header if new section
        if section != current_section:
            if col != 0:
                y += y_spacing
                x = start_x
                col = 0
            symbols += generate_text_label(section, start_x - 5, y - 10)
            current_section = section

        symbols += generate_symbol(part, x, y)

        col += 1
        if col >= cols:
            col = 0
            x = start_x
            y += y_spacing
        else:
            x += x_spacing

    return symbols


def generate_radio_sheet(parts):
    """Generate the radio.kicad_sch file."""
    radio_parts = [p for p in parts if p["designator"] in RADIO_DESIGNATORS]

    content = generate_schematic_header("Radio Section - SI4735", "A4")
    content += generate_text_label("SI4735 RADIO SECTION", 25, 15, 3)
    content += place_components_grid(radio_parts, start_x=40, start_y=50, cols=4, x_spacing=45, y_spacing=40)
    content += generate_schematic_footer()

    return content


def generate_main_sheet(parts):
    """Generate the main.kicad_sch file."""
    main_parts = [p for p in parts if p["designator"] not in RADIO_DESIGNATORS]

    content = generate_schematic_header("Main Section - Power, MCU, UI", "A3")
    content += generate_text_label("MAIN SECTION - Power, ESP32, User Interface", 25, 15, 3)
    content += place_components_grid(main_parts, start_x=40, start_y=50, cols=6, x_spacing=40, y_spacing=35)
    content += generate_schematic_footer()

    return content


def generate_root_schematic():
    """Generate the root schematic with hierarchy."""
    content = generate_schematic_header("ESP32-S3 Radio Receiver - Root", "A4")
    content += generate_text_label("ESP32-S3 PORTABLE RADIO RECEIVER", 50, 30, 4)
    content += generate_text_label("Hierarchical Schematic", 50, 40, 2)

    # Add sheet references
    content += generate_sheet_reference("Main", "main.kicad_sch", 40, 70, 50, 25)
    content += generate_sheet_reference("Radio", "radio.kicad_sch", 40, 110, 50, 25)

    content += generate_schematic_footer()

    return content


def main():
    print("KiCAD 9 Schematic Generator")
    print("=" * 40)

    # Load parts
    print(f"Loading parts from: {PARTS_JSON}")
    parts = load_parts()
    print(f"Loaded {len(parts)} parts")

    # Separate parts
    radio_parts = [p for p in parts if p["designator"] in RADIO_DESIGNATORS]
    main_parts = [p for p in parts if p["designator"] not in RADIO_DESIGNATORS]
    print(f"Radio sheet: {len(radio_parts)} parts")
    print(f"Main sheet: {len(main_parts)} parts")

    # Generate radio sheet
    print("\nGenerating radio.kicad_sch...")
    radio_content = generate_radio_sheet(parts)
    radio_file = OUTPUT_DIR / "radio.kicad_sch"
    with open(radio_file, "w", encoding="utf-8") as f:
        f.write(radio_content)
    print(f"  Written: {radio_file}")

    # Generate main sheet
    print("\nGenerating main.kicad_sch...")
    main_content = generate_main_sheet(parts)
    main_file = OUTPUT_DIR / "main.kicad_sch"
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_content)
    print(f"  Written: {main_file}")

    # Generate root schematic
    print("\nGenerating Version2.kicad_sch (root)...")
    root_content = generate_root_schematic()
    root_file = OUTPUT_DIR / f"{PROJECT_NAME}.kicad_sch"
    with open(root_file, "w", encoding="utf-8") as f:
        f.write(root_content)
    print(f"  Written: {root_file}")

    print("\n" + "=" * 40)
    print("Generation complete!")
    print("\nNext steps:")
    print("1. Open Version2.kicad_pro in KiCAD 9")
    print("2. The root schematic shows hierarchy")
    print("3. Double-click sheets to view components")
    print("4. Verify symbols load from your KiCAD libraries")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
