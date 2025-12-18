#!/usr/bin/env python3
"""
Generate Enhanced Pin Model JSON from step4/step5 YAML files.

Transforms net-centric connections (step5) into part-centric pin mappings
for the SKiDL-compatible pipeline.

Output format matches the proposed deterministic schema:
- Every pin has exactly one net
- No implicit power pins
- Explicit belongs_to relationships preserved
"""

import json
import yaml
from pathlib import Path
from collections import defaultdict


def load_yaml(filepath: Path) -> dict:
    """Load YAML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def invert_nets_to_pins(nets: dict) -> dict:
    """
    Invert net-centric view to part-centric pin mappings.

    Input:  {"GND": ["mcu.GND", "ldo.GND"], "+3V3": ["mcu.3V3"]}
    Output: {"mcu": {"GND": "GND", "3V3": "+3V3"}, "ldo": {"GND": "GND"}}
    """
    part_pins = defaultdict(dict)

    for net_name, connections in nets.items():
        for conn in connections:
            if '.' not in conn:
                continue
            part_id, pin_name = conn.split('.', 1)
            part_pins[part_id][pin_name] = net_name

    return dict(part_pins)


def generate_ref(prefix: str, index: int) -> str:
    """Generate reference designator."""
    return f"{prefix}{index}"


def generate_pin_model(parts_file: Path, connections_file: Path) -> dict:
    """Generate the enhanced pin model JSON."""

    # Load source files
    parts_data = load_yaml(parts_file)
    connections_data = load_yaml(connections_file)

    parts = parts_data.get('parts', [])
    nets = connections_data.get('nets', {})
    no_connect = connections_data.get('no_connect', [])

    # Invert nets to per-part pin mappings
    part_pins = invert_nets_to_pins(nets)

    # Build NC pins lookup
    nc_pins = defaultdict(list)
    for nc in no_connect:
        comp = nc.get('component', '')
        pin = nc.get('pin', '')
        reason = nc.get('reason', '')
        if comp and pin:
            nc_pins[comp].append({'pin': pin, 'reason': reason})

    # Assign reference designators
    prefix_counters = defaultdict(int)

    # Collect all net names
    all_nets = sorted(nets.keys())

    # Build output parts list
    output_parts = []

    for part in parts:
        part_id = part.get('id')
        prefix = part.get('prefix', 'X')

        # Assign ref designator
        prefix_counters[prefix] += 1
        ref = generate_ref(prefix, prefix_counters[prefix])

        # Get pin mappings for this part
        pins = part_pins.get(part_id, {})

        # Build output part entry
        output_part = {
            "id": part_id,
            "ref": ref,
            "name": part.get('name', ''),
            "symbol": f"JLCPCB:{part.get('lcsc_hint', 'UNKNOWN')}",
            "footprint": f"JLCPCB:{part.get('package', 'UNKNOWN')}",
            "value": part.get('part', ''),
            "lcsc": part.get('lcsc', ''),
            "belongs_to": part.get('belongs_to'),
            "category": part.get('category', ''),
            "pins": pins
        }

        # Add no-connect pins if any
        if part_id in nc_pins:
            output_part["no_connect"] = nc_pins[part_id]

        output_parts.append(output_part)

    # Build complete model
    model = {
        "_meta": {
            "version": "1.0",
            "generated_from": [
                str(parts_file.name),
                str(connections_file.name)
            ],
            "date": "2025-12-17",
            "description": "Enhanced pin model for SKiDL generation"
        },
        "parts": output_parts,
        "nets": all_nets,
        "statistics": {
            "total_parts": len(output_parts),
            "total_nets": len(all_nets),
            "total_pin_assignments": sum(len(p["pins"]) for p in output_parts)
        }
    }

    return model


def main():
    script_dir = Path(__file__).parent.parent
    parts_file = script_dir / "work" / "step4_final_parts.yaml"
    connections_file = script_dir / "work" / "step5_connections.yaml"
    output_file = script_dir / "work" / "pin_model.json"

    print(f"Reading: {parts_file.name}")
    print(f"Reading: {connections_file.name}")

    model = generate_pin_model(parts_file, connections_file)

    # Write JSON output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(model, f, indent=2)

    print(f"\nGenerated: {output_file}")
    print(f"  Parts: {model['statistics']['total_parts']}")
    print(f"  Nets: {model['statistics']['total_nets']}")
    print(f"  Pin assignments: {model['statistics']['total_pin_assignments']}")


if __name__ == "__main__":
    main()
