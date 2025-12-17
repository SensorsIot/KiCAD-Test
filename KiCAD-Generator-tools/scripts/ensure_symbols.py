#!/usr/bin/env python3
"""
Ensure all required symbols exist in the JLCPCB library.

This script:
1. Reads pin_model.json OR step2_parts_complete.yaml to get all LCSC codes
2. Checks which symbols are missing from JLCPCB.kicad_sym
3. Downloads missing symbols using JLC2KiCadLib
4. Appends them to the library

Run this AFTER Step 2 (parts list) and BEFORE schematic generation.

Usage:
    # From pin_model.json (default)
    python ensure_symbols.py

    # From step2 YAML file
    python ensure_symbols.py --parts work/step2_parts_complete.yaml

    # Specify library path
    python ensure_symbols.py --library output/libs/JLCPCB/symbol/JLCPCB.kicad_sym
"""

import json
import subprocess
import tempfile
import re
import shutil
from pathlib import Path
from typing import Set, Dict, List

# Try to import yaml, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Generic parts that use standard symbols (don't need individual LCSC symbols)
GENERIC_PREFIXES = {'R', 'C', 'L'}  # Resistor, Capacitor, Inductor


def extract_lcsc_from_yaml(yaml_path: Path) -> Dict[str, str]:
    """
    Extract LCSC codes from step2_parts_complete.yaml.
    Returns dict of {lcsc_code: part_value} for tracking.
    Skips generic passives (R, C, L) that use standard symbols.
    """
    lcsc_parts = {}

    if HAS_YAML:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for part in data.get('parts', []):
            lcsc = part.get('lcsc', '')
            value = part.get('part', '') or part.get('value', '')
            prefix = part.get('prefix', '')

            # Skip generic passives - they use standard R/C/L symbols
            if prefix in GENERIC_PREFIXES:
                continue

            if lcsc and lcsc.startswith('C'):
                lcsc_parts[lcsc] = value
    else:
        # Basic regex parsing if PyYAML not installed
        content = yaml_path.read_text(encoding='utf-8')
        # Find lcsc: "Cxxxxx" patterns (can't filter by prefix without full parsing)
        for match in re.finditer(r'lcsc:\s*["\']?(C\d+)["\']?', content):
            lcsc = match.group(1)
            lcsc_parts[lcsc] = lcsc  # Use LCSC as value if can't parse

    return lcsc_parts


