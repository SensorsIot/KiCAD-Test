#!/usr/bin/env python3
"""
Map semantic connections to pin-level net labels.

Usage:
    python map_connections.py

Input:
    connections.yaml - Semantic net definitions (MCU.GPIO4)
    parts_with_designators.json - Semantic name to designator mapping
    symbol_pins.json - Pin data from JLCPCB symbols

Output:
    parts_with_netlabels.json - Full part list with net labels per pin
"""

import yaml
import json
import re
from pathlib import Path
from collections import defaultdict


# Pin name mapping: semantic name -> possible symbol pin names
PIN_NAME_ALIASES = {
    # ESP32 GPIO mapping
    "GPIO4": ["IO4", "GPIO4", "4"],
    "GPIO5": ["IO5", "GPIO5", "5"],
    "GPIO6": ["IO6", "GPIO6", "6"],
    "GPIO7": ["IO7", "GPIO7", "7"],
    "GPIO8": ["IO8", "GPIO8", "8"],
    "GPIO9": ["IO9", "GPIO9", "9"],
    "GPIO10": ["IO10", "GPIO10", "10"],
    "GPIO19": ["IO19", "GPIO19", "19"],
    "GPIO20": ["IO20", "GPIO20", "20"],
    "GPIO21": ["IO21", "GPIO21", "21"],
    "GPIO35": ["IO35", "GPIO35", "35"],
    "GPIO36": ["IO36", "GPIO36", "36"],
    "EN": ["EN", "CHIP_PU", "ENABLE"],
    "3V3": ["3V3", "VCC", "VDD", "3.3V"],
    "VBUS": ["VBUS", "5V", "VIN"],

    # SI4735 pins
    "SDIO": ["SDIO", "SDA"],
    "SCLK": ["SCLK", "SCL"],
    "RST": ["RST", "RESET", "RSTB"],
    "LOUT": ["LOUT", "AOUTL", "LO"],
    "ROUT": ["ROUT", "AOUTR", "RO"],
    "RCLK": ["RCLK", "REFCLK", "CLK", "RCLKI"],
    "VDD": ["VDD", "VCC", "DVDD"],
    "VA": ["VA", "AVDD", "CVDD"],
    "VD": ["VD", "DVDD"],
    "FMI": ["FMI", "FM_IN"],
    "AMI": ["AMI", "AM_IN"],

    # TP4056 pins
    "VIN": ["VIN", "VCC", "IN"],
    "BAT": ["BAT", "VBAT", "OUT"],
    "PROG": ["PROG"],

    # AMS1117 pins
    "VOUT": ["VOUT", "OUT", "VO"],

    # USB-C pins
    "VBUS": ["VBUS", "VCC", "5V"],
    "DP": ["DP", "D+", "USB_D+", "DP1", "DP2"],
    "DM": ["DM", "D-", "USB_D-", "DN1", "DN2"],
    "CC1": ["CC1"],
    "CC2": ["CC2"],

    # WS2812B pins
    "DIN": ["DIN", "DI", "DATA"],
    "DOUT": ["DOUT", "DO"],
    "VSS": ["VSS", "GND"],
    "VDD": ["VDD", "VCC"],

    # Audio jack
    "TIP": ["TIP", "T", "1"],
    "RING": ["RING", "R", "2"],
    "SLEEVE": ["SLEEVE", "S", "3", "GND"],

    # Encoder pins
    "A": ["A", "1"],
    "B": ["B", "2"],
    "C": ["C", "3", "COM"],
    "SW": ["SW", "S", "SWITCH", "D", "E", "6", "7"],

    # Generic
    "GND": ["GND", "VSS", "0V", "GND1", "GND2"],
    "1": ["1"],
    "2": ["2"],
    "3": ["3"],
    "4": ["4"],
}

MANUAL_SYMBOL_PINS_FILE = Path(__file__).parent / "manual_symbol_pins.yaml"
CUSTOM_OVERRIDES = Path(__file__).parent / "custom_library_overrides.yaml"


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_manual_symbol_pins(path: Path) -> dict:
    """Load manual symbol pin mappings from YAML if present."""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return data


