#!/usr/bin/env python3
"""
JLCPCB MCP Server

Exposes JLCPCB part search and lookup as MCP tools for Claude Code.

Tools:
- search_parts: Search JLCPCB by keyword or description
- get_part_by_lcsc: Get part by LCSC code (e.g., C2913206)
- get_part_by_name: Get part by manufacturer part number (e.g., SI4735-D60-GU)
- check_symbol_available: Check if KiCAD symbol can be downloaded for LCSC code
- download_symbol: Download KiCAD symbol for LCSC code

Usage:
    # Add to Claude Code
    claude mcp add --transport stdio jlcpcb -- python /path/to/jlcpcb_mcp.py

    # Then in Claude Code:
    > Search JLCPCB for ESP32-S3 modules
    > Get details for LCSC part C2913206
    > Find part SI4735-D60-GU
    > Check if symbol available for C2913206
    > Download symbol for C2913206
"""

import json
import sys
import re
import subprocess
import tempfile
import shutil
import requests
from pathlib import Path
from typing import Any

# JLCPCB API endpoint
JLCPCB_API_URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
DEFAULT_TIMEOUT = 30


def search_jlcpcb(query: str, limit: int = 10) -> list[dict]:
    """
    Search JLCPCB for parts matching query.

    Args:
        query: Search term (part number, LCSC code, or keyword)
        limit: Maximum results to return (default 10)

    Returns:
        List of parts with lcsc, mfr, package, stock, price, type, description
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
        response = requests.post(
            JLCPCB_API_URL,
            json=payload,
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {"error": f"API error: {data.get('message')}"}

        page_info = data.get("data", {}).get("componentPageInfo", {})
        raw_components = page_info.get("list") or []

        components = []
        for comp in raw_components:
            # Skip discontinued parts
            if comp.get("componentTypeEn") == "Abolished Device":
                continue

            # Get all price tiers
            prices = comp.get("componentPrices") or []
            price_tiers = []
            price_10 = None
            for p in prices:
                tier = {
                    "qty": p.get("startNumber", 0),
                    "price": p.get("productPrice")
                }
                price_tiers.append(tier)
                if p.get("startNumber", 0) >= 10 and price_10 is None:
                    price_10 = p.get("productPrice")

            if price_10 is None and prices:
                price_10 = prices[-1].get("productPrice", "")

            lcsc_code = comp.get("componentCode", "")
            if lcsc_code and not lcsc_code.startswith("C"):
                lcsc_code = f"C{lcsc_code}"

            # Determine part type
            if comp.get("componentLibraryType") == "base":
                part_type = "Basic"
            elif comp.get("preferredComponentFlag"):
                part_type = "Preferred"
            else:
                part_type = "Extended"

            components.append({
                "lcsc": lcsc_code,
                "mfr_part": comp.get("componentModelEn", ""),
                "manufacturer": comp.get("brandNameEn", ""),
                "package": comp.get("componentSpecificationEn", ""),
                "stock": comp.get("stockCount", 0),
                "price_usd": price_10,
                "price_tiers": price_tiers,
                "type": part_type,
                "description": comp.get("describe", ""),
                "datasheet": comp.get("dataManualUrl", ""),
                "in_stock": comp.get("stockCount", 0) > 0
            })

        return components

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def is_lcsc_code(query: str) -> bool:
    """Check if query looks like an LCSC code (C followed by digits)."""
    return bool(re.match(r'^C?\d{4,}$', query.strip()))


def get_part_by_lcsc(lcsc_code: str) -> dict:
    """
    Get detailed information for a specific LCSC part.

    Args:
        lcsc_code: LCSC part code (e.g., "C2913206")

    Returns:
        Part details or error
    """
    lcsc_code = lcsc_code.strip()
    if not lcsc_code.startswith("C"):
        lcsc_code = f"C{lcsc_code}"

    results = search_jlcpcb(lcsc_code, limit=5)

    if isinstance(results, dict) and "error" in results:
        return results

    # Find exact match by LCSC code
    for part in results:
        if part.get("lcsc") == lcsc_code:
            return part

    if results:
        return {"warning": f"Exact LCSC match not found for {lcsc_code}", "part": results[0]}

    return {"error": f"Part {lcsc_code} not found"}


def get_part_by_name(part_name: str) -> dict:
    """
    Get detailed information for a part by manufacturer part number.

    Args:
        part_name: Manufacturer part number (e.g., "SI4735-D60-GU", "ESP32-S3-MINI-1-N8")

    Returns:
        Part details or error
    """
    part_name = part_name.strip()
    results = search_jlcpcb(part_name, limit=10)

    if isinstance(results, dict) and "error" in results:
        return results

    if not results:
        return {"error": f"Part '{part_name}' not found"}

    # Try to find exact match by mfr_part
    part_name_upper = part_name.upper()
    for part in results:
        mfr = part.get("mfr_part", "").upper()
        if mfr == part_name_upper or part_name_upper in mfr:
            return part

    # Return first result as best match
    return {"warning": f"Exact match not found for '{part_name}', showing best match", "part": results[0]}


def get_type_sort_key(part_type: str) -> int:
    """Sort key for part types: Basic=0, Preferred=1, Extended=2."""
    return {"Basic": 0, "Preferred": 1, "Extended": 2}.get(part_type, 3)


def propose_best_part(variants: list[dict]) -> dict | None:
    """
    Propose the best part based on criteria:
    1. In-stock preferred over out-of-stock
    2. Type priority: Basic > Preferred > Extended
    3. Highest stock (among same type)
    4. Lowest price (among same type and stock tier)
    """
    if not variants:
        return None

    def sort_key(v):
        in_stock_key = 0 if v.get("in_stock", False) else 1
        type_key = get_type_sort_key(v.get("type", "Extended"))
        stock_key = -v.get("stock", 0)
        price_key = v.get("price_usd") or 999999
        return (in_stock_key, type_key, stock_key, price_key)

    sorted_variants = sorted(variants, key=sort_key)
    return sorted_variants[0] if sorted_variants else None


def search_family_variants(family: str, module: str = "", quantity: int = 1) -> dict:
    """
    Search for ALL variants of a part family with proposed_by_claude selection.
    Returns structured data suitable for CSV generation.

    Args:
        family: Part family name (e.g., "ME6211", "ESP32-S3-MINI")
        module: Module name for circuit-analysis (e.g., "LDO", "MCU")
        quantity: Quantity needed

    Returns:
        Dict with family info and variants list
    """
    try:
        # Search for up to 30 variants
        results = search_jlcpcb(family, limit=30)

        if isinstance(results, dict) and "error" in results:
            return results

        if not results:
            return {
                "family": family,
                "module": module,
                "quantity": quantity,
                "status": "not_found",
                "variants": []
            }

        # Sort by type (Basic first), then by stock (highest first)
        results.sort(key=lambda x: (get_type_sort_key(x.get("type", "Extended")), -x.get("stock", 0)))

        # Propose the best part
        proposed = propose_best_part(results)
        proposed_lcsc = proposed.get("lcsc") if proposed else None

        # Mark proposed and add module/quantity
        variants = []
        for v in results:
            is_proposed = v.get("lcsc") == proposed_lcsc
            variants.append({
                "family": family,
                "module": module,
                "quantity": quantity if is_proposed else None,
                "mfr_part": v.get("mfr_part", ""),
                "proposed_by_claude": is_proposed,
                "lcsc": v.get("lcsc", ""),
                "type": v.get("type", "Extended"),
                "package": v.get("package", ""),
                "stock": v.get("stock", 0),
                "in_stock": v.get("in_stock", False),
                "price": v.get("price_usd"),
                "description": v.get("description", "")
            })

        # Count by type
        basic_count = sum(1 for v in variants if v["type"] == "Basic")
        preferred_count = sum(1 for v in variants if v["type"] == "Preferred")
        extended_count = sum(1 for v in variants if v["type"] == "Extended")
        in_stock_count = sum(1 for v in variants if v["in_stock"])

        return {
            "family": family,
            "module": module,
            "quantity": quantity,
            "status": "found",
            "total_variants": len(variants),
            "basic_count": basic_count,
            "preferred_count": preferred_count,
            "extended_count": extended_count,
            "in_stock_count": in_stock_count,
            "proposed": proposed_lcsc,
            "variants": variants
        }

    except Exception as e:
        return {"error": str(e)}


# EasyEDA API for symbol availability
EASYEDA_API_URL = "https://easyeda.com/api/products/{}/svgs"


def check_symbol_available(lcsc_code: str) -> dict:
    """
    Check if a KiCAD symbol can be downloaded for an LCSC code.

    Args:
        lcsc_code: LCSC part code (e.g., "C2913206")

    Returns:
        Dict with 'available' bool and additional info
    """
    lcsc_code = lcsc_code.strip()
    if not lcsc_code.startswith("C"):
        lcsc_code = f"C{lcsc_code}"

    # First check if part exists on JLCPCB
    part_info = get_part_by_lcsc(lcsc_code)
    if "error" in part_info:
        return {
            "available": False,
            "lcsc": lcsc_code,
            "reason": part_info["error"]
        }

    # Check EasyEDA API for component UUID
    try:
        url = EASYEDA_API_URL.format(lcsc_code)
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("result"):
                return {
                    "available": True,
                    "lcsc": lcsc_code,
                    "mfr_part": part_info.get("mfr_part", ""),
                    "package": part_info.get("package", "")
                }

        return {
            "available": False,
            "lcsc": lcsc_code,
            "reason": "Symbol not found on EasyEDA"
        }

    except Exception as e:
        return {
            "available": False,
            "lcsc": lcsc_code,
            "reason": f"API error: {str(e)}"
        }


def download_symbol(lcsc_code: str) -> dict:
    """
    Download KiCAD symbol for an LCSC code using JLC2KiCadLib.

    Args:
        lcsc_code: LCSC part code (e.g., "C2913206")

    Returns:
        Dict with 'symbol' (S-expression string) or 'error'
    """
    lcsc_code = lcsc_code.strip()
    if not lcsc_code.startswith("C"):
        lcsc_code = f"C{lcsc_code}"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            result = subprocess.run(
                ['JLC2KiCadLib', lcsc_code, '-dir', str(temp_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                if "failed to get component uuid" in error_msg.lower():
                    return {"error": f"Symbol not available for {lcsc_code} (not on EasyEDA)"}
                return {"error": f"JLC2KiCadLib failed: {error_msg}"}

            # Find the generated .kicad_sym file
            symbol_dir = temp_path / 'symbol'
            if not symbol_dir.exists():
                return {"error": "No symbol directory created"}

            sym_files = list(symbol_dir.glob('*.kicad_sym'))
            if not sym_files:
                return {"error": "No symbol file generated"}

            # Read and extract the symbol
            sym_content = sym_files[0].read_text(encoding='utf-8')
            symbol_text = extract_symbol_from_content(sym_content, lcsc_code)

            if symbol_text:
                return {
                    "lcsc": lcsc_code,
                    "symbol": symbol_text,
                    "symbol_name": get_symbol_name(sym_content)
                }
            else:
                return {"error": "Could not extract symbol from file"}

        except subprocess.TimeoutExpired:
            return {"error": f"Timeout downloading symbol for {lcsc_code}"}
        except FileNotFoundError:
            return {"error": "JLC2KiCadLib not installed. Run: pip install JLC2KiCadLib"}
        except Exception as e:
            return {"error": f"Error: {str(e)}"}


def extract_symbol_from_content(content: str, lcsc_code: str) -> str | None:
    """
    Extract the symbol definition from .kicad_sym content.
    Returns the symbol S-expression string or None.
    """
    lines = content.split('\n')
    in_symbol = False
    symbol_lines = []
    paren_depth = 0

    for line in lines:
        # Find main symbol (not sub-symbols like _0_1 or _1_1)
        if '(symbol "' in line and '_0_1' not in line and '_1_1' not in line and not in_symbol:
            if line.strip().startswith('(symbol "'):
                in_symbol = True
                paren_depth = 0

        if in_symbol:
            symbol_lines.append(line)
            paren_depth += line.count('(') - line.count(')')

            if paren_depth <= 0 and len(symbol_lines) > 1:
                break

    if symbol_lines:
        symbol_text = '\n'.join(symbol_lines)
        # Ensure LCSC property exists
        if '"LCSC"' not in symbol_text:
            symbol_text = re.sub(
                r'(\(property "Value"[^)]+\)\s*\))',
                f'\\1\n    (property "LCSC" "{lcsc_code}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
                symbol_text
            )
        return symbol_text

    return None


def get_symbol_name(content: str) -> str:
    """Extract symbol name from .kicad_sym content."""
    match = re.search(r'\(symbol "([^"]+)"', content)
    return match.group(1) if match else "UNKNOWN"


# MCP Protocol Implementation (JSON-RPC over stdio)

def send_response(id: Any, result: Any = None, error: Any = None):
    """Send JSON-RPC response."""
    response = {"jsonrpc": "2.0", "id": id}
    if error:
        response["error"] = error
    else:
        response["result"] = result
    print(json.dumps(response), flush=True)


def send_notification(method: str, params: Any = None):
    """Send JSON-RPC notification."""
    msg = {"jsonrpc": "2.0", "method": method}
    if params:
        msg["params"] = params
    print(json.dumps(msg), flush=True)


def handle_initialize(id: Any, params: dict):
    """Handle initialize request."""
    send_response(id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "jlcpcb-mcp",
            "version": "1.1.0"
        }
    })


def handle_list_tools(id: Any):
    """Handle tools/list request."""
    send_response(id, {
        "tools": [
            {
                "name": "search_parts",
                "description": "Search JLCPCB/LCSC for electronic components by keyword or description. Returns multiple results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term: keyword (e.g., '100nF 0603'), category (e.g., 'LDO 3.3V')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default 10, max 50)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_part_by_lcsc",
                "description": "Get detailed information for a specific LCSC code. Use this when you have the LCSC code (e.g., C2913206).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lcsc_code": {
                            "type": "string",
                            "description": "LCSC part code (e.g., 'C2913206', '2913206')"
                        }
                    },
                    "required": ["lcsc_code"]
                }
            },
            {
                "name": "get_part_by_name",
                "description": "Get detailed information for a part by manufacturer part number. Use this when you have the part name (e.g., SI4735-D60-GU, ESP32-S3-MINI-1-N8).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "part_name": {
                            "type": "string",
                            "description": "Manufacturer part number (e.g., 'SI4735-D60-GU', 'ESP32-S3-MINI-1-N8', 'TDA1308')"
                        }
                    },
                    "required": ["part_name"]
                }
            },
            {
                "name": "check_symbol_available",
                "description": "Check if a KiCAD symbol can be downloaded for an LCSC code. Use before download_symbol to avoid errors.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lcsc_code": {
                            "type": "string",
                            "description": "LCSC part code (e.g., 'C2913206')"
                        }
                    },
                    "required": ["lcsc_code"]
                }
            },
            {
                "name": "download_symbol",
                "description": "Download KiCAD symbol for an LCSC code. Returns the symbol S-expression that can be appended to a .kicad_sym library file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lcsc_code": {
                            "type": "string",
                            "description": "LCSC part code (e.g., 'C2913206')"
                        }
                    },
                    "required": ["lcsc_code"]
                }
            },
            {
                "name": "search_family",
                "description": "Search for ALL variants of a part family. Returns structured JSON with proposed_by_claude selection. Use for fsd-review skill to build parts.csv.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "family": {
                            "type": "string",
                            "description": "Part family name (e.g., 'ME6211', 'ESP32-S3-MINI', 'SI2301')"
                        },
                        "module": {
                            "type": "string",
                            "description": "Module name for circuit-analysis (e.g., 'LDO', 'MCU', 'PFET')"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Quantity needed (e.g., 1, 3 for LEDs)",
                            "default": 1
                        }
                    },
                    "required": ["family"]
                }
            }
        ]
    })


def handle_call_tool(id: Any, params: dict):
    """Handle tools/call request."""
    tool_name = params.get("name")
    args = params.get("arguments", {})

    if tool_name == "search_parts":
        query = args.get("query", "")
        limit = min(args.get("limit", 10), 50)
        result = search_jlcpcb(query, limit)

        if isinstance(result, dict) and "error" in result:
            text = f"Error: {result['error']}"
        elif not result:
            text = f"No parts found for '{query}'"
        else:
            lines = [f"Found {len(result)} parts for '{query}':\n"]
            for p in result:
                stock_str = f"{p['stock']:,}" if p['in_stock'] else "OUT OF STOCK"
                lines.append(
                    f"- **{p['lcsc']}** | {p['mfr_part']}\n"
                    f"  Package: {p['package']} | Type: {p['type']} | Stock: {stock_str} | ${p['price_usd']}\n"
                    f"  {p['description'][:100]}..."
                )
            text = "\n".join(lines)

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    elif tool_name == "get_part_by_lcsc":
        lcsc_code = args.get("lcsc_code", "")
        result = get_part_by_lcsc(lcsc_code)

        if "error" in result:
            text = f"Error: {result['error']}"
        elif "warning" in result:
            p = result["part"]
            text = f"Warning: {result['warning']}\n\n" + format_part_details(p)
        else:
            text = format_part_details(result)

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    elif tool_name == "get_part_by_name":
        part_name = args.get("part_name", "")
        result = get_part_by_name(part_name)

        if "error" in result:
            text = f"Error: {result['error']}"
        elif "warning" in result:
            p = result["part"]
            text = f"Warning: {result['warning']}\n\n" + format_part_details(p)
        else:
            text = format_part_details(result)

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    # Keep backward compatibility with old tool name
    elif tool_name == "get_part_details":
        lcsc_code = args.get("lcsc_code", "")
        result = get_part_by_lcsc(lcsc_code)

        if "error" in result:
            text = f"Error: {result['error']}"
        elif "warning" in result:
            p = result["part"]
            text = f"Warning: {result['warning']}\n\n" + format_part_details(p)
        else:
            text = format_part_details(result)

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    elif tool_name == "check_symbol_available":
        lcsc_code = args.get("lcsc_code", "")
        result = check_symbol_available(lcsc_code)

        if result.get("available"):
            text = (
                f"## Symbol Available: {result['lcsc']}\n\n"
                f"**Part:** {result.get('mfr_part', 'N/A')}\n"
                f"**Package:** {result.get('package', 'N/A')}\n\n"
                f"Ready to download with `download_symbol`."
            )
        else:
            text = (
                f"## Symbol NOT Available: {result['lcsc']}\n\n"
                f"**Reason:** {result.get('reason', 'Unknown')}"
            )

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    elif tool_name == "download_symbol":
        lcsc_code = args.get("lcsc_code", "")
        result = download_symbol(lcsc_code)

        if "error" in result:
            text = f"Error: {result['error']}"
        else:
            text = (
                f"## Symbol Downloaded: {result['lcsc']}\n\n"
                f"**Symbol Name:** {result.get('symbol_name', 'N/A')}\n\n"
                f"**Symbol S-expression:**\n```\n{result['symbol']}\n```\n\n"
                f"Append this to your project's `JLCPCB.kicad_sym` library file."
            )

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    elif tool_name == "search_family":
        family = args.get("family", "")
        module = args.get("module", "")
        quantity = args.get("quantity", 1)

        result = search_family_variants(family, module, quantity)

        if "error" in result:
            text = f"Error: {result['error']}"
        else:
            # Return structured JSON for CSV generation
            text = json.dumps(result, indent=2)

        send_response(id, {
            "content": [{"type": "text", "text": text}]
        })

    else:
        send_response(id, error={
            "code": -32601,
            "message": f"Unknown tool: {tool_name}"
        })


def format_part_details(p: dict) -> str:
    """Format part details for display."""
    stock_str = f"{p['stock']:,}" if p['in_stock'] else "OUT OF STOCK"

    # Format price tiers
    tiers_str = ""
    if p.get('price_tiers'):
        tiers = [f"  - {t['qty']}+: ${t['price']}" for t in p['price_tiers'][:5]]
        tiers_str = "\n**Price Tiers:**\n" + "\n".join(tiers)

    return (
        f"## {p['lcsc']} - {p['mfr_part']}\n\n"
        f"**Manufacturer:** {p.get('manufacturer', 'N/A')}\n"
        f"**Package:** {p['package']}\n"
        f"**Type:** {p['type']}\n"
        f"**Stock:** {stock_str}\n"
        f"**Price:** ${p['price_usd']} (qty 10+)\n"
        f"{tiers_str}\n"
        f"**Description:** {p['description']}\n"
        f"**Datasheet:** {p['datasheet'] or 'N/A'}"
    )


def main():
    """Main MCP server loop."""
    # Read JSON-RPC messages from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            handle_initialize(id, params)
        elif method == "initialized":
            pass  # Notification, no response needed
        elif method == "tools/list":
            handle_list_tools(id)
        elif method == "tools/call":
            handle_call_tool(id, params)
        elif method == "shutdown":
            send_response(id, None)
            break
        else:
            if id is not None:
                send_response(id, error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                })


if __name__ == "__main__":
    main()
