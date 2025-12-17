#!/usr/bin/env python3
"""
KiCAD Schematic Generation Pipeline Runner

This script orchestrates the automated steps of the pipeline:
- Step 4: Generate pin_model.json from parts + connections YAML
- Ensure all symbols exist in the library
- Step 5: Generate KiCAD schematic
- Run ERC verification

Steps 1-3 are LLM-driven and should be completed before running this script.

Usage:
    python run_pipeline.py [--skip-symbols] [--debug]
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str, cwd: Path = None) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"  Command: {' '.join(str(c) for c in cmd)}")
    print()

    result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0:
        print(f"\n  FAILED with exit code {result.returncode}")
        return False

    print(f"\n  SUCCESS")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run KiCAD schematic generation pipeline')
    parser.add_argument('--skip-symbols', action='store_true', help='Skip symbol download step')
    parser.add_argument('--debug', action='store_true', help='Generate debug schematic')
    parser.add_argument('--project', type=Path, help='Project design directory (default: parent of scripts)')
    args = parser.parse_args()

    # Determine project directory
    script_dir = Path(__file__).parent
    if args.project:
        project_dir = args.project
    else:
        # Assume scripts are in design/scripts/ or KiCAD-Generator-tools/scripts/
        project_dir = script_dir.parent

    # Check if this is the tools directory or a project directory
    if (project_dir / 'work').exists():
        design_dir = project_dir
    elif (project_dir / 'design' / 'work').exists():
        design_dir = project_dir / 'design'
    else:
        print(f"Error: Cannot find work directory in {project_dir}")
        print("  Expected: {project}/work/ or {project}/design/work/")
        return 1

    print(f"Project directory: {design_dir}")

    # Define paths
    work_dir = design_dir / 'work'
    output_dir = design_dir / 'output'
    scripts_dir = script_dir
    tools_dir = script_dir.parent  # KiCAD-Generator-tools directory

    pin_model = work_dir / 'pin_model.json'
    parts_yaml = work_dir / 'step2_parts_complete.yaml'
    connections_yaml = work_dir / 'step3_connections.yaml'

    # Use central library (shared across all projects)
    central_library = tools_dir / 'libs' / 'JLCPCB' / 'symbol' / 'JLCPCB.kicad_sym'
    if central_library.exists():
        library = central_library
    else:
        # Fall back to project-local library
        library = output_dir / 'libs' / 'JLCPCB' / 'symbol' / 'JLCPCB.kicad_sym'

    # Check required files exist
    print("\nChecking required files...")
    missing = []
    for f, name in [(parts_yaml, 'Parts YAML'), (connections_yaml, 'Connections YAML')]:
        if not f.exists():
            missing.append(f"{name}: {f}")
        else:
            print(f"  Found: {name}")

    if missing:
        print("\nMissing required files:")
        for m in missing:
            print(f"  - {m}")
        print("\nComplete Steps 1-3 (LLM steps) before running pipeline.")
        return 1

    # Step 4: Generate pin_model.json (if generate_pin_model.py exists)
    generate_pin_model = scripts_dir / 'generate_pin_model.py'
    if generate_pin_model.exists() and not pin_model.exists():
        if not run_command(
            [sys.executable, str(generate_pin_model)],
            "Step 4: Generate pin_model.json",
            cwd=design_dir
        ):
            return 1
    elif pin_model.exists():
        print(f"\n  pin_model.json already exists")
    else:
        print(f"\n  Warning: generate_pin_model.py not found, assuming pin_model.json created by LLM")

    # Check pin_model exists now
    if not pin_model.exists():
        print(f"\nError: pin_model.json not found at {pin_model}")
        print("  Create it manually or ensure generate_pin_model.py works")
        return 1

    # Ensure symbols step
    if not args.skip_symbols:
        ensure_symbols = scripts_dir / 'ensure_symbols.py'
        if ensure_symbols.exists():
            if not run_command(
                [sys.executable, str(ensure_symbols),
                 '--pin-model', str(pin_model),
                 '--library', str(library)],
                "Ensure all symbols exist in library"
            ):
                print("\nSome symbols could not be downloaded.")
                print("You may need to add them manually to the library.")
                # Continue anyway - some symbols might work
    else:
        print("\n  Skipping symbol check (--skip-symbols)")

    # Step 5: Generate schematic
    schematic_script = scripts_dir / 'kicad9_schematic.py'
    if not schematic_script.exists():
        # Try in design/scripts
        schematic_script = design_dir / 'scripts' / 'kicad9_schematic.py'

    if not schematic_script.exists():
        print(f"\nError: kicad9_schematic.py not found")
        return 1

    cmd = [sys.executable, str(schematic_script)]
    if args.debug:
        cmd.append('--debug')

    if not run_command(cmd, "Step 5: Generate KiCAD schematic", cwd=design_dir):
        return 1

    # Run ERC
    schematic = output_dir / ('Debug.kicad_sch' if args.debug else 'RadioReceiver_v3.kicad_sch')
    if schematic.exists():
        result = subprocess.run(
            ['kicad-cli', 'sch', 'erc', str(schematic), '--exit-code-violations'],
            capture_output=True,
            text=True
        )
        print(f"\n{'='*60}")
        print("  ERC Results")
        print(f"{'='*60}")
        print(result.stdout)

        # Parse error count
        if 'Errors 0' in result.stdout:
            print("  ERC PASSED - No errors!")
        else:
            print("  ERC found errors - check the report")

    print(f"\n{'='*60}")
    print("  Pipeline Complete")
    print(f"{'='*60}")
    print(f"\nOutput files:")
    print(f"  Schematic: {schematic}")
    print(f"  Debug CSV: {output_dir / 'debug.csv'}")

    return 0


if __name__ == "__main__":
    exit(main())
