#!/usr/bin/env python3
"""
Parse JLCPCB.kicad_sym library to extract pin names, numbers, and positions.

Usage:
    python parse_library_pins.py

Output:
    symbol_pins.json - Pin data for all symbols in JLCPCB library
"""
import re
import json
import os
from pathlib import Path

# JLCPCB library location - detect platform
import platform
if platform.system() == "Windows":
    KICAD_USER_DIR = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "KiCad"
else:
    # Linux/macOS
    KICAD_USER_DIR = Path.home() / ".local" / "share" / "kicad" / "9.0"
LIBRARY_PATH = KICAD_USER_DIR / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"


def parse_library():
    """Parse symbol library and extract pin information."""
    if not LIBRARY_PATH.exists():
        raise FileNotFoundError(
            f"Library not found at {LIBRARY_PATH}. "
            "Ask the LLM to run download_jlcpcb_libs.py or set LIBRARY_PATH to the correct JLCPCB.kicad_sym."
        )

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

        # Extract LCSC code from properties
        lcsc_match = re.search(r'\(property "LCSC" "([^"]+)"', part)
        lcsc_code = lcsc_match.group(1) if lcsc_match else None

        # Find all pins with position information
        # Pattern matches: (pin TYPE STYLE (at X Y ANGLE) ... (name "NAME") (number "NUM"))
        pin_pattern = r'\(pin\s+\w+\s+\w+\s*\(at\s+([\d.-]+)\s+([\d.-]+)\s+(\d+)\)'

        pins = []

        # Find pin blocks
        pin_matches = list(re.finditer(pin_pattern, part))

        # Find all (name "..." and (number "..." patterns
        name_matches = list(re.finditer(r'\(name "([^"]+)"', part))
        number_matches = list(re.finditer(r'\(number "([^"]+)"', part))

        # Match pins with their names and numbers by position in the file
        for i, (pin_m, name_m, num_m) in enumerate(zip(pin_matches, name_matches, number_matches)):
            pin_x = float(pin_m.group(1))
            pin_y = float(pin_m.group(2))
            pin_rot = int(pin_m.group(3))
            pin_name = name_m.group(1)
            pin_number = num_m.group(1)

            pins.append({
                "number": pin_number,
                "name": pin_name,
                "x": pin_x,
                "y": pin_y,
                "rotation": pin_rot
            })

        if pins:
            symbols[symbol_name] = {"pins": pins, "lcsc": lcsc_code}

    return symbols


def main():
    print("Parsing JLCPCB symbol library...")
    print(f"Library: {LIBRARY_PATH}")

    try:
        symbols = parse_library()
    except FileNotFoundError as e:
        print(e)
        return

    if not symbols:
        print("Error: No symbols parsed from library. "
              "Ask the LLM to verify the library file or rerun download_jlcpcb_libs.py.")
        return

    print(f"\nFound {len(symbols)} symbols with pins:\n")

    for symbol_name, data in sorted(symbols.items()):
        pins = data["pins"]
        print(f"{symbol_name}: {len(pins)} pins")
        # Show first few pins
        for pin in pins[:3]:
            print(f"  Pin {pin['number']:>3}: {pin['name']:<15} at ({pin['x']}, {pin['y']}) rot={pin['rotation']}")
        if len(pins) > 3:
            print(f"  ... and {len(pins) - 3} more pins")
        print()

    # Save to JSON
    output_path = Path(__file__).parent / "symbol_pins.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(symbols, f, indent=2)

    print(f"Saved to {output_path}")
    print(f"Total: {len(symbols)} symbols, {sum(len(s['pins']) for s in symbols.values())} pins")


if __name__ == "__main__":
    main()
