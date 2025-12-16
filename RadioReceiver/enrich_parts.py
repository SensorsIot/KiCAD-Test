#!/usr/bin/env python3
"""
Enrich parts from parts.yaml with JLCPCB options.
Outputs CSV for engineer review and selection.

Usage:
    python enrich_parts.py

Output:
    parts_options.csv - Multiple options per part for engineer selection
"""

import yaml
import csv
import requests
import time
from collections import defaultdict
from pathlib import Path

# Known LCSC codes for parts that may not search well (defaults; override via parts.yaml lcsc_hint)
KNOWN_LCSC = {
    "ESP32-S3-MINI-1-N8": "C2913206",
    "TP4056": "C16581",
    "AMS1117-3.3": "C6186",
    "SI4735-D60-GU": "C195417",
    "WS2812B-B": "C2761795",
    "TYPE-C-31-M-12": "C393939",
    "JST-PH-2P": "C131337",
    "PJ-327A": "C145819",
    "Header-1x04": "C2337",
    "TS-1102S": "C127509",
    "EC11E18244A5": "C255515",
    "32.768kHz": "C32346",
    # Generic protection diode (single-line ESD, SOD-323)
    "ESD_Diode": "C112644",
}

# Known LCSC for passive values
PASSIVE_LCSC = {
    "5.1k_0603": "C23186",
    "2k_0603": "C22975",
    "10k_0603": "C25804",
    "4.7k_0603": "C23162",
    "100R_0603": "C22775",
    "10uF_0805": "C15850",
    "22uF_0805": "C45783",
    "100nF_0603": "C14663",
    "22pF_0603": "C1653",
}


def search_jlcpcb(query: str, limit: int = 5) -> list:
    """Search jlcsearch API for parts."""
    url = "https://jlcsearch.tscircuit.com/api/search"
    params = {"q": query, "limit": limit}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("components", [])
    except Exception as e:
        print(f"  Search error for '{query}': {e}")
        return []


def get_lcsc_details(lcsc_code: str) -> dict:
    """Get details for a known LCSC code."""
    # Strip C prefix if present for API
    code = lcsc_code.lstrip("C")

    try:
        # Search by LCSC code
        results = search_jlcpcb(lcsc_code, limit=1)
        if results:
            return results[0]
    except:
        pass

    return None


def build_query(part: dict) -> str:
    """Build search query from part info."""
    if "search_query" in part:
        return part["search_query"]
    if "part" in part:
        return part["part"]
    elif "value" in part:
        # For passives, combine value and package
        return f"{part['value']} {part.get('package', '')}"
    return part.get("name", "")


def sanitize_ascii(value: str, fallback: str = "") -> str:
    """Return ASCII-safe text; fall back to provided default on non-ASCII."""
    if value is None:
        return fallback
    try:
        encoded = value.encode("ascii", "ignore").decode("ascii")
    except Exception:
        return fallback
    encoded = encoded.strip()
    return encoded if encoded else fallback


