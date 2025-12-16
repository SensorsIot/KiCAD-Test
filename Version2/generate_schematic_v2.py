#!/usr/bin/env python3
"""
KiCAD 9 Schematic Generator v2

Generates KiCAD 9 schematic files using JLCPCB library symbols.
Creates hierarchical structure with Radio and Main sheets.

Usage:
    python generate_schematic_v2.py
"""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path

# Configuration
PARTS_JSON = Path(__file__).parent.parent / "jlcpcb_parts_pipeline" / "jlc_parts_enriched.json"
OUTPUT_DIR = Path(__file__).parent
PROJECT_NAME = "Version2"

# JLCPCB Library location
KICAD_USER_DIR = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "KiCad"
JLCPCB_LIB_DIR = KICAD_USER_DIR / "JLCPCB"
JLCPCB_SYM_FILE = JLCPCB_LIB_DIR / "symbol" / "JLCPCB.kicad_sym"

# Mapping from LCSC part numbers to JLCPCB symbol names
# Symbol names are based on MPN (manufacturer part number)
LCSC_TO_SYMBOL = {
    "C2913206": "ESP32-S3-MINI-1-N8",
    "C16581": "TP4056",
    "C6186": "AMS1117-3_3",
    "C195417": None,  # SI4735 - not available, use fallback
    "C2761795": "WS2812B-B{slash}W",
    "C393939": "TYPE-C16PIN",
    "C131337": "B2B-PH-K-S(LF)(SN)",
    "C145819": "PJ-227-5A",
    "C2337": "Header-Male-2_54_1x40",
    "C127509": "K2-1102SP-C4SC-04",
    "C255515": "EC11E18244A5",
    "C1713": "CL21A106KOQNNNE",
    "C5674": "CL21A226MQQNNNE",
    "C1591": "CL10B104KB8NNNC",
    "C1653": "CL10C220JB8NNNC",
    "C23186": "0603WAF5101T5E",
    "C22975": "0603WAF2001T5E",
    "C25804": "0603WAF1002T5E",
    "C23162": "0603WAF4701T5E",
    "C22775": "0603WAF1000T5E",
    "C32346": "Q13FC1350000400",
}

# Mapping from LCSC to JLCPCB footprint names
LCSC_TO_FOOTPRINT = {
    "C2913206": "JLCPCB:BULETM-SMD_ESP32-S3-MINI-1-N8",
    "C16581": "JLCPCB:ESOP-8_L4.9-W3.9-P1.27-LS6.0-BL-EP",
    "C6186": "JLCPCB:SOT-223-3_L6.5-W3.4-P2.30-LS7.0-BR",
    "C195417": "Package_SO:SSOP-24_5.3x8.2mm_P0.65mm",  # SI4735 fallback
    "C2761795": "JLCPCB:LED-SMD_4P-L5.0-W5.0-TL_WS2812B-B",
    "C393939": "JLCPCB:USB-C-SMD_TYPE-C16PIN",
    "C131337": "JLCPCB:CONN-TH_B2B-PH-K-S",
    "C145819": "JLCPCB:AUDIO-SMD_PJ-227-5A",
    "C2337": "JLCPCB:HDR-TH_40P-P2.54-V-M-1",
    "C127509": "JLCPCB:KEY-SMD_4P-L6.0-W6.0-P4.50-LS9.5-BL",
    "C255515": "JLCPCB:SW-TH_EC11E18244A5",
    "C1713": "JLCPCB:C0805",
    "C5674": "JLCPCB:C0805",
    "C1591": "JLCPCB:C0603",
    "C1653": "JLCPCB:C0603",
    "C23186": "JLCPCB:R0603",
    "C22975": "JLCPCB:R0603",
    "C25804": "JLCPCB:R0603",
    "C23162": "JLCPCB:R0603",
    "C22775": "JLCPCB:R0603",
    "C32346": "JLCPCB:FC-135R_L3.2-W1.5",
}

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


