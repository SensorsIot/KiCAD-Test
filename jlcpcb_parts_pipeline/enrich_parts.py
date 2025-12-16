#!/usr/bin/env python3
"""
Enrich a parts requirement list with JLCPCB/LCSC details and write a machine-readable file.

Input:
  - parts_requirements.yaml

Output:
  - jlc_parts_enriched.json

Data sources (in order):
  1) Official JLCPCB Components API (requires approval + API key)
  2) No-auth fallback: jlcsearch.tscircuit.com API (public mirror of in-stock JLCPCB parts)

Notes:
  - For production use, prefer the official JLCPCB Components API once approved.
  - The fallback mirror is suitable for prototyping and automation pipelines.

"""
from __future__ import annotations
import os
import json
import time
import urllib.parse
import requests
import yaml
from typing import Any, Dict, List, Optional

DEFAULT_TIMEOUT = 30

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

# -------------------------
# Source A: Official JLCPCB Components API (requires key)
# -------------------------
def jlc_components_api_search(query: str) -> Optional[dict]:
    api_key = os.getenv("JLCPCB_API_KEY")
    base = os.getenv("JLCPCB_API_BASE", "https://api.jlcpcb.com")
    if not api_key:
        return None

    # This is intentionally a stub: endpoint paths depend on your JLCAPI account docs.
    # Implement once you have access to the developer portal.
    raise NotImplementedError("Fill in official Components API endpoints from your JLCAPI docs.")

# -------------------------
# Source B: No-auth fallback mirror (jlcsearch)
# -------------------------
def jlcsearch_search(query: str, limit: int = 10) -> dict:
    """
    Query jlcsearch.tscircuit.com API.

    API returns: {"components": [...]}
    Each component has: lcsc (int), mfr (str), package (str),
                        is_basic (bool), is_preferred (bool),
                        description (str), stock (int), price (float)
    """
    url = "https://jlcsearch.tscircuit.com/api/search?" + urllib.parse.urlencode({
        "q": query,
        "limit": str(limit)
    })
    r = requests.get(url, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.json()

def pick_best_candidate(components: List[dict], prefer_basic: bool = True) -> Optional[dict]:
    """
    Pick the best component from results.
    Preference order: basic > preferred > in-stock > highest stock
    """
    if not components:
        return None

    def score(c):
        # Higher score = better choice
        s = 0
        if c.get("is_basic"):
            s += 10000
        if c.get("is_preferred"):
            s += 5000
        stock = c.get("stock", 0) or 0
        if stock > 0:
            s += 1000
        s += min(stock, 999)  # Cap stock contribution
        return s

    sorted_components = sorted(components, key=score, reverse=True)
    return sorted_components[0]

def format_lcsc(lcsc_num) -> str:
    """Format LCSC number with C prefix"""
    if lcsc_num is None:
        return None
    if isinstance(lcsc_num, str) and lcsc_num.startswith("C"):
        return lcsc_num
    return f"C{lcsc_num}"

def get_part_type(component: dict) -> str:
    """Determine part type from component flags"""
    if component.get("is_basic"):
        return "basic"
    if component.get("is_preferred"):
        return "preferred"
    return "extended"

def enrich_parts(req_path: str, out_path: str) -> dict:
    req = load_yaml(req_path)
    out = {"meta": req.get("meta", {}), "parts": []}

    total = len(req.get("parts", []))

    for idx, p in enumerate(req.get("parts", []), 1):
        designator = p.get("designator") or p.get("key")
        query = p.get("mpn")
        known_lcsc = p.get("lcsc")

        print(f"[{idx}/{total}] Searching: {designator} - {query}")

        record = {
            "designator": designator,
            "query": query,
            "function": p.get("function"),
            "package": p.get("package"),
            "value": p.get("value"),
            "known_lcsc": known_lcsc,
            # KiCAD fields
            "symbol": p.get("symbol"),
            "footprint": p.get("footprint"),
            "datasheet": p.get("datasheet"),
            "candidates": [],
            "selection": None,
            "error": None
        }

        # Try official API (if configured)
        try:
            api_res = jlc_components_api_search(query)
            if api_res:
                record["candidates"] = api_res.get("components", [])
        except NotImplementedError:
            pass
        except Exception as e:
            record["error"] = f"Official API error: {str(e)}"

        # Fall back to jlcsearch
        if not record["candidates"]:
            try:
                res = jlcsearch_search(query, limit=10)
                components = res.get("components", [])
                record["candidates"] = components

                best = pick_best_candidate(components)
                if best:
                    record["selection"] = {
                        "lcsc": format_lcsc(best.get("lcsc")),
                        "mpn": best.get("mfr"),
                        "package": best.get("package"),
                        "description": best.get("description"),
                        "stock": best.get("stock"),
                        "price": best.get("price"),
                        "part_type": get_part_type(best),
                        "is_basic": best.get("is_basic", False),
                        "is_preferred": best.get("is_preferred", False),
                    }
                    print(f"    -> Found: {record['selection']['lcsc']} ({record['selection']['part_type']}) stock={record['selection']['stock']}")
                else:
                    # If no results from search, use known LCSC from YAML
                    if known_lcsc:
                        record["selection"] = {
                            "lcsc": known_lcsc if known_lcsc.startswith("C") else f"C{known_lcsc}",
                            "mpn": query,
                            "package": p.get("package"),
                            "description": p.get("function"),
                            "stock": None,
                            "price": None,
                            "part_type": p.get("part_type", "unknown"),
                            "is_basic": p.get("part_type") == "basic",
                            "is_preferred": False,
                            "note": "Using known LCSC from requirements (no API match)"
                        }
                        print(f"    -> Using known: {known_lcsc}")
                    else:
                        print(f"    -> NO MATCH FOUND")

            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP {e.response.status_code}: {str(e)}"
                record["error"] = error_msg
                print(f"    -> Error: {error_msg}")
                # Fall back to known LCSC
                if known_lcsc:
                    record["selection"] = {
                        "lcsc": known_lcsc if known_lcsc.startswith("C") else f"C{known_lcsc}",
                        "mpn": query,
                        "package": p.get("package"),
                        "description": p.get("function"),
                        "stock": None,
                        "price": None,
                        "part_type": p.get("part_type", "unknown"),
                        "is_basic": p.get("part_type") == "basic",
                        "is_preferred": False,
                        "note": "Using known LCSC from requirements (API error)"
                    }
                    print(f"    -> Fallback to known: {known_lcsc}")
            except Exception as e:
                record["error"] = str(e)
                print(f"    -> Error: {str(e)}")

        out["parts"].append(record)
        time.sleep(0.3)  # be polite to the API

    # Summary stats
    found = sum(1 for p in out["parts"] if p.get("selection"))
    basic = sum(1 for p in out["parts"] if p.get("selection") and p["selection"].get("is_basic"))
    preferred = sum(1 for p in out["parts"] if p.get("selection") and p["selection"].get("is_preferred"))

    out["summary"] = {
        "total_parts": total,
        "found": found,
        "not_found": total - found,
        "basic_parts": basic,
        "preferred_parts": preferred,
        "extended_parts": found - basic - preferred
    }

    print(f"\nSummary: {found}/{total} found, {basic} basic, {preferred} preferred")

    return out

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="parts_requirements.yaml")
    ap.add_argument("--out", dest="out", default="jlc_parts_enriched.json")
    args = ap.parse_args()

    enriched = enrich_parts(args.inp, args.out)
    save_json(args.out, enriched)
    print(f"\nWrote {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
