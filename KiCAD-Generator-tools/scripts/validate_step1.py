#!/usr/bin/env python3
"""
Validate step1_primary_parts.yaml

Checks:
- YAML parses correctly
- primary_parts[*].id is unique
- Each primary part has suggested_part (not empty)
- Required fields present
"""

import sys
import yaml
from pathlib import Path

REQUIRED_FIELDS = ['id', 'name', 'suggested_part', 'category', 'quantity']
VALID_CATEGORIES = ['microcontroller', 'radio', 'power', 'connector', 'ui', 'sensor', 'passive', 'other']


def validate(filepath: Path) -> list:
    """Validate step1 file and return list of errors."""
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

    # Check primary_parts exists
    if 'primary_parts' not in data:
        return ["Missing 'primary_parts' key"]

    parts = data['primary_parts']
    if not isinstance(parts, list):
        return ["'primary_parts' must be a list"]

    if len(parts) == 0:
        errors.append("WARNING: No primary parts defined")

    # Track IDs for uniqueness
    seen_ids = set()

    for i, part in enumerate(parts):
        prefix = f"primary_parts[{i}]"

        if not isinstance(part, dict):
            errors.append(f"{prefix}: Must be a dictionary")
            continue

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in part:
                errors.append(f"{prefix}: Missing required field '{field}'")

        # Check id uniqueness
        part_id = part.get('id')
        if part_id:
            if part_id in seen_ids:
                errors.append(f"{prefix}: Duplicate id '{part_id}'")
            seen_ids.add(part_id)

        # Check suggested_part not empty
        suggested = part.get('suggested_part', '')
        if not suggested or suggested.strip() == '':
            errors.append(f"{prefix} ({part_id}): suggested_part is empty")

        # Check category is valid
        category = part.get('category')
        if category and category not in VALID_CATEGORIES:
            errors.append(f"{prefix} ({part_id}): Invalid category '{category}'. Must be one of {VALID_CATEGORIES}")

        # Check quantity is positive integer
        qty = part.get('quantity')
        if qty is not None:
            if not isinstance(qty, int) or qty < 1:
                errors.append(f"{prefix} ({part_id}): quantity must be positive integer, got '{qty}'")

    return errors


def main():
    script_dir = Path(__file__).parent.parent
    filepath = script_dir / "work" / "step1_primary_parts.yaml"

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
        parts = data.get('primary_parts', [])
        print(f"\nSummary: {len(parts)} primary parts defined")
        sys.exit(0)


if __name__ == "__main__":
    main()
