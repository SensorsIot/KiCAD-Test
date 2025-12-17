#!/usr/bin/env python3
"""
Validate step4_final_parts.yaml

Checks:
- YAML parses correctly
- No unresolved TBD values
- IDs unique
- All required fields present
- Valid prefixes
"""

import sys
import yaml
from pathlib import Path

REQUIRED_FIELDS = ['id', 'name', 'part', 'package', 'prefix', 'category', 'quantity', 'belongs_to']
VALID_PREFIXES = ['R', 'C', 'U', 'D', 'J', 'SW', 'Y', 'L', 'F', 'ENC', 'ANT', 'TP', 'FB']


def validate(filepath: Path) -> list:
    """Validate step4 file and return list of errors."""
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

    # Check parts exists
    if 'parts' not in data:
        return ["Missing 'parts' key"]

    parts = data['parts']
    if not isinstance(parts, list):
        return ["'parts' must be a list"]

    if len(parts) == 0:
        return ["No parts defined - cannot have empty BOM"]

    # Track IDs for uniqueness
    seen_ids = set()

    for i, part in enumerate(parts):
        prefix = f"parts[{i}]"

        if not isinstance(part, dict):
            errors.append(f"{prefix}: Must be a dictionary")
            continue

        part_id = part.get('id', f'<no id at index {i}>')

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in part:
                errors.append(f"{prefix} ({part_id}): Missing required field '{field}'")

        # Check id uniqueness
        if part_id in seen_ids:
            errors.append(f"{prefix}: Duplicate id '{part_id}'")
        seen_ids.add(part_id)

        # Check for TBD values
        part_value = part.get('part', '')
        if 'TBD' in str(part_value).upper():
            errors.append(f"{prefix} ({part_id}): Unresolved TBD in part value '{part_value}'")

        package = part.get('package', '')
        if 'TBD' in str(package).upper():
            errors.append(f"{prefix} ({part_id}): Unresolved TBD in package '{package}'")

        # Check prefix is valid
        part_prefix = part.get('prefix', '')
        if part_prefix and part_prefix not in VALID_PREFIXES:
            errors.append(f"{prefix} ({part_id}): Invalid prefix '{part_prefix}'. Must be one of {VALID_PREFIXES}")

        # Check quantity is positive
        qty = part.get('quantity')
        if qty is not None:
            if not isinstance(qty, int) or qty < 1:
                errors.append(f"{prefix} ({part_id}): quantity must be positive integer")

        # Check lcsc_hint present (warning only)
        if 'lcsc_hint' not in part:
            errors.append(f"WARNING: {prefix} ({part_id}): Missing lcsc_hint for JLCPCB lookup")

    return errors


def main():
    script_dir = Path(__file__).parent.parent
    filepath = script_dir / "work" / "step4_final_parts.yaml"

    print(f"Validating: {filepath}")
    print("=" * 60)

    errors = validate(filepath)

    # Separate warnings from errors
    warnings = [e for e in errors if e.startswith("WARNING")]
    real_errors = [e for e in errors if not e.startswith("WARNING")]

    if real_errors:
        print("VALIDATION FAILED\n")
        for error in real_errors:
            print(f"  ❌ {error}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")
        print(f"\nTotal errors: {len(real_errors)}")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")
        # Print summary
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        parts = data.get('parts', [])
        total_qty = sum(p.get('quantity', 1) for p in parts)
        print(f"\nSummary: {len(parts)} unique parts, {total_qty} total components")

        # Count by prefix
        by_prefix = {}
        for p in parts:
            pfx = p.get('prefix', '?')
            by_prefix[pfx] = by_prefix.get(pfx, 0) + p.get('quantity', 1)
        print("By type:")
        for pfx, count in sorted(by_prefix.items()):
            print(f"  {pfx}: {count}")

        sys.exit(0)


if __name__ == "__main__":
    main()