def load_overrides(path: Path) -> dict:
    """Load custom overrides for symbols/footprints."""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def find_pin_number(symbol_pins: dict, symbol_name: str, semantic_pin: str) -> str:
    """
    Find actual pin number for a semantic pin name.

    Args:
        symbol_pins: Dict of symbol -> pins data
        symbol_name: Name of the symbol to search
        semantic_pin: Semantic pin name (GPIO4, DIN, etc.)

    Returns:
        Pin number as string, or None if not found
    """
    # Get possible aliases for this semantic name
    aliases = PIN_NAME_ALIASES.get(semantic_pin, [semantic_pin])

    # If semantic_pin is already a number, return it
    if semantic_pin.isdigit():
        return semantic_pin

    # Search symbol pins
    pins = symbol_pins.get(symbol_name, {}).get("pins", [])

    for pin in pins:
        pin_name = pin.get("name", "")
        pin_number = pin.get("number", "")

        # Check if pin name matches any alias
        for alias in aliases:
            if pin_name.upper() == alias.upper():
                return pin_number

        # Also check if semantic pin matches pin number directly
        if pin_number == semantic_pin:
            return pin_number

    return None


def parse_connection_ref(ref: str) -> tuple:
    """
    Parse a connection reference like 'MCU.GPIO4' or 'R_CC.2'.

    Returns:
        (component_name, pin_name)
    """
    parts = ref.split(".")
    if len(parts) == 2:
        return parts[0], parts[1]
    return ref, None


def get_symbol_name_for_lcsc(lcsc: str, lcsc_to_symbol: dict) -> str:
    """Get symbol name for LCSC code."""
    return lcsc_to_symbol.get(lcsc, None)


def build_pin_assignments(
    connections: dict,
    designators: dict,
    symbol_pins: dict,
    lcsc_to_symbol: dict
) -> dict:
    """
    Build net label assignments for all pins.

    Returns:
        Dict keyed by designator, containing pin -> net_label mapping
    """
    # Initialize result with all pins having unique labels
    result = {}

    # Manual symbol pins are loaded from manual_symbol_pins.yaml in the calling code
    # No hardcoded product-specific data here

    # First, create entries for all parts with default unique labels
    for semantic_name, data in designators.items():
        for des in data["designators"]:
            lcsc = data["lcsc"]
            symbol_name = get_symbol_name_for_lcsc(lcsc, lcsc_to_symbol)
            symbol_pin_data = symbol_pins.get(symbol_name, {})
            pins = symbol_pin_data.get("pins", []) if isinstance(symbol_pin_data, dict) else []

            if not pins:
                if symbol_name in symbol_pins and symbol_pins[symbol_name]:
                    # Symbol present but pins empty
                    print(
                        f"WARNING: Symbol '{symbol_name}' has no pins for {des} (LCSC={lcsc}). "
                        "Add pins to manual_symbol_pins.yaml."
                    )
                else:
                    print(
                        f"WARNING: No pin data for {des} (LCSC={lcsc}, symbol={symbol_name}). "
                        "Add this symbol's pin map to manual_symbol_pins.yaml."
                    )
                pins = [{"number": "1", "name": "1"}, {"number": "2", "name": "2"}]  # Fallback

            result[des] = {
                "semantic_name": semantic_name,
                "lcsc": lcsc,
                "symbol": symbol_name,
                "pins": {}
            }

            # Default: unique label per pin
            for pin in pins:
                pin_num = pin["number"]
                result[des]["pins"][pin_num] = {
                    "name": pin.get("name", pin_num),
                    "net_label": f"{des}_{pin_num}"  # Default unique label
                }

    # Now apply net connections
    nets = connections.get("nets", {})

    for net_name, refs in nets.items():
        for ref in refs:
            comp_name, pin_name = parse_connection_ref(ref)

            if comp_name not in designators:
                print(f"WARNING: Unknown component '{comp_name}' in net '{net_name}'")
                continue

            des_data = designators[comp_name]

            # Apply to all instances of this component
            for des in des_data["designators"]:
                if des not in result:
                    continue

                lcsc = des_data["lcsc"]
                symbol_name = get_symbol_name_for_lcsc(lcsc, lcsc_to_symbol)

                # Find the actual pin number
                if pin_name:
                    pin_num = find_pin_number(symbol_pins, symbol_name, pin_name)

                    if pin_num is None:
                        # Try direct pin number
                        if pin_name.isdigit():
                            pin_num = pin_name
                        else:
                            print(f"WARNING: Pin '{pin_name}' not found for {des} ({symbol_name})")
                            continue

                    # Assign net label
                    if pin_num in result[des]["pins"]:
                        result[des]["pins"][pin_num]["net_label"] = net_name
                    else:
                        print(f"WARNING: Pin {pin_num} not in {des}")

    return result


