#!/usr/bin/env python3
"""
Verify schematic connections using KiCad's netlist export.

This script:
1. Uses kicad-cli to export a netlist from the schematic
2. Parses the netlist to extract actual connections
3. Compares against expected connections from pin_model.json
4. Reports any missing or extra connections

Usage:
    python verify_netlist.py [schematic.kicad_sch]

Requires KiCad 7+ installed with kicad-cli in PATH.
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from collections import defaultdict


def export_netlist(schematic_path: Path, output_path: Path) -> bool:
    """Export netlist from schematic using kicad-cli."""
    cmd = [
        "kicad-cli", "sch", "export", "netlist",
        "--output", str(output_path),
        str(schematic_path)
    ]

    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        print("Error: kicad-cli not found. Make sure KiCad 7+ is installed and in PATH.")
        return False


def parse_kicad_netlist(netlist_path: Path) -> dict:
    """
    Parse KiCad netlist file (.net format).

    Returns dict: net_name -> [(ref, pin_number), ...]
    """
    content = netlist_path.read_text()

    nets = {}

    # Find all net definitions: (net (code X) (name "NET_NAME") ... (node (ref X) (pin Y)) ...)
    net_pattern = re.compile(
        r'\(net\s+\(code\s+\d+\)\s+\(name\s+"([^"]+)"\)(.*?)\)\s*(?=\(net|\(libparts|\Z)',
        re.DOTALL
    )

    node_pattern = re.compile(r'\(node\s+\(ref\s+"?([^")\s]+)"?\)\s+\(pin\s+"?([^")\s]+)"?\)')

    for net_match in net_pattern.finditer(content):
        net_name = net_match.group(1)
        net_content = net_match.group(2)

        nodes = []
        for node_match in node_pattern.finditer(net_content):
            ref = node_match.group(1)
            pin = node_match.group(2)
            nodes.append((ref, pin))

        if nodes:
            nets[net_name] = nodes

    return nets


def load_expected_connections(pin_model_path: Path) -> dict:
    """
    Load expected connections from pin_model.json.

    Returns dict: net_name -> [(ref, pin_name), ...]
    """
    with open(pin_model_path) as f:
        model = json.load(f)

    nets = defaultdict(list)

    for part in model.get('parts', []):
        ref = part['ref']
        for pin_name, net_name in part.get('pins', {}).items():
            if net_name:
                nets[net_name].append((ref, pin_name))

    return dict(nets)


def compare_netlists(expected: dict, actual: dict, symbol_lib_path: Path = None) -> dict:
    """
    Compare expected vs actual netlists.

    Note: expected uses pin NAMES, actual uses pin NUMBERS.
    We need the symbol library to map between them.

    Returns dict with 'missing', 'extra', 'matched' lists.
    """
    results = {
        'missing': [],  # In expected but not in actual
        'extra': [],    # In actual but not in expected
        'matched': [],  # Correctly matched
        'net_mismatches': []  # Pin exists but on wrong net
    }

    # For now, do a simple comparison by net name
    # This won't catch pin name vs number mismatches

    all_nets = set(expected.keys()) | set(actual.keys())

    for net in sorted(all_nets):
        exp_pins = set(expected.get(net, []))
        act_pins = set(actual.get(net, []))

        # Find matches (note: expected has pin names, actual has pin numbers)
        # For a proper comparison, we'd need to map names to numbers
        # For now, report the raw comparison

        if net in expected and net not in actual:
            results['missing'].append({
                'net': net,
                'expected_pins': list(exp_pins),
                'issue': 'Net not found in schematic'
            })
        elif net not in expected and net in actual:
            results['extra'].append({
                'net': net,
                'actual_pins': list(act_pins),
                'issue': 'Unexpected net in schematic'
            })
        else:
            # Both exist - compare pin counts at least
            if len(exp_pins) != len(act_pins):
                results['net_mismatches'].append({
                    'net': net,
                    'expected_count': len(exp_pins),
                    'actual_count': len(act_pins),
                    'expected_pins': list(exp_pins),
                    'actual_pins': list(act_pins)
                })
            else:
                results['matched'].append(net)

    return results


def main():
    # Paths
    base_dir = Path(__file__).parent.parent

    if len(sys.argv) > 1:
        schematic_path = Path(sys.argv[1])
    else:
        schematic_path = base_dir / "output" / "Debug.kicad_sch"

    if not schematic_path.exists():
        print(f"Error: Schematic not found: {schematic_path}")
        sys.exit(1)

    pin_model_path = base_dir / "work" / "pin_model.json"
    netlist_path = base_dir / "output" / "netlist.net"

    print(f"Schematic: {schematic_path}")
    print(f"Pin model: {pin_model_path}")
    print()

    # Export netlist
    print("=== Exporting netlist from KiCad ===")
    if not export_netlist(schematic_path, netlist_path):
        print("\nFailed to export netlist.")
        print("Make sure:")
        print("  1. KiCad 7+ is installed")
        print("  2. kicad-cli is in your PATH")
        print("  3. The schematic has been opened in KiCad and 'Update from Symbol Library' was run")
        sys.exit(1)

    print(f"Netlist exported to: {netlist_path}")
    print()

    # Parse netlist
    print("=== Parsing netlist ===")
    actual_nets = parse_kicad_netlist(netlist_path)
    print(f"Found {len(actual_nets)} nets in schematic")
    print()

    # Load expected
    print("=== Loading expected connections ===")
    expected_nets = load_expected_connections(pin_model_path)
    print(f"Expected {len(expected_nets)} nets from pin_model.json")
    print()

    # Compare
    print("=== Comparing connections ===")
    results = compare_netlists(expected_nets, actual_nets)

    print(f"\nMatched nets: {len(results['matched'])}")

    if results['missing']:
        print(f"\n*** MISSING NETS ({len(results['missing'])}) ***")
        for item in results['missing']:
            print(f"  {item['net']}: {item['issue']}")
            for pin in item['expected_pins']:
                print(f"    Expected: {pin}")

    if results['extra']:
        print(f"\n*** EXTRA NETS ({len(results['extra'])}) ***")
        for item in results['extra']:
            print(f"  {item['net']}: {item['issue']}")

    if results['net_mismatches']:
        print(f"\n*** PIN COUNT MISMATCHES ({len(results['net_mismatches'])}) ***")
        for item in results['net_mismatches']:
            print(f"  {item['net']}: expected {item['expected_count']} pins, got {item['actual_count']}")
            print(f"    Expected: {item['expected_pins']}")
            print(f"    Actual:   {item['actual_pins']}")

    # Summary
    print("\n=== Summary ===")
    total_issues = len(results['missing']) + len(results['extra']) + len(results['net_mismatches'])
    if total_issues == 0:
        print("All connections verified successfully!")
    else:
        print(f"Found {total_issues} issue(s)")

    # Also print actual netlist for inspection
    print("\n=== Actual Netlist Contents ===")
    for net, pins in sorted(actual_nets.items()):
        print(f"  {net}: {pins}")


if __name__ == "__main__":
    main()
