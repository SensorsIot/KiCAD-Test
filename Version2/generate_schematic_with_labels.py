#!/usr/bin/env python3
"""
Generate KiCAD schematic with net labels on every pin endpoint.
Each pin gets a unique label: {designator}_{pin_number}
"""
import json
import re
import uuid
import math
from pathlib import Path
from datetime import datetime

# Paths
PARTS_JSON = Path(__file__).parent / "parts_with_netlabels.json"
SYMBOL_LIB = Path(r"C:\Users\AndreasSpiess\Documents\KiCad\JLCPCB\symbol\JLCPCB.kicad_sym")
OUTPUT_FILE = Path(__file__).parent / "radio_with_netlabels.kicad_sch"

# Components for Radio sheet vs Main sheet
RADIO_DESIGNATORS = {"U4", "Y1", "J3", "C12", "C13", "C14", "C15", "C16", "R7", "R8"}


def generate_uuid():
    return str(uuid.uuid4())


def parse_symbol_pins(symbol_lib_path):
    """Parse symbol library to get pin positions for each symbol."""
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

        # Find all pins with positions
        pins = []
        # Pattern: (pin TYPE STYLE (at X Y ROT) (length LEN) (name "NAME"...) (number "NUM"...))
        pin_pattern = r'\(pin\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s*\(length\s+([-\d.]+)\)'
        name_pattern = r'\(name "([^"]+)"'
        number_pattern = r'\(number "([^"]+)"'

        # Find each pin block - handle multiline format
        # Pattern: (pin TYPE STYLE\n  (at X Y ROT)\n  (length L)\n  (name "N"...)\n  (number "N"...)\n)
        pin_blocks = re.findall(r'\(pin\s+\w+\s+\w+\s*\(at[^)]+\).*?\(number\s+"[^"]+"\s*\([^)]+\)\s*\)', part, re.DOTALL)

        for pin_block in pin_blocks:
            at_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)', pin_block)
            len_match = re.search(r'\(length\s+([-\d.]+)\)', pin_block)
            name_match = re.search(r'\(name\s+"([^"]+)"', pin_block)
            num_match = re.search(r'\(number\s+"([^"]+)"', pin_block)

            if at_match and len_match and name_match and num_match:
                x = float(at_match.group(1))
                y = float(at_match.group(2))
                rotation = int(at_match.group(3))
                length = float(len_match.group(1))
                name = name_match.group(1)
                number = num_match.group(1)

                # Pin endpoint calculation:
                # In KiCAD symbol library, (at X Y ROT) IS the wire connection point
                # The pin line extends FROM this point TOWARD the symbol body
                # So X, Y is already the endpoint - no length calculation needed!
                end_x = x
                end_y = y

                pins.append({
                    'number': number,
                    'name': name,
                    'x': end_x,
                    'y': end_y,
                    'rotation': rotation
                })

        if pins:
            symbols[symbol_name] = pins

    return symbols


def get_label_position(pin_x, pin_y, pin_rotation):
    """
    Calculate label position and rotation based on pin direction.
    Returns: (x_offset, y_offset, label_rotation, justify)

    Pin rotation = direction pin LINE points (toward symbol body):
    - 0°   = pin points RIGHT → endpoint on LEFT  → LEFT pins
    - 180° = pin points LEFT  → endpoint on RIGHT → RIGHT pins
    - 90°  = pin points UP    → endpoint on BOTTOM → BOTTOM pins
    - 270° = pin points DOWN  → endpoint on TOP   → TOP pins
    """
    offset = 2.0  # Base offset in mm

    if pin_rotation == 0:      # LEFT pins - label extends left
        x_off = -offset
        y_off = 0
        label_rot = 180
        justify = "right"  # Text ends at pin

    elif pin_rotation == 180:  # RIGHT pins - label extends right
        x_off = offset
        y_off = 0
        label_rot = 0
        justify = "left"   # Text starts at pin

    elif pin_rotation == 90:   # BOTTOM pins - label extends down
        x_off = 0
        y_off = offset
        label_rot = 270
        justify = "right"  # Vertical text extends down from pin

    elif pin_rotation == 270:  # TOP pins - label extends up
        x_off = 0
        y_off = -offset
        label_rot = 270
        justify = "left"  # Vertical text starts at pin

    else:
        x_off = 0
        y_off = 0
        label_rot = 0
        justify = "left"

    return x_off, y_off, label_rot, justify


