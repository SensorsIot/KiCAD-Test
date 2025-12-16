#!/usr/bin/env python3
"""
Assign designators to parts based on engineer's CSV selections.

Usage:
    python assign_designators.py

Input:
    parts.yaml - Component list with quantities
    parts_options.csv - Engineer's selections (marked with X)

Output:
    parts_with_designators.json - Mapping of semantic names to designators
"""

import yaml
import csv
import json
from pathlib import Path
from collections import defaultdict


def load_parts_yaml(path: Path) -> dict:
    """Load parts.yaml and return dict keyed by name."""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    parts = {}
    for comp in data.get("components", []):
        name = comp["name"]
        quantity = comp.get("quantity", 1)
        if not isinstance(quantity, int) or quantity < 1:
            raise ValueError(
                f"Invalid quantity for '{name}': {quantity!r} (must be positive integer). "
                "Ask the LLM to regenerate parts.yaml with integer quantities."
            )
        parts[name] = {
            "prefix": comp.get("prefix", "X"),
            "quantity": quantity,
            "part": comp.get("part", ""),
            "value": comp.get("value", ""),
            "package": comp.get("package", ""),
            "description": comp.get("description", ""),
        }
    return parts


def load_csv_selections(path: Path) -> dict:
    """Load CSV and return selected parts keyed by name."""
    selections = {}

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        required = {"name", "selected", "lcsc", "mpn", "package", "stock", "price"}
        missing_cols = required - set(reader.fieldnames or [])
        if missing_cols:
            raise ValueError(
                "CSV is missing required columns: "
                f"{sorted(missing_cols)}. Ask the LLM to regenerate parts_options.csv "
                "with headers: name,selected,lcsc,mpn,package,stock,price,is_basic,is_preferred"
            )

        for row in reader:
            # Only process selected rows
            if row.get("selected", "").strip().upper() == "X":
                name = row["name"]
                # Keep first selection per name (in case of duplicates)
                if name not in selections:
                    selections[name] = {
                        "lcsc": row["lcsc"],
                        "mpn": row["mpn"],
                        "package": row["package"],
                        "stock": row["stock"],
                        "price": row["price"],
                        "is_basic": row.get("is_basic", "").strip().lower() == "yes",
                        "is_preferred": row.get("is_preferred", "").strip().lower() == "yes",
                    }
                else:
                    raise ValueError(
                        f"Duplicate selection for '{name}' in CSV; only one row may be marked selected. "
                        "Ask the LLM to regenerate parts_options.csv so each part has exactly one 'selected' row."
                    )

    return selections


def assign_designators(parts: dict, selections: dict) -> dict:
    """
    Assign designators based on prefix and quantity.

    Returns dict mapping semantic name to:
    - designators: list of assigned designators
    - lcsc: LCSC part number
    - mpn: manufacturer part number
    - other fields from selection
    """
    # Track next number per prefix
    prefix_counters = defaultdict(lambda: 1)

    result = {}

    # Process in order of parts.yaml to maintain consistent numbering
    for name, part_info in parts.items():
        prefix = part_info["prefix"]
        quantity = part_info["quantity"]

        # Get selection data
        selection = selections.get(name, {})
        if not selection:
            print(f"WARNING: No selection for '{name}' - using placeholder")
            selection = {"lcsc": "NOT_SELECTED", "mpn": "", "package": ""}

        # Assign designators
        designators = []
        for _ in range(quantity):
            num = prefix_counters[prefix]
            designators.append(f"{prefix}{num}")
            prefix_counters[prefix] += 1

        if len(designators) != quantity:
            raise ValueError(
                f"Designator count mismatch for '{name}': expected {quantity}, got {len(designators)}. "
                "Ask the LLM to regenerate parts.yaml with correct quantities."
            )

        result[name] = {
            "designators": designators,
            "lcsc": selection.get("lcsc", ""),
            "mpn": selection.get("mpn", ""),
            "package": selection.get("package", part_info.get("package", "")),
            "value": part_info.get("value", ""),
            "description": part_info.get("description", ""),
            "is_basic": selection.get("is_basic", False),
            "is_preferred": selection.get("is_preferred", False),
        }

    return result


def main():
    script_dir = Path(__file__).parent
    parts_yaml = script_dir / "parts.yaml"
    csv_path = script_dir / "parts_options.csv"
    output_json = script_dir / "parts_with_designators.json"

    # Check inputs exist
    if not parts_yaml.exists():
        print(f"Error: {parts_yaml} not found")
        return

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        print("Run enrich_parts.py first, then mark selections in CSV")
        return

    # Load data
    print(f"Loading parts from: {parts_yaml.name}")
    parts = load_parts_yaml(parts_yaml)
    print(f"  Found {len(parts)} component types")

    print(f"Loading selections from: {csv_path.name}")
    selections = load_csv_selections(csv_path)
    print(f"  Found {len(selections)} selected parts")

    # Check for missing selections
    missing = set(parts.keys()) - set(selections.keys())
    if missing:
        raise ValueError(
            f"Missing selections for: {sorted(missing)}. "
            "Ask the LLM to regenerate parts_options.csv with exactly one row marked selected='X' for each part in parts.yaml."
        )
    # Check for selections that don't map to a part
    extra = set(selections.keys()) - set(parts.keys())
    if extra:
        raise ValueError(
            f"Selections found for unknown parts: {sorted(extra)}. "
            "Ask the LLM to regenerate parts_options.csv so it only contains parts from parts.yaml."
        )

    # Assign designators
    print("\nAssigning designators...")
    result = assign_designators(parts, selections)

    # Count total components
    total = sum(len(v["designators"]) for v in result.values())
    print(f"  Total components: {total}")

    # Show summary by prefix
    prefix_summary = defaultdict(list)
    for name, data in result.items():
        for des in data["designators"]:
            prefix = ''.join(c for c in des if c.isalpha())
            prefix_summary[prefix].append(des)

    print("\nDesignator summary:")
    for prefix in sorted(prefix_summary.keys()):
        items = prefix_summary[prefix]
        print(f"  {prefix}: {items[0]}-{items[-1]} ({len(items)} parts)")

    # Save output
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\nOutput: {output_json}")
    print("\nNext step: Run download_jlcpcb_libs.py to get symbols")


if __name__ == "__main__":
    main()