def extract_lcsc_from_json(json_path: Path) -> Dict[str, str]:
    """
    Extract LCSC codes from pin_model.json.
    Returns dict of {lcsc_code: part_value} for tracking.
    Skips generic passives (R, C, L) that use standard symbols.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        model = json.load(f)

    lcsc_parts = {}
    for part in model.get('parts', []):
        lcsc = part.get('lcsc', '')
        value = part.get('value', '')
        ref = part.get('ref', '')

        # Skip generic passives - check if ref starts with R, C, or L
        if ref and ref[0] in GENERIC_PREFIXES:
            continue

        if lcsc and lcsc.startswith('C'):
            lcsc_parts[lcsc] = value

    return lcsc_parts


def extract_lcsc_codes(parts_path: Path) -> Dict[str, str]:
    """
    Extract LCSC codes from either JSON or YAML file.
    Returns dict of {lcsc_code: part_value} for tracking.
    """
    if parts_path.suffix in ['.yaml', '.yml']:
        return extract_lcsc_from_yaml(parts_path)
    else:
        return extract_lcsc_from_json(parts_path)


def get_existing_symbols(library_path: Path) -> Set[str]:
    """
    Get set of LCSC codes that already have symbols in the library.
    Looks for property "LCSC" "Cxxxxx" in the .kicad_sym file.
    """
    existing = set()

    if not library_path.exists():
        return existing

    content = library_path.read_text(encoding='utf-8')

    # Find all LCSC properties: (property "LCSC" "C12345" ...)
    pattern = r'\(property\s+"LCSC"\s+"(C\d+)"'
    matches = re.findall(pattern, content)
    existing.update(matches)

    return existing


def download_symbol(lcsc_code: str, temp_dir: Path) -> Path | None:
    """
    Download symbol using JLC2KiCadLib.
    Returns path to downloaded .kicad_sym file or None if failed.
    """
    try:
        result = subprocess.run(
            ['JLC2KiCadLib', lcsc_code, '-dir', str(temp_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"    Warning: JLC2KiCadLib failed for {lcsc_code}")
            print(f"    {result.stderr}")
            return None

        # Find the generated .kicad_sym file
        symbol_dir = temp_dir / 'symbol'
        if symbol_dir.exists():
            sym_files = list(symbol_dir.glob('*.kicad_sym'))
            if sym_files:
                return sym_files[0]

        return None

    except subprocess.TimeoutExpired:
        print(f"    Warning: Timeout downloading {lcsc_code}")
        return None
    except FileNotFoundError:
        print("    Error: JLC2KiCadLib not found. Install with: pip install JLC2KiCadLib")
        return None


def extract_symbol_from_file(sym_file: Path, lcsc_code: str) -> str | None:
    """
    Extract the symbol definition from a .kicad_sym file.
    Returns the symbol S-expression string or None.
    """
    content = sym_file.read_text(encoding='utf-8')

    # Find the main symbol definition (not the _0_1 or _1_1 sub-symbols)
    # Pattern: (symbol "NAME" (in_bom ...) ... until matching close paren

    # Simple approach: find all top-level symbols
    lines = content.split('\n')
    in_symbol = False
    symbol_lines = []
    paren_depth = 0

    for line in lines:
        if '(symbol "' in line and '_0_1' not in line and '_1_1' not in line and not in_symbol:
            # Check if this is a top-level symbol (not nested)
            if line.strip().startswith('(symbol "'):
                in_symbol = True
                paren_depth = 0

        if in_symbol:
            symbol_lines.append(line)
            paren_depth += line.count('(') - line.count(')')

            if paren_depth <= 0 and len(symbol_lines) > 1:
                break

    if symbol_lines:
        symbol_text = '\n'.join(symbol_lines)
        # Ensure LCSC property exists
        if f'"LCSC"' not in symbol_text:
            # Add LCSC property after Value property
            symbol_text = re.sub(
                r'(\(property "Value"[^)]+\)\s*\))',
                f'\\1\n    (property "LCSC" "{lcsc_code}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
                symbol_text
            )
        return symbol_text

    return None


def append_symbol_to_library(library_path: Path, symbol_text: str):
    """
    Append a symbol definition to the JLCPCB.kicad_sym library.
    """
    content = library_path.read_text(encoding='utf-8')

    # Find the closing paren of the library
    # Insert the new symbol before the final )
    if content.rstrip().endswith(')'):
        # Remove final ) and add new symbol + )
        content = content.rstrip()[:-1]
        content += f"\n\n  {symbol_text}\n\n)"
        library_path.write_text(content, encoding='utf-8')
        return True

    return False


def ensure_symbols(pin_model_path: Path, library_path: Path, dry_run: bool = False) -> Dict[str, str]:
    """
    Main function to ensure all symbols exist.

    Returns dict of {lcsc_code: status} where status is:
    - "exists" - already in library
    - "added" - successfully downloaded and added
    - "failed" - could not download
    """
    print(f"Reading: {pin_model_path}")
    lcsc_parts = extract_lcsc_codes(pin_model_path)
    print(f"  Found {len(lcsc_parts)} unique LCSC codes")

    print(f"\nChecking library: {library_path}")
    existing = get_existing_symbols(library_path)
    print(f"  Library has {len(existing)} symbols with LCSC codes")

    # Find missing symbols
    missing = set(lcsc_parts.keys()) - existing

    if not missing:
        print("\n  All symbols present!")
        return {code: "exists" for code in lcsc_parts}

    print(f"\n  Missing {len(missing)} symbols:")
    for code in sorted(missing):
        print(f"    - {code}: {lcsc_parts[code]}")

    if dry_run:
        print("\n  Dry run - not downloading")
        return {code: "exists" if code in existing else "missing" for code in lcsc_parts}

    # Download missing symbols
    results = {code: "exists" for code in existing}

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for code in sorted(missing):
            print(f"\n  Downloading {code} ({lcsc_parts[code]})...")

            # Clear temp dir for each download
            for item in temp_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            sym_file = download_symbol(code, temp_path)

            if sym_file:
                symbol_text = extract_symbol_from_file(sym_file, code)
                if symbol_text:
                    if append_symbol_to_library(library_path, symbol_text):
                        print(f"    Added to library")
                        results[code] = "added"
                    else:
                        print(f"    Failed to append to library")
                        results[code] = "failed"
                else:
                    print(f"    Could not extract symbol")
                    results[code] = "failed"
            else:
                results[code] = "failed"

    # Summary
    added = sum(1 for s in results.values() if s == "added")
    failed = sum(1 for s in results.values() if s == "failed")
    print(f"\n  Summary: {added} added, {failed} failed, {len(existing)} already existed")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Ensure all symbols exist in JLCPCB library')
    parser.add_argument('--parts', type=Path, help='Path to parts file (step2_parts_complete.yaml or pin_model.json)')
    parser.add_argument('--pin-model', type=Path, help='Alias for --parts (deprecated)')
    parser.add_argument('--library', type=Path, help='Path to JLCPCB.kicad_sym')
    parser.add_argument('--dry-run', action='store_true', help='Check only, do not download')
    parser.add_argument('--create-library', action='store_true', help='Create library file if it does not exist')
    args = parser.parse_args()

    # Default paths
    script_dir = Path(__file__).parent
    tools_dir = script_dir.parent  # KiCAD-Generator-tools directory

    # Central library location (shared across all projects)
    central_library = tools_dir / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"

    # Find parts file (prefer --parts, fall back to --pin-model, then defaults)
    parts_file = args.parts or args.pin_model
    if not parts_file:
        # Try current directory first, then tools_dir
        cwd = Path.cwd()
        candidates = [
            cwd / "work" / "step2_parts_complete.yaml",
            cwd / "work" / "pin_model.json",
            tools_dir / "work" / "step2_parts_complete.yaml",
            tools_dir / "work" / "pin_model.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                parts_file = candidate
                break

        if not parts_file:
            print(f"Error: No parts file found")
            print(f"  Looked for:")
            for c in candidates:
                print(f"    - {c}")
            print(f"  Specify with --parts <path>")
            return 1

    # Use central library by default, fall back to project-local library
    library = args.library
    if not library:
        if central_library.exists():
            library = central_library
        else:
            # Fall back to project-local library
            library = Path.cwd() / "output" / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"

    if not parts_file.exists():
        print(f"Error: Parts file not found at {parts_file}")
        return 1

    if not library.exists():
        if args.create_library:
            # Create empty library
            library.parent.mkdir(parents=True, exist_ok=True)
            library.write_text('(kicad_symbol_lib (version 20220914) (generator ensure_symbols)\n\n)\n')
            print(f"Created empty library: {library}")
        else:
            print(f"Error: Library not found at {library}")
            print("  Create the library first, specify --library path, or use --create-library")
            return 1

    results = ensure_symbols(parts_file, library, dry_run=args.dry_run)

    # Exit with error if any failed
    if any(s == "failed" for s in results.values()):
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