def main():
    script_dir = Path(__file__).parent
    connections_yaml = script_dir / "LLM-connections.yaml"
    designators_json = script_dir / "parts_with_designators.json"
    symbol_pins_json = script_dir / "symbol_pins.json"
    output_json = script_dir / "parts_with_netlabels.json"

    # Also check parent Version2 folder for symbol_pins.json
    if not symbol_pins_json.exists():
        alt_path = script_dir.parent / "Version2" / "symbol_pins.json"
        if alt_path.exists():
            symbol_pins_json = alt_path

    # Check inputs
    for path in [connections_yaml, designators_json]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing input {path}. "
                "Ensure parts.yaml/connections.yaml are generated and assign_designators.py has been run."
            )

    if not symbol_pins_json.exists():
        raise FileNotFoundError(
            f"Missing symbol pins file: {symbol_pins_json}. "
            "Run parse_library_pins.py after downloading libraries."
        )

    # Load data
    print(f"Loading connections from: {connections_yaml.name}")
    connections = load_yaml(connections_yaml)
    net_count = len(connections.get("nets", {}))
    print(f"  Found {net_count} nets")

    print(f"Loading designators from: {designators_json.name}")
    designators = load_json(designators_json)
    print(f"  Found {len(designators)} component types")

    print(f"Loading symbol pins from: {symbol_pins_json.name}")
    symbol_pins = load_json(symbol_pins_json)
    manual_pins = load_manual_symbol_pins(MANUAL_SYMBOL_PINS_FILE)
    if manual_pins:
        symbol_pins.update(manual_pins)
        print(f"  Loaded manual symbol pins: {len(manual_pins)} symbols from {MANUAL_SYMBOL_PINS_FILE.name}")
    else:
        print(f"  No manual symbol pins loaded (optional): {MANUAL_SYMBOL_PINS_FILE.name} not found or empty")
    print(f"  Found {len(symbol_pins)} symbols")

    overrides = load_overrides(CUSTOM_OVERRIDES)

    # Build LCSC to symbol mapping
    # This would normally come from the download script's index
    # For now, use the designators data
    lcsc_to_symbol = {}
    for name, data in designators.items():
        lcsc = data["lcsc"]
        if not lcsc or lcsc in {"NOT_SELECTED", "NOT_FOUND"}:
            # Allow override mapping for non-LCSC parts (DNP/custom)
            override_sym = overrides.get(lcsc, {}).get("symbol_lib_id") if overrides else None
            if override_sym == "DNP":
                # Skip DNP (Do Not Place) parts - external components like antennas
                print(f"  Skipping DNP component: {name}")
                continue
            elif override_sym:
                lcsc_to_symbol[lcsc] = override_sym
            else:
                raise ValueError(
                    f"Component '{name}' has no valid LCSC code ({lcsc}). "
                    "Ensure parts_options.csv has a selection or add override to custom_library_overrides.yaml."
                )
        else:
            # Will be mapped from symbol_pins.json LCSC codes below
            pass

    # Build LCSC-to-symbol mapping from symbol_pins.json (contains LCSC codes extracted from library)
    for symbol_name, sym_data in symbol_pins.items():
        sym_lcsc = sym_data.get("lcsc")
        if sym_lcsc:
            lcsc_to_symbol[sym_lcsc] = symbol_name

    # Apply overrides from custom_library_overrides.yaml
    if overrides:
        for lcsc, data in overrides.items():
            sym_id = data.get("symbol_lib_id")
            if sym_id and sym_id != "DNP":
                lcsc_to_symbol[lcsc] = sym_id

    # Build pin assignments
    print("\nMapping connections to pins...")
    result = build_pin_assignments(connections, designators, symbol_pins, lcsc_to_symbol)

    # Count statistics
    total_pins = sum(len(d["pins"]) for d in result.values())

    unique_labels = set()
    net_labels = set()
    for des, data in result.items():
        for pin_num, pin_data in data["pins"].items():
            label = pin_data["net_label"]
            unique_labels.add(label)
            if not label.startswith(des + "_"):
                net_labels.add(label)

    print(f"  Total parts: {len(result)}")
    print(f"  Total pins: {total_pins}")
    print(f"  Unique net names: {len(net_labels)}")
    print(f"  Unconnected pins (unique labels): {len(unique_labels) - len(net_labels)}")

    # Save output
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\nOutput: {output_json}")
    print("\nNext step: Run generate_schematic.py to create KiCAD schematic")


if __name__ == "__main__":
    main()