def enrich_parts(parts_yaml: Path, output_csv: Path):
    """Read parts.yaml, search JLCPCB, output CSV with options."""

    # Load parts
    with open(parts_yaml, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    components = data.get("components", [])
    if not isinstance(components, list):
        raise ValueError(
            "parts.yaml does not contain a list under 'components'. "
            "Ask the LLM to regenerate parts.yaml with a top-level 'components' list."
        )
    print(f"Loaded {len(components)} components from {parts_yaml.name}")

    # CSV rows
    rows = []

    for part in components:
        if "name" not in part:
            raise ValueError(
                "Component entry missing 'name'. "
                "Ask the LLM to regenerate parts.yaml ensuring every component has a name."
            )
        name = part["name"]
        if "part" not in part and "value" not in part:
            raise ValueError(
                f"Component '{name}' missing both 'part' and 'value'. "
                "Ask the LLM to regenerate parts.yaml with either 'part' (for actives/connectors) "
                "or 'value' (for passives) plus 'package'."
            )
        query = build_query(part)
        print(f"\nSearching: {name} ({query})")

        # Skip search if explicitly requested
        if part.get("skip_search"):
            lcsc_hint = part.get("lcsc_hint", "NOT_FOUND")
            rows.append({
                "name": name,
                "query": query,
                "option": 1,
                "lcsc": lcsc_hint,
                "mpn": part.get("part", part.get("value", "")),
                "package": sanitize_ascii(part.get("package", ""), part.get("package", "")),
                "stock": "",
                "price": "",
                "is_basic": "",
                "is_preferred": "",
                "selected": "",
            })
            print(f"  Skipped search for {name} (skip_search=true, lcsc_hint={lcsc_hint})")
            continue

        # Get known LCSC if available
        known_lcsc = None
        if "part" in part and part["part"] in KNOWN_LCSC:
            known_lcsc = KNOWN_LCSC[part["part"]]
        elif "value" in part:
            key = f"{part['value']}_{part.get('package', '')}"
            known_lcsc = PASSIVE_LCSC.get(key)
        # Explicit override from parts.yaml
        if part.get("lcsc_hint"):
            known_lcsc = part["lcsc_hint"]

        # Search API
        results = search_jlcpcb(query, limit=5)

        # If no results but we have known LCSC, try searching by LCSC
        if not results and known_lcsc and known_lcsc != "NOT_FOUND":
            print(f"  No results, trying known LCSC: {known_lcsc}")
            details = get_lcsc_details(known_lcsc)
            if details:
                results = [details]

        # If still no results, add placeholder with known LCSC
        if not results:
            if known_lcsc and known_lcsc != "NOT_FOUND":
                rows.append({
                    "name": name,
                    "query": query,
                    "option": 1,
                    "lcsc": known_lcsc,
                    "mpn": part.get("part", part.get("value", "")),
                    "package": part.get("package", ""),
                    "stock": "unknown",
                    "price": "unknown",
                    "is_basic": "",
                    "is_preferred": "",
                    "selected": "X",  # Pre-select known parts
                })
                print(f"  Added known LCSC: {known_lcsc}")
            else:
                missing_entry = {
                    "name": name,
                    "query": query,
                    "lcsc_hint": part.get("lcsc_hint", ""),
                    "mpn": part.get("part", part.get("value", "")),
                    "package": part.get("package", ""),
                    "reason": "No search results and no lcsc_hint/skip_search",
                    "llm_prompt": "Provide lcsc_hint or set skip_search:true in parts.yaml for this part.",
                }
                rows.append({
                    "name": name,
                    "query": query,
                    "option": 1,
                    "lcsc": "NOT_FOUND",
                    "mpn": "",
                    "package": "",
                    "stock": "",
                    "price": "",
                    "is_basic": "",
                    "is_preferred": "",
                    "selected": "",
                })
                missing.append(missing_entry)
                print(f"  WARNING: No results found; added to missing list")
            continue

        # Add all options
        for i, result in enumerate(results, 1):
            lcsc = result.get("lcsc", "")
            if isinstance(lcsc, int):
                lcsc = f"C{lcsc}"

            # Pre-select first option or known LCSC
            selected = ""
            if i == 1:
                selected = "X"
            elif known_lcsc and lcsc == known_lcsc:
                selected = "X"
                # Clear previous selection
                for row in rows:
                    if row["name"] == name:
                        row["selected"] = ""

            rows.append({
                "name": name,
                "query": query,
                "option": i,
                "lcsc": lcsc,
                "mpn": sanitize_ascii(result.get("mfr", ""), part.get("part", "")),
                "package": sanitize_ascii(result.get("package", ""), part.get("package", "")),
                "stock": result.get("stock", ""),
                "price": result.get("price", ""),
                "is_basic": "yes" if result.get("is_basic") else "",
                "is_preferred": "yes" if result.get("is_preferred") else "",
                "selected": selected,
            })

        print(f"  Found {len(results)} options")

        # Rate limit
        time.sleep(0.3)

    # Write CSV
    fieldnames = ["name", "query", "option", "lcsc", "mpn", "package",
                  "stock", "price", "is_basic", "is_preferred", "selected", "review_note"]

    # Add reviewer notes after collecting all rows
    name_counts = defaultdict(int)
    selection_counts = defaultdict(int)
    for row in rows:
        name_counts[row["name"]] += 1
        if str(row.get("selected", "")).strip().upper() == "X":
            selection_counts[row["name"]] += 1

    for row in rows:
        name = row["name"]
        selected = str(row.get("selected", "")).strip().upper() == "X"
        if row["lcsc"] == "NOT_FOUND":
            note = "No LCSC; ask LLM to add lcsc_hint or mark DNP"
        elif name_counts[name] > 1:
            if selection_counts[name] == 0:
                note = "Multiple options; choose one and set selected='X'"
            elif selection_counts[name] > 1:
                note = "Multiple rows selected; keep one 'X' only"
            else:
                note = "Selected option; other rows for this part should stay blank"
        else:
            note = "Single option; verify package/stock"
        row["review_note"] = note

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'='*50}")
    print(f"Output: {output_csv}")
    print(f"Total rows: {len(rows)}")
    print(f"\nNext step: Review CSV, mark selections with 'X', save file")

    # Write missing parts report if any
    if missing:
        missing_path = Path(output_csv).with_name("missing_parts_enrich.yaml")
        with open(missing_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"missing": missing}, f, sort_keys=False)
        print(f"\nMissing parts written to {missing_path}")
        print("Ask the LLM to update parts.yaml with lcsc_hint or skip_search for these entries.")


def main():
    script_dir = Path(__file__).parent
    parts_yaml = script_dir / "parts.yaml"
    output_csv = script_dir / "parts_options.csv"

    if not parts_yaml.exists():
        print(f"Error: {parts_yaml} not found")
        return

    enrich_parts(parts_yaml, output_csv)


if __name__ == "__main__":
    main()
