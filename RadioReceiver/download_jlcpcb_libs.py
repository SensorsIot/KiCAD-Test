#!/usr/bin/env python3
"""
Download JLCPCB/LCSC symbols and footprints for all parts.

Uses JLC2KiCadLib to fetch symbols, footprints, and 3D models from JLCPCB/EasyEDA.
Only downloads parts not already in the library (uses LCSC numbers as index).

Libraries are stored in KiCAD's standard user library location:
  Windows: %USERPROFILE%\Documents\KiCad\JLCPCB\

Usage:
    python download_jlcpcb_libs.py
    python download_jlcpcb_libs.py --force       # Re-download all parts
    python download_jlcpcb_libs.py --register    # Register in global KiCAD library tables
"""

import json
import subprocess
import sys
import re
import argparse
import os
from pathlib import Path
import yaml

# Configuration
PARTS_JSON = Path(__file__).parent / "parts_with_designators.json"
CUSTOM_OVERRIDES = Path(__file__).parent / "custom_library_overrides.yaml"
MISSING_REPORT = Path(__file__).parent / "missing_parts.yaml"

# Detect platform and set paths accordingly
import platform
if platform.system() == "Windows":
    KICAD_USER_DIR = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "KiCad"
    KICAD_CONFIG_DIR = Path(os.environ.get("APPDATA", "")) / "kicad" / "9.0"
    JLC2KICAD_EXE = r"C:\Users\AndreasSpiess\AppData\Local\Programs\Python\Python312\Scripts\JLC2KiCadLib.exe"
else:
    # Linux/macOS
    KICAD_USER_DIR = Path.home() / ".local" / "share" / "kicad" / "9.0"
    KICAD_CONFIG_DIR = Path.home() / ".config" / "kicad" / "9.0"
    # Use venv JLC2KiCadLib or system-installed
    VENV_PATH = Path(__file__).parent.parent / ".venv" / "bin" / "JLC2KiCadLib"
    if VENV_PATH.exists():
        JLC2KICAD_EXE = str(VENV_PATH)
    else:
        JLC2KICAD_EXE = "JLC2KiCadLib"  # Assume in PATH

OUTPUT_DIR = KICAD_USER_DIR / "JLCPCB"
SYMBOL_LIB = "JLCPCB"
FOOTPRINT_LIB = "JLCPCB"

# Index file to track downloaded LCSC parts
INDEX_FILE = OUTPUT_DIR / "lcsc_index.json"


