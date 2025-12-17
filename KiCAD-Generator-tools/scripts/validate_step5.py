#!/usr/bin/env python3
"""
Validate step5_connections.yaml

Checks:
- YAML parses correctly
- Every connection references an existing component ID (from step4)
- No single-pin nets unless marked as test point or NC
- Required power nets exist (GND, at least one supply rail)
- No duplicate pin usage (same pin on multiple nets)
"""

import sys
import yaml
from pathlib import Path


def validate(filepath: Path, parts_filepath: Path) -> list:
    """Validate step5 file and return list of errors."""
    errors = []

    # Check file exists
    if not filepath.exists():
        return [f"File not found: {filepath}"]

    # Parse YAML
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not data:
        return ["File is empty"]

    # Load parts from step4 for reference validation
    valid_component_ids = set()
    if parts_filepath.exists():
        try:
            with open(parts_filepath, 'r', encoding='utf-8') as f:
                parts_data = yaml.safe_load(f)
            if parts_data and 'parts' in parts_data:
                for part in parts_data['parts']:
                    if isinstance(part, dict) and 'id' in part:
                        valid_component_ids.add(part['id'])
        except yaml.YAMLError:
            errors.append("WARNING: Could not parse step4_final_parts.yaml for reference validation")

    # Check nets exists
    if 'nets' not in data:
        return ["Missing 'nets' key"]

    nets = data['nets']
    if not isinstance(nets, dict):
        return ["'nets' must be a dictionary"]

    if len(nets) == 0:
        return ["No nets defined - cannot have empty netlist"]

    # Track all pin references for duplicate detection
    pin_to_nets = {}  # pin_ref -> list of net names

    # Collect test points and no_connect for single-pin exceptions
    test_point_nets = set()
    nc_pins = set()

    if 'test_points' in data:
        for tp in data.get('test_points', []):
            if isinstance(tp, dict) and 'net' in tp:
                test_point_nets.add(tp['net'])

    if 'no_connect' in data:
        for nc in data.get('no_connect', []):
            if isinstance(nc, dict):
                comp = nc.get('component', '')
                pin = nc.get('pin', '')
                if comp and pin:
                    nc_pins.add(f"{comp}.{pin}")

    # Validate each net
    for net_name, connections in nets.items():
        if not isinstance(connections, list):
            errors.append(f"Net '{net_name}': connections must be a list")
            continue

        # Check for single-pin nets
        if len(connections) < 2 and net_name not in test_point_nets:
            errors.append(f"Net '{net_name}': Only {len(connections)} connection(s) - needs at least 2 (or mark as test_point)")

        # Validate each connection
        for conn in connections:
            if not isinstance(conn, str):
                errors.append(f"Net '{net_name}': Connection must be string, got {type(conn).__name__}")
                continue

            # Parse component.pin format
            if '.' not in conn:
                errors.append(f"Net '{net_name}': Invalid connection format '{conn}' - must be 'component_id.PIN'")
                continue

            parts = conn.split('.', 1)
            component_id = parts[0]
            pin_name = parts[1] if len(parts) > 1 else ''

            # Check component exists (if we have parts data)
            if valid_component_ids and component_id not in valid_component_ids:
                errors.append(f"Net '{net_name}': Unknown component '{component_id}' in connection '{conn}'")

            # Track for duplicate detection
            if conn not in pin_to_nets:
                pin_to_nets[conn] = []
            pin_to_nets[conn].append(net_name)

    # Check for duplicate pin usage
    for pin_ref, net_names in pin_to_nets.items():
        if len(net_names) > 1:
            errors.append(f"Duplicate pin usage: '{pin_ref}' appears in multiple nets: {net_names}")

    # Check required power nets
    net_names_upper = {n.upper() for n in nets.keys()}
    if 'GND' not in net_names_upper:
        errors.append("Missing required 'GND' net")

    # Check for at least one supply rail (common patterns)
    supply_patterns = ['+3V3', '+5V', 'VCC', 'VBAT', '+3.3V', '+5.0V', 'VDD', '+12V', '+1V8']
    has_supply = False
    for pattern in supply_patterns:
        if pattern.upper() in net_names_upper or pattern in nets:
            has_supply = True
            break
    if not has_supply:
        errors.append("WARNING: No common supply rail found (expected one of: +3V3, +5V, VCC, VBAT, VDD, etc.)")

    # Validate no_connect entries reference valid components
    if valid_component_ids and 'no_connect' in data:
        for i, nc in enumerate(data.get('no_connect', [])):
            if isinstance(nc, dict):
                comp = nc.get('component', '')
                if comp and comp not in valid_component_ids:
                    errors.append(f"no_connect[{i}]: Unknown component '{comp}'")

    return errors


def main():
    script_dir = Path(__file__).parent.parent
    filepath = script_dir / "work" / "step5_connections.yaml"
    parts_filepath = script_dir / "work" / "step4_final_parts.yaml"

    print(f"Validating: {filepath}")
    print("=" * 60)

    errors = validate(filepath, parts_filepath)

    # Separate warnings from errors
    warnings = [e for e in errors if e.startswith("WARNING")]
    real_errors = [e for e in errors if not e.startswith("WARNING")]

    if real_errors:
        print("VALIDATION FAILED\n")
        for error in real_errors:
            print(f"  {error}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  {warning}")
        print(f"\nTotal errors: {len(real_errors)}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  {warning}")

        # Print summary
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        nets = data.get('nets', {})
        total_connections = sum(len(conns) for conns in nets.values() if isinstance(conns, list))
        nc_count = len(data.get('no_connect', []))
        tp_count = len(data.get('test_points', []))

        print(f"\nSummary: {len(nets)} nets, {total_connections} total connections")
        print(f"  - No-connect pins: {nc_count}")
        print(f"  - Test points: {tp_count}")

        # List power nets
        power_nets = [n for n in nets.keys() if any(p in n.upper() for p in ['GND', 'VCC', 'VDD', 'BAT', '+3V', '+5V', '+12V', '+1V'])]
        if power_nets:
            print(f"  - Power nets: {', '.join(power_nets)}")

        sys.exit(0)


if __name__ == "__main__":
    main()
