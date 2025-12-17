#!/usr/bin/env python3
"""
Validate step2_parts_extended.yaml

Checks:
- YAML parses correctly
- All belongs_to references exist
- No supporting parts with belongs_to: null (except primary parts)
- Optional parts have optional: true
- Required fields present
"""

import sys
import yaml
from pathlib import Path

REQUIRED_FIELDS = ['id', 'name', 'part', 'category', 'quantity', 'belongs_to']


def validate(filepath: Path) -> list:
    """Validate step2 file and return list of errors."""
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
        errors.append("WARNING: No parts defined")

    # Collect all IDs and primary part IDs
    all_ids = set()
    primary_ids = set()

    for part in parts:
        if isinstance(part, dict):
            part_id = part.get('id')
            if part_id:
                all_ids.add(part_id)
                if part.get('belongs_to') is None:
                    primary_ids.add(part_id)

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

        # Check belongs_to reference
        belongs_to = part.get('belongs_to')
        if belongs_to is not None:
            if belongs_to not in primary_ids:
                errors.append(f"{prefix} ({part_id}): belongs_to '{belongs_to}' not found in primary parts")

            # Supporting parts should have source/purpose
            if 'purpose' not in part and 'source' not in part:
                errors.append(f"{prefix} ({part_id}): Supporting part should have 'purpose' or 'source' field")

        # Check optional field if present
        optional = part.get('optional')
        if optional is not None and not isinstance(optional, bool):
            errors.append(f"{prefix} ({part_id}): 'optional' must be true or false")

        # Check quantity is positive
        qty = part.get('quantity')
        if qty is not None:
            if not isinstance(qty, int) or qty < 1:
                errors.append(f"{prefix} ({part_id}): quantity must be positive integer")

    # Summary checks
    primary_count = len(primary_ids)
    supporting_count = len(all_ids) - primary_count

    if primary_count == 0:
        errors.append("WARNING: No primary parts (belongs_to: null) found")

    return errors


def main():
    script_dir = Path(__file__).parent.parent
    filepath = script_dir / "work" / "step2_parts_extended.yaml"

    print(f"Validating: {filepath}")
    print("=" * 60)

    errors = validate(filepath)

    if errors:
        print("VALIDATION FAILED\n")
        for error in errors:
            print(f"  ❌ {error}")
        print(f"\nTotal errors: {len(errors)}")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED")
        # Print summary
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        parts = data.get('parts', [])
        primary = sum(1 for p in parts if p.get('belongs_to') is None)
        supporting = len(parts) - primary
        print(f"\nSummary: {len(parts)} total parts")
        print(f"  - Primary parts: {primary}")
        print(f"  - Supporting parts: {supporting}")
        sys.exit(0)


if __name__ == "__main__":
    main()