def load_index():
    """Load index of already downloaded LCSC parts."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"parts": {}, "version": 1}


def save_index(index):
    """Save index of downloaded LCSC parts."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def get_existing_symbols():
    """Parse symbol library to find existing symbols with LCSC properties."""
    sym_file = OUTPUT_DIR / "symbol" / f"{SYMBOL_LIB}.kicad_sym"
    existing = {}

    if not sym_file.exists():
        return existing

    with open(sym_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all symbols and their LCSC properties
    symbol_pattern = r'\(symbol "([^"]+)"[^)]*\(in_bom'
    lcsc_pattern = r'\(property "LCSC" "([^"]+)"'

    for match in re.finditer(symbol_pattern, content):
        symbol_name = match.group(1)
        start = match.start()
        search_area = content[start:start + 5000]
        lcsc_match = re.search(lcsc_pattern, search_area)
        if lcsc_match:
            lcsc = lcsc_match.group(1)
            existing[lcsc] = symbol_name

    return existing


def load_parts():
    """Load parts from JSON and extract unique LCSC numbers."""
    with open(PARTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    lcsc_parts = {}
    for name, part in data.items():
        lcsc = part.get("lcsc", "")
        if lcsc and lcsc != "NOT_SELECTED" and lcsc != "NOT_FOUND":
            lcsc_clean = lcsc if lcsc.startswith("C") else f"C{lcsc}"
            designators = part.get("designators", [])
            mpn = part.get("mpn", "")

            if lcsc_clean not in lcsc_parts:
                lcsc_parts[lcsc_clean] = {
                    "designators": [],
                    "mpn": mpn,
                    "semantic_name": name
                }
            lcsc_parts[lcsc_clean]["designators"].extend(designators)

    return lcsc_parts


def load_overrides():
    """Load custom overrides for symbols/footprints."""
    if not CUSTOM_OVERRIDES.exists():
        return {}
    with open(CUSTOM_OVERRIDES, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_missing_parts(missing):
    """Save missing parts report to YAML for LLM/human to fill."""
    with open(MISSING_REPORT, "w", encoding="utf-8") as f:
        yaml.safe_dump(missing, f, sort_keys=False)
    print(f"\nMissing parts report written to {MISSING_REPORT}")
    print("Ask the LLM to populate symbol_lib_id/footprint_lib_id in custom_library_overrides.yaml and rerun.")


def download_parts(lcsc_list, index):
    """Download specified parts using JLC2KiCadLib."""

    if not lcsc_list:
        print("No new parts to download.")
        return True

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading {len(lcsc_list)} parts to: {OUTPUT_DIR}")
    print("=" * 50)

    cmd = [
        JLC2KICAD_EXE,
        *lcsc_list,
        "-dir", str(OUTPUT_DIR),
        "-symbol_lib", SYMBOL_LIB,
        "-footprint_lib", FOOTPRINT_LIB,
        "-models", "STEP",
        "-logging_level", "INFO",
        "--skip_existing",
    ]

    print(f"Running: JLC2KiCadLib {' '.join(lcsc_list[:3])}... ({len(lcsc_list)} parts)")
    print()

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            for lcsc in lcsc_list:
                index["parts"][lcsc] = {
                    "downloaded": True,
                    "symbol_lib": SYMBOL_LIB,
                    "footprint_lib": FOOTPRINT_LIB
                }
            save_index(index)
            print("\n" + "=" * 50)
            print("Download complete!")
        else:
            print(f"\nWarning: JLC2KiCadLib exited with code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print("\nError: Download timed out after 5 minutes")
        return False
    except FileNotFoundError:
        print(f"\nError: JLC2KiCadLib not found at {JLC2KICAD_EXE}")
        print("Ask the LLM to set JLC2KICAD_EXE to your installed path or install JLC2KiCadLib via pip.")
        return False

    return True


def register_global_libraries():
    """Add JLCPCB library to KiCAD's global library tables."""

    sym_lib_table = KICAD_CONFIG_DIR / "sym-lib-table"
    fp_lib_table = KICAD_CONFIG_DIR / "fp-lib-table"

    sym_path = OUTPUT_DIR / "symbol" / f"{SYMBOL_LIB}.kicad_sym"
    fp_path = OUTPUT_DIR / FOOTPRINT_LIB

    # Use forward slashes for paths
    sym_path_str = str(sym_path).replace("\\", "/")
    fp_path_str = str(fp_path).replace("\\", "/")

    # Symbol library entry
    sym_entry = f'  (lib (name "{SYMBOL_LIB}")(type "KiCad")(uri "{sym_path_str}")(options "")(descr "JLCPCB/LCSC parts library"))'

    # Footprint library entry
    fp_entry = f'  (lib (name "{FOOTPRINT_LIB}")(type "KiCad")(uri "{fp_path_str}")(options "")(descr "JLCPCB/LCSC footprints library"))'

    # Update sym-lib-table
    if sym_lib_table.exists():
        with open(sym_lib_table, "r", encoding="utf-8") as f:
            content = f.read()

        if f'(name "{SYMBOL_LIB}")' not in content:
            content = content.rstrip().rstrip(")")
            content += f"\n{sym_entry}\n)\n"
            with open(sym_lib_table, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Added {SYMBOL_LIB} to {sym_lib_table}")
        else:
            print(f"{SYMBOL_LIB} already in sym-lib-table")
    else:
        print(f"Warning: {sym_lib_table} not found")

    # Update fp-lib-table
    if fp_lib_table.exists():
        with open(fp_lib_table, "r", encoding="utf-8") as f:
            content = f.read()

        if f'(name "{FOOTPRINT_LIB}")' not in content:
            content = content.rstrip().rstrip(")")
            content += f"\n{fp_entry}\n)\n"
            with open(fp_lib_table, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Added {FOOTPRINT_LIB} to {fp_lib_table}")
        else:
            print(f"{FOOTPRINT_LIB} already in fp-lib-table")
    else:
        print(f"Warning: {fp_lib_table} not found")


def fix_library_for_kicad9():
    """Fix library format for KiCAD 9 compatibility."""
    sym_file = OUTPUT_DIR / "symbol" / f"{SYMBOL_LIB}.kicad_sym"

    if not sym_file.exists():
        return

    with open(sym_file, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False

    # Fix 1: Update header version to KiCAD 9
    old_header = '(kicad_symbol_lib (version 20210201) (generator TousstNicolas/JLC2KiCad_lib)'
    new_header = '''(kicad_symbol_lib
\t(version 20241209)
\t(generator "kicad_symbol_editor")
\t(generator_version "9.0")'''

    if old_header in content:
        content = content.replace(old_header, new_header)
        modified = True

    # Fix 2: Remove (id X) from properties (KiCAD 6 format)
    new_content = re.sub(r'\(id \d+\) ', '', content)
    if new_content != content:
        content = new_content
        modified = True

    if modified:
        with open(sym_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed library format for KiCAD 9: {sym_file}")


def show_summary():
    """Show what was downloaded."""
    print("\n" + "=" * 50)
    print("Library Summary")
    print("=" * 50)
    print(f"Location: {OUTPUT_DIR}")

    sym_file = OUTPUT_DIR / "symbol" / f"{SYMBOL_LIB}.kicad_sym"
    if sym_file.exists():
        size = sym_file.stat().st_size / 1024
        print(f"Symbol library: {sym_file.name} ({size:.1f} KB)")
    else:
        print(f"Symbol library: NOT FOUND")

    fp_dir = OUTPUT_DIR / FOOTPRINT_LIB
    if fp_dir.exists():
        fp_files = list(fp_dir.glob("*.kicad_mod"))
        print(f"Footprint library: {FOOTPRINT_LIB}/ ({len(fp_files)} footprints)")
    else:
        print(f"Footprint library: NOT FOUND")

    models_dir = OUTPUT_DIR / FOOTPRINT_LIB / "packages3d"
    if models_dir.exists():
        step_files = list(models_dir.glob("*.step"))
        print(f"3D models: packages3d/ ({len(step_files)} STEP files)")

    if INDEX_FILE.exists():
        index = load_index()
        print(f"Index: {len(index.get('parts', {}))} LCSC parts tracked")

    print("\n" + "=" * 50)
    print("To use in KiCAD:")
    print("  1. Run with --register flag to add to global libraries")
    print("     Or manually: Preferences > Manage Symbol/Footprint Libraries")
    print("  2. After opening schematic, run:")
    print("     Tools > Update Schematic from Symbol Libraries...")
    print("     (This embeds symbol definitions in the schematic)")


def main():
    parser = argparse.ArgumentParser(description="Download JLCPCB symbols/footprints")
    parser.add_argument("--force", action="store_true", help="Re-download all parts")
    parser.add_argument("--register", action="store_true", help="Register in global KiCAD library tables")
    parser.add_argument("--allow-missing", action="store_true", help="Proceed even if some parts are missing downloads (not recommended)")
    args = parser.parse_args()

    print("JLCPCB Library Downloader")
    print("=" * 50)
    print(f"Library location: {OUTPUT_DIR}")

    if not PARTS_JSON.exists():
        print(f"\nError: {PARTS_JSON} not found")
        print("Run assign_designators.py first")
        return 1

    import shutil
    global JLC2KICAD_EXE
    jlc2kicad_path = JLC2KICAD_EXE if Path(JLC2KICAD_EXE).exists() else shutil.which(JLC2KICAD_EXE)
    if not jlc2kicad_path:
        print(f"\nError: JLC2KiCadLib not found at configured path: {JLC2KICAD_EXE}")
        print("Install via: pip install JLC2KiCadLib")
        return 1
    JLC2KICAD_EXE = jlc2kicad_path
    print(f"Using JLC2KiCadLib: {JLC2KICAD_EXE}")

    print(f"\nLoading parts from: {PARTS_JSON}")
    lcsc_parts = load_parts()
    overrides = load_overrides()

    if not lcsc_parts:
        print("Error: No LCSC parts found in JSON")
        print("Ask the LLM to ensure parts_options.csv has selections and rerun assign_designators.py.")
        return 1

    print(f"Found {len(lcsc_parts)} unique LCSC parts in project:")
    for lcsc, info in lcsc_parts.items():
        # Sanitize MPN for console output (remove non-ASCII)
        mpn = info['mpn'].encode('ascii', 'replace').decode('ascii')
        print(f"  {lcsc}: {', '.join(info['designators'])} ({mpn})")

    index = load_index()
    existing_in_index = set(index.get("parts", {}).keys())
    existing_in_lib = get_existing_symbols()
    existing = existing_in_index | set(existing_in_lib.keys())

    needed = set(lcsc_parts.keys())
    # Apply overrides: treat overridden parts as present
    overridden = {lcsc for lcsc, ov in overrides.items() if ov.get("footprint_lib_id") or ov.get("symbol_lib_id")}
    existing |= overridden

    if args.force:
        to_download = list(needed)
        print(f"\n--force flag: Re-downloading all {len(to_download)} parts")
    else:
        already_have = needed & existing
        to_download = list(needed - existing)

        if already_have:
            print(f"\nAlready in library ({len(already_have)}):")
            for lcsc in sorted(already_have):
                designators = lcsc_parts.get(lcsc, {}).get("designators", [])
                print(f"  {lcsc}: {', '.join(designators)}")

        if to_download:
            print(f"\nNeed to download ({len(to_download)}):")
            for lcsc in sorted(to_download):
                designators = lcsc_parts.get(lcsc, {}).get("designators", [])
                print(f"  {lcsc}: {', '.join(designators)}")
        else:
            print("\nAll parts already in library!")

    if to_download:
        success = download_parts(to_download, index)
    else:
        success = True

    # Handle missing parts with overrides
    missing_parts = []
    if not success or to_download:
        # Any parts still not in index or overrides?
        remaining = needed - (existing | set(index.get("parts", {}).keys()))
        for lcsc in sorted(remaining):
            info = lcsc_parts.get(lcsc, {})
            missing_parts.append({
                "lcsc": lcsc,
                "designators": info.get("designators", []),
                "mpn": info.get("mpn", ""),
                "semantic_name": info.get("semantic_name", ""),
                "symbol_lib_id": overrides.get(lcsc, {}).get("symbol_lib_id", ""),
                "footprint_lib_id": overrides.get(lcsc, {}).get("footprint_lib_id", ""),
                "llm_prompt": (
                    "Provide symbol_lib_id and footprint_lib_id for this part. "
                    "Use existing KiCad libraries or custom lib. Keep lib_ids consistent with generate_schematic expectations."
                )
            })

    if missing_parts:
        save_missing_parts({"missing": missing_parts})
        if not args.allow_missing:
            print("\nError: Some parts are missing downloads/overrides. See missing_parts.yaml.")
            return 1

    if success:
        # Fix library format for KiCAD 9 compatibility
        print("\nFixing library format for KiCAD 9...")
        fix_library_for_kicad9()

        if args.register:
            print("\nRegistering libraries in KiCAD...")
            register_global_libraries()

        show_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
