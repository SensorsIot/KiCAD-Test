#!/usr/bin/env python3
"""
Parse JLCPCB.kicad_sym library to extract pin names and numbers for each symbol.
"""
import re
import json
from pathlib import Path

LIBRARY_PATH = Path(r"C:\Users\AndreasSpiess\Documents\KiCad\JLCPCB\symbol\JLCPCB.kicad_sym")

def parse_library():
    """Parse symbol library and extract pin information."""
    content = LIBRARY_PATH.read_text(encoding='utf-8')

    symbols = {}

    # Split content by top-level symbols (those with in_bom)
    parts = re.split(r'(?=\(symbol "[^"]+"\s+\(in_bom)', content)

    for part in parts:
        if not part.strip() or '(in_bom' not in part:
            continue

        # Get symbol name
        match = re.match(r'\(symbol "([^"]+)"', part)
        if not match:
            continue
        symbol_name = match.group(1)

        # Find all pins - simpler pattern
        # Looking for (name "X" and (number "Y" on separate lines
        pins = []

        # Find all (name "..." lines
        name_matches = list(re.finditer(r'\(name "([^"]+)"', part))
        number_matches = list(re.finditer(r'\(number "([^"]+)"', part))

        # Pair them up (they should appear in order)
        for i, (name_m, num_m) in enumerate(zip(name_matches, number_matches)):
            pin_name = name_m.group(1)
            pin_number = num_m.group(1)
            pins.append({"name": pin_name, "number": pin_number})

        if pins:
            symbols[symbol_name] = pins

    return symbols

def main():
    print("Parsing JLCPCB symbol library...")
    symbols = parse_library()

    print(f"\nFound {len(symbols)} symbols with pins:\n")

    for symbol_name, pins in sorted(symbols.items()):
        print(f"{symbol_name}:")
        for pin in pins:
            print(f"  Pin {pin['number']:>3}: {pin['name']}")
        print()

    # Save to JSON
    output_path = Path(__file__).parent / "symbol_pins.json"
    with open(output_path, 'w') as f:
        json.dump(symbols, f, indent=2)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