def get_symbol_lib(part):
    """Get the JLCPCB symbol library reference for a part."""
    lcsc = part.get("selection", {}).get("lcsc") or part.get("known_lcsc", "")

    symbol_name = LCSC_TO_SYMBOL.get(lcsc)
    if symbol_name:
        return f"JLCPCB:{symbol_name}"

    # Fallback to original symbol from YAML
    original_symbol = part.get("symbol", "")
    if original_symbol:
        return original_symbol

    # Default fallbacks based on designator
    designator = part["designator"]
    if designator.startswith("R"):
        return "Device:R"
    elif designator.startswith("C"):
        return "Device:C"
    elif designator.startswith("U"):
        return "Device:Generic"

    return "Device:Generic"


def get_footprint(part):
    """Get the JLCPCB footprint for a part."""
    lcsc = part.get("selection", {}).get("lcsc") or part.get("known_lcsc", "")

    footprint = LCSC_TO_FOOTPRINT.get(lcsc)
    if footprint:
        return footprint

    # Fallback to original footprint from YAML
    return part.get("footprint", "")


def generate_symbol(part, x, y, rotation=0):
    """Generate a KiCAD symbol S-expression for a part."""
    symbol_lib = get_symbol_lib(part)
    footprint = get_footprint(part)
    designator = part["designator"]
    value = part.get("value") or part.get("query") or designator
    lcsc = part.get("selection", {}).get("lcsc") or part.get("known_lcsc", "")
    datasheet = part.get("datasheet", "")

    sym_uuid = generate_uuid()

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

    return f'''(kicad_sch (version 20231120) (generator "python_generator_v2")
  (uuid "{sch_uuid}")
  (paper "{paper}")
  (title_block
    (title "{title}")
    (date "{timestamp}")
    (rev "2.0")
    (company "Generated with JLCPCB symbols")
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

    ordered = ics + connectors + switches + leds + crystals + resistors + caps

    y = start_y
    x = start_x
    col = 0
    current_section = None

    for part in ordered:
        designator = part["designator"]

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
    content += generate_text_label("Hierarchical Schematic (JLCPCB Symbols)", 50, 40, 2)

    content += generate_sheet_reference("Main", "main.kicad_sch", 40, 70, 50, 25)
    content += generate_sheet_reference("Radio", "radio.kicad_sch", 40, 110, 50, 25)

    content += generate_schematic_footer()

    return content


def main():
    print("KiCAD 9 Schematic Generator v2 (JLCPCB Symbols)")
    print("=" * 50)

    # Check JLCPCB library
    if JLCPCB_SYM_FILE.exists():
        print(f"JLCPCB library found: {JLCPCB_SYM_FILE}")
    else:
        print(f"Warning: JLCPCB library not found at {JLCPCB_SYM_FILE}")
        print("Run download_jlcpcb_libs.py --register first")

    # Load parts
    print(f"\nLoading parts from: {PARTS_JSON}")
    parts = load_parts()
    print(f"Loaded {len(parts)} parts")

    # Separate parts
    radio_parts = [p for p in parts if p["designator"] in RADIO_DESIGNATORS]
    main_parts = [p for p in parts if p["designator"] not in RADIO_DESIGNATORS]
    print(f"Radio sheet: {len(radio_parts)} parts")
    print(f"Main sheet: {len(main_parts)} parts")

    # Show symbol mapping
    print("\nSymbol mapping (LCSC -> JLCPCB):")
    for part in parts[:5]:  # Show first 5
        lcsc = part.get("selection", {}).get("lcsc") or part.get("known_lcsc", "")
        symbol = get_symbol_lib(part)
        print(f"  {part['designator']}: {lcsc} -> {symbol}")
    print("  ...")

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

    print("\n" + "=" * 50)
    print("Generation complete!")
    print("\nNext steps:")
    print("1. Open Version2.kicad_pro in KiCAD 9")
    print("2. Symbols should load from JLCPCB library")
    print("3. For SI4735 (U4): manually assign symbol or use generic")
    print("4. Note: SI4735 (C195417) not available on EasyEDA")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