def generate_symbol(designator, symbol_name, footprint, x, y):
    """Generate a KiCAD symbol."""
    sym_uuid = generate_uuid()

    # Handle special symbol names
    if symbol_name == "SI4735-D60-GU":
        lib_id = "Interface_Expansion:SI4735-D60-GU"  # Fallback
    else:
        lib_id = f"JLCPCB:{symbol_name}"

    return f'''  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0)
    (uuid "{sym_uuid}")
    (property "Reference" "{designator}" (at {x:.2f} {y - 10:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{symbol_name}" (at {x:.2f} {y + 10:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "{footprint}" (at {x:.2f} {y + 12:.2f} 0)
      (effects (font (size 1.27 1.27)) hide))
    (instances (project "" (path "/" (reference "{designator}") (unit 1))))
  )
'''


def generate_label(net_label, x, y, rotation=0, justify="left"):
    """Generate a net label."""
    label_uuid = generate_uuid()

    return f'''  (label "{net_label}" (at {x:.2f} {y:.2f} {rotation}) (fields_autoplaced yes)
    (effects (font (size 1.27 1.27)) (justify {justify}))
    (uuid "{label_uuid}"))
'''


def generate_schematic(parts, symbol_pins, output_path, title="Radio Project"):
    """Generate complete schematic with all parts and labels."""

    # Header
    content = f'''(kicad_sch (version 20231120) (generator "python_generator")
  (uuid "{generate_uuid()}")
  (paper "A2")
  (title_block
    (title "{title}")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (rev "1.0")
    (comment 1 "Generated with net labels on every pin")
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

    # Sort parts by designator type
    def sort_key(p):
        d = p['designator']
        prefix = ''.join(c for c in d if c.isalpha())
        num = ''.join(c for c in d if c.isdigit())
        order = {'U': 0, 'J': 1, 'SW': 2, 'ENC': 3, 'D': 4, 'Y': 5, 'R': 6, 'C': 7}
        return (order.get(prefix, 99), int(num) if num else 0)

    sorted_parts = sorted(parts, key=sort_key)

    # Place components and labels
    for part in sorted_parts:
        designator = part['designator']
        symbol_name = part['symbol']
        footprint = part['footprint']
        pins = part['pins']

        # Calculate position
        x = start_x + col * x_spacing
        y = start_y + row * y_spacing

        # Generate symbol
        content += generate_symbol(designator, symbol_name, footprint, x, y)

        # Get pin positions from symbol library
        sym_pins = symbol_pins.get(symbol_name, [])

        # Create pin number to position mapping
        pin_positions = {p['number']: p for p in sym_pins}

        # Generate labels for each pin
        for pin in pins:
            pin_num = pin['number']
            net_label = pin['net_label']

            if pin_num in pin_positions:
                pin_info = pin_positions[pin_num]
                pin_x = pin_info['x']
                pin_y = pin_info['y']
                pin_rot = pin_info['rotation']

                # Get label offset, rotation, and justification (all logic in one place)
                x_off, y_off, label_rot, justify = get_label_position(pin_x, pin_y, pin_rot)

                # Calculate absolute position
                # NOTE: Y-axis is inverted! Symbol library Y+ = up, schematic Y+ = down
                label_x = x + pin_x + x_off
                label_y = y - pin_y + y_off

            else:
                # Fallback: place label near symbol
                label_x = x + 25
                label_y = y + pins.index(pin) * 3
                label_rot = 0
                justify = "left"

            content += generate_label(net_label, label_x, label_y, label_rot, justify)

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

    output_path.write_text(content, encoding='utf-8')
    return len(sorted_parts)


def main():
    print("Generating schematic with net labels on every pin...")
    print("=" * 60)

    # Load parts data
    print(f"\nLoading parts from: {PARTS_JSON}")
    with open(PARTS_JSON) as f:
        data = json.load(f)
    parts = data['parts']
    print(f"  Loaded {len(parts)} parts")

    # Parse symbol library for pin positions
    print(f"\nParsing symbol library: {SYMBOL_LIB}")
    symbol_pins = parse_symbol_pins(SYMBOL_LIB)
    print(f"  Found pin data for {len(symbol_pins)} symbols")

    # Count total pins
    total_pins = sum(len(p['pins']) for p in parts)
    print(f"\nTotal pins to label: {total_pins}")

    # Generate schematic
    print(f"\nGenerating: {OUTPUT_FILE}")
    num_parts = generate_schematic(parts, symbol_pins, OUTPUT_FILE,
                                    "ESP32-S3 Radio Receiver - All Pins Labeled")

    print(f"\n" + "=" * 60)
    print(f"SUCCESS! Generated schematic with:")
    print(f"  - {num_parts} components")
    print(f"  - {total_pins} net labels (one per pin)")
    print(f"\nOpen in KiCAD:")
    print(f"  1. File > Open > {OUTPUT_FILE}")
    print(f"  2. Tools > Update Schematic from Symbol Libraries")
    print("=" * 60)


if __name__ == "__main__":
    main()
