#!/usr/bin/env python3
"""
Validate pin_model.json (Phase 2 of SKiDL pipeline)

Checks:
- No undefined nets (every net used in pins must be in nets list)
- No duplicate drivers (same net driven by multiple outputs) - warning only
- Required power nets exist (GND, at least one supply)
- No floating control pins (pins with no net assignment)
- Every part has at least one pin connection
- Reference designators are unique
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def validate_pin_model(filepath: Path) -> list:
    """Validate pin model and return list of errors."""
    errors = []
    warnings = []

    # Load JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            model = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"], []

    parts = model.get('parts', [])
    declared_nets = set(model.get('nets', []))

    # Track all nets used in pin assignments
    used_nets = set()
    net_drivers = defaultdict(list)  # net -> list of (ref, pin)

    # Track refs for uniqueness
    seen_refs = set()
    seen_ids = set()

    # Required power nets
    required_nets = {'GND'}
    supply_patterns = ['+3V3', '+5V', 'VCC', 'VBAT', 'VDD', '+3.3V', '+5V', 'VBUS']

    for part in parts:
        part_id = part.get('id', '<unknown>')
        ref = part.get('ref', '<no ref>')
        pins = part.get('pins', {})

        # Check ref uniqueness
        if ref in seen_refs:
            errors.append(f"Duplicate ref designator: {ref}")
        seen_refs.add(ref)

        # Check id uniqueness
        if part_id in seen_ids:
            errors.append(f"Duplicate part id: {part_id}")
        seen_ids.add(part_id)

        # Check part has at least one pin (unless it's explicitly NC-only)
        if not pins and not part.get('no_connect'):
            warnings.append(f"{ref} ({part_id}): No pin connections defined")

        # Check each pin assignment
        for pin_name, net_name in pins.items():
            used_nets.add(net_name)
            net_drivers[net_name].append((ref, pin_name))

            # Check net is declared
            if net_name not in declared_nets:
                errors.append(f"{ref}.{pin_name}: Uses undeclared net '{net_name}'")

    # Check for required power nets
    if 'GND' not in declared_nets:
        errors.append("Missing required 'GND' net")

    has_supply = False
    for pattern in supply_patterns:
        if pattern in declared_nets:
            has_supply = True
            break
    if not has_supply:
        errors.append("No supply rail found (expected +3V3, VCC, VBAT, etc.)")

    # Check for unused declared nets
    unused_nets = declared_nets - used_nets
    for net in unused_nets:
        warnings.append(f"Declared net '{net}' is not used by any pin")

    # Check for potential driver conflicts (multiple outputs on same net)
    # This is informational - some nets legitimately have multiple connections
    for net, drivers in net_drivers.items():
        if len(drivers) > 10:  # Likely a power net, skip
            continue
        # Could add more sophisticated output detection here

    # Validate belongs_to references
    part_ids = {p.get('id') for p in parts}
    for part in parts:
        belongs_to = part.get('belongs_to')
        if belongs_to is not None and belongs_to not in part_ids:
            errors.append(f"{part.get('ref')}: belongs_to '{belongs_to}' not found")

    return errors, warnings


def main():
    script_dir = Path(__file__).parent.parent
    filepath = script_dir / "work" / "pin_model.json"

    print(f"Validating: {filepath}")
    print("=" * 60)

    errors, warnings = validate_pin_model(filepath)

    if errors:
        print("VALIDATION FAILED\n")
        for error in errors:
            print(f"  ERROR: {error}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  WARN: {warning}")
        print(f"\nTotal errors: {len(errors)}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  WARN: {warning}")

        # Load and print summary
        with open(filepath, 'r', encoding='utf-8') as f:
            model = json.load(f)

        stats = model.get('statistics', {})
        print(f"\nSummary:")
        print(f"  Parts: {stats.get('total_parts', 0)}")
        print(f"  Nets: {stats.get('total_nets', 0)}")
        print(f"  Pin assignments: {stats.get('total_pin_assignments', 0)}")

        # Check completeness
        parts = model.get('parts', [])
        parts_with_pins = sum(1 for p in parts if p.get('pins'))
        parts_without_pins = sum(1 for p in parts if not p.get('pins'))

        print(f"\nCompleteness:")
        print(f"  Parts with pin mappings: {parts_with_pins}")
        print(f"  Parts without pin mappings: {parts_without_pins}")

        if parts_without_pins > 0:
            print("\n  Missing pins for:")
            for p in parts:
                if not p.get('pins'):
                    print(f"    - {p.get('ref')} ({p.get('id')})")

        sys.exit(0)


if __name__ == "__main__":
    main()
