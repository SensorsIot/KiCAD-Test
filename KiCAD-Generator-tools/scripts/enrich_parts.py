#!/usr/bin/env python3
"""
Enrich parts candidates with JLCPCB pricing and availability data.

Input:
    design/work/step1_parts_candidates.yaml

Output:
    design/work/step2_parts_enriched.yaml

Uses the official JLCPCB BOM API to fetch:
- Stock count
- Unit price (tiered)
- Part type (Basic/Extended/Preferred)
- Package info
- Datasheet URL

Usage:
    python enrich_parts.py --input work/step1_parts_candidates.yaml --output work/step2_parts_enriched.yaml
"""

import argparse
import json
import logging
import time
import yaml
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# JLCPCB API endpoint
JLCPCB_API_URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

# Request timeout
DEFAULT_TIMEOUT = 30

# Rate limiting (be polite to API)
REQUEST_DELAY = 0.3


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict) -> None:
    """Save data to YAML file."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def search_jlcpcb(query: str, limit: int = 5) -> List[dict]:
    """
    Search official JLCPCB BOM API for parts.

    Returns list of components with:
    - lcsc: LCSC part code (e.g., "C12345")
    - mfr: Manufacturer part number
    - package: Package/footprint
    - stock: Stock count
    - price: Unit price (best tier)
    - is_basic: True if Basic part
    - is_preferred: True if Preferred part
    - description: Part description
    - datasheet: Datasheet URL
    """
    payload = {
        "keyword": query,
        "currentPage": 1,
        "pageSize": limit,
        "componentLibraryType": "",
        "stockSort": ""
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.post(JLCPCB_API_URL, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            logger.warning(f"API returned code {data.get('code')}: {data.get('message')}")
            return []

        # Extract component list from nested response
        page_info = data.get("data", {}).get("componentPageInfo", {})
        raw_components = page_info.get("list") or []

        # Transform to common format
        components = []
        for comp in raw_components:
            # Skip abolished/discontinued parts
            if comp.get("componentTypeEn") == "Abolished Device":
                continue

            # Get best price (usually the highest quantity tier)
            prices = comp.get("componentPrices") or []
            price = None
            if prices:
                # Get price for qty 10+ tier if available, else last tier
                for p in prices:
                    if p.get("startNumber", 0) >= 10:
                        price = p.get("productPrice")
                        break
                if price is None:
                    price = prices[-1].get("productPrice", "")

            lcsc_code = comp.get("componentCode", "")
            if lcsc_code and not lcsc_code.startswith("C"):
                lcsc_code = f"C{lcsc_code}"

            components.append({
                "lcsc": lcsc_code,
                "mfr": comp.get("componentModelEn", ""),
                "package": comp.get("componentSpecificationEn", ""),
                "stock": comp.get("stockCount", 0),
                "price": price,
                "is_basic": comp.get("componentLibraryType") == "base",
                "is_preferred": comp.get("preferredComponentFlag", False),
                "description": comp.get("describe", ""),
                "datasheet": comp.get("dataManualUrl", ""),
            })

        return components

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for '{query}': {e}")
        return []
    except Exception as e:
        logger.error(f"Error processing response for '{query}': {e}")
        return []


def get_part_type(component: dict) -> str:
    """Determine part type string from component flags."""
    if component.get("is_basic"):
        return "Basic"
    if component.get("is_preferred"):
        return "Preferred"
    return "Extended"


def extract_base_part_name(part_number: str) -> str:
    """
    Extract base part name for searching alternatives.
    E.g., "SI4735-D60-GU" -> "SI4735"
          "TDA1308T/N2,115" -> "TDA1308"
          "EC11J1525402" -> "EC11"
          "AMS1117-3.3" -> "AMS1117"
    """
    import re
    if not part_number:
        return ""

    # Remove common suffixes and variants
    # Split on common separators: -, /, _, space
    base = re.split(r'[-/_\s]', part_number)[0]

    # Remove trailing letters/numbers that look like variants (e.g., "T", "N2")
    # But keep the core part number
    base = re.sub(r'[A-Z]$', '', base)  # Remove single trailing letter

    return base if len(base) >= 3 else part_number


def find_best_in_stock(candidates: List[dict]) -> Optional[dict]:
    """
    Find the best candidate that is in stock.
    Preference: Basic > Preferred > Extended, then by stock level.
    """
    in_stock = [c for c in candidates if c.get("stock", 0) > 0]
    if not in_stock:
        return None

    def score(c):
        s = 0
        if c.get("is_basic"):
            s += 10000
        if c.get("is_preferred"):
            s += 5000
        s += min(c.get("stock", 0), 9999)
        return s

    return max(in_stock, key=score)


def enrich_part(part: dict) -> dict:
    """
    Enrich a single part with JLCPCB data.

    Search strategy:
    1. Search by known LCSC code (if provided)
    2. Search by exact part number
    3. If stock=0, search by BASE part name to find alternatives
    4. Collect ALL candidates and pick best in-stock option
    """
    part_id = part.get("id", "unknown")
    part_number = part.get("part_number", "")
    known_lcsc = part.get("lcsc")

    enriched = part.copy()
    enriched["jlcpcb_lookup"] = {
        "searched": True,
        "found": False,
        "search_queries": [],
        "all_candidates": [],
        "selected": None,
        "alternatives_searched": False
    }

    all_candidates = []

    # Step 1: Search by LCSC code first (most reliable)
    if known_lcsc:
        logger.info(f"  [{part_id}] Searching by LCSC: {known_lcsc}")
        results = search_jlcpcb(known_lcsc, limit=5)
        enriched["jlcpcb_lookup"]["search_queries"].append({"query": known_lcsc, "type": "lcsc"})
        all_candidates.extend(results)
        time.sleep(REQUEST_DELAY)

    # Step 2: Search by exact part number
    if part_number:
        logger.info(f"  [{part_id}] Searching by part number: {part_number}")
        results = search_jlcpcb(part_number, limit=10)
        enriched["jlcpcb_lookup"]["search_queries"].append({"query": part_number, "type": "part_number"})
        # Add results not already in candidates
        existing_lcsc = {c.get("lcsc") for c in all_candidates}
        for r in results:
            if r.get("lcsc") not in existing_lcsc:
                all_candidates.append(r)
        time.sleep(REQUEST_DELAY)

    # Step 3: If no in-stock candidates, search by BASE part name
    in_stock_count = sum(1 for c in all_candidates if c.get("stock", 0) > 0)
    if in_stock_count == 0 and part_number:
        base_name = extract_base_part_name(part_number)
        if base_name and base_name != part_number:
            logger.info(f"  [{part_id}] No stock found, searching alternatives: {base_name}")
            results = search_jlcpcb(base_name, limit=15)
            enriched["jlcpcb_lookup"]["search_queries"].append({"query": base_name, "type": "base_name"})
            enriched["jlcpcb_lookup"]["alternatives_searched"] = True
            # Add results not already in candidates
            existing_lcsc = {c.get("lcsc") for c in all_candidates}
            for r in results:
                if r.get("lcsc") not in existing_lcsc:
                    all_candidates.append(r)
            time.sleep(REQUEST_DELAY)

    # Store all candidates
    enriched["jlcpcb_lookup"]["all_candidates"] = all_candidates

    # Select best candidate (prefer in-stock)
    best = find_best_in_stock(all_candidates)
    if not best and all_candidates:
        # No in-stock, use first result
        best = all_candidates[0]

    if best:
        enriched["jlcpcb_lookup"]["found"] = True
        enriched["jlcpcb_lookup"]["selected"] = best
        enriched["jlcpcb_price"] = best.get("price")
        enriched["jlcpcb_stock"] = best.get("stock", 0)
        enriched["jlcpcb_type"] = get_part_type(best)
        enriched["jlcpcb_available"] = best.get("stock", 0) > 0
        enriched["jlcpcb_package"] = best.get("package")
        enriched["jlcpcb_datasheet"] = best.get("datasheet")
        enriched["lcsc"] = best.get("lcsc")

        # Check for LCSC mismatch
        if known_lcsc and best.get("lcsc") != known_lcsc:
            enriched["jlcpcb_lookup"]["lcsc_mismatch"] = {
                "fsd_lcsc": known_lcsc,
                "selected_lcsc": best.get("lcsc"),
                "reason": "selected_better_stock" if best.get("stock", 0) > 0 else "original_not_found"
            }
            logger.warning(f"    -> LCSC changed: {known_lcsc} -> {best.get('lcsc')} (stock={best.get('stock')})")

        # Log selection
        stock_status = f"stock={best.get('stock')}" if best.get('stock', 0) > 0 else "OUT OF STOCK"
        logger.info(f"    -> Selected: {best.get('lcsc')} | {best.get('mfr')} | {get_part_type(best)} | {stock_status} | ${best.get('price')}")

        # Log alternatives if any are in stock
        in_stock_alternatives = [c for c in all_candidates if c.get("stock", 0) > 0 and c.get("lcsc") != best.get("lcsc")]
        if in_stock_alternatives:
            logger.info(f"    -> {len(in_stock_alternatives)} other in-stock alternatives available")
    else:
        logger.warning(f"  [{part_id}] No JLCPCB results found")
        enriched["jlcpcb_price"] = None
        enriched["jlcpcb_stock"] = 0
        enriched["jlcpcb_type"] = "Unknown"
        enriched["jlcpcb_available"] = False

    return enriched


def enrich_parts(input_path: Path, output_path: Path) -> dict:
    """
    Enrich all parts from input YAML with JLCPCB data.
    """
    logger.info(f"Loading parts from: {input_path}")
    data = load_yaml(input_path)

    parts = data.get("parts", [])
    total = len(parts)
    logger.info(f"Found {total} parts to enrich")

    enriched_parts = []
    stats = {
        "total": total,
        "found": 0,
        "not_found": 0,
        "basic": 0,
        "preferred": 0,
        "extended": 0,
        "out_of_stock": 0,
        "lcsc_mismatches": []
    }

    for idx, part in enumerate(parts, 1):
        part_id = part.get("id", f"part_{idx}")
        logger.info(f"[{idx}/{total}] Processing: {part_id}")

        enriched = enrich_part(part)
        enriched_parts.append(enriched)

        # Update stats
        if enriched.get("jlcpcb_lookup", {}).get("found"):
            stats["found"] += 1
            part_type = enriched.get("jlcpcb_type", "").lower()
            if part_type == "basic":
                stats["basic"] += 1
            elif part_type == "preferred":
                stats["preferred"] += 1
            else:
                stats["extended"] += 1

            if not enriched.get("jlcpcb_available"):
                stats["out_of_stock"] += 1
        else:
            stats["not_found"] += 1

        # Track LCSC mismatches
        mismatch = enriched.get("jlcpcb_lookup", {}).get("lcsc_mismatch")
        if mismatch:
            stats["lcsc_mismatches"].append({
                "part_id": part_id,
                **mismatch
            })

        time.sleep(REQUEST_DELAY)

    # Build output
    output = {
        "meta": {
            "source": str(input_path),
            "enriched_at": datetime.now().isoformat(),
            "stats": stats
        },
        "parts": enriched_parts,
        "option_groups": data.get("option_groups", {}),
        "notes": data.get("notes", [])
    }

    # Save output
    logger.info(f"Saving enriched parts to: {output_path}")
    save_yaml(output_path, output)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Enrichment Summary")
    print(f"{'='*60}")
    print(f"Total parts:     {stats['total']}")
    print(f"Found:           {stats['found']}")
    print(f"Not found:       {stats['not_found']}")
    print(f"Basic:           {stats['basic']}")
    print(f"Preferred:       {stats['preferred']}")
    print(f"Extended:        {stats['extended']}")
    print(f"Out of stock:    {stats['out_of_stock']}")

    if stats["lcsc_mismatches"]:
        print(f"\nLCSC Mismatches ({len(stats['lcsc_mismatches'])}):")
        for m in stats["lcsc_mismatches"]:
            print(f"  - {m['part_id']}: FSD={m['fsd_lcsc']} -> Selected={m['selected_lcsc']}")

    print(f"\nOutput: {output_path}")

    return output


def main():
    parser = argparse.ArgumentParser(description="Enrich parts with JLCPCB data")
    parser.add_argument("--input", "-i", required=True, help="Input YAML file (step1_parts_candidates.yaml)")
    parser.add_argument("--output", "-o", required=True, help="Output YAML file (step2_parts_enriched.yaml)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    enrich_parts(input_path, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
