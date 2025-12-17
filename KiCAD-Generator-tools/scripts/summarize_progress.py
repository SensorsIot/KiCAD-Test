#!/usr/bin/env python3
"""
Summarize design progress across all pipeline steps.

Generates a human-readable report showing:
- Which steps have been completed
- Part counts and changes between steps
- Connection statistics
- Outstanding issues
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime


def load_yaml(filepath: Path) -> dict | None:
    """Load YAML file, return None if missing or invalid."""
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        return None


def summarize():
    """Generate progress summary."""
    script_dir = Path(__file__).parent.parent
    work_dir = script_dir / "work"

    print("=" * 70)
    print("DESIGN PIPELINE PROGRESS REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Track overall status
    steps_complete = 0
    total_steps = 6

    # === Step 1: Primary Parts ===
    print("\n[Step 1] Primary Parts Extraction")
    print("-" * 40)
    step1 = load_yaml(work_dir / "step1_primary_parts.yaml")
    if step1:
        parts = step1.get('primary_parts', [])
        print(f"  Status: COMPLETE")
        print(f"  Primary parts identified: {len(parts)}")
        if parts:
            categories = {}
            for p in parts:
                cat = p.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            print(f"  By category: {dict(sorted(categories.items()))}")
        steps_complete += 1
    else:
        print("  Status: NOT STARTED")

    # === Step 2: Extended Parts ===
    print("\n[Step 2] Supporting Parts Research")
    print("-" * 40)
    step2 = load_yaml(work_dir / "step2_parts_extended.yaml")
    if step2:
        parts = step2.get('parts', [])
        primary = sum(1 for p in parts if p.get('belongs_to') is None)
        supporting = len(parts) - primary
        print(f"  Status: COMPLETE")
        print(f"  Total parts: {len(parts)}")
        print(f"    - Primary: {primary}")
        print(f"    - Supporting: {supporting}")
        if step1:
            step1_count = len(step1.get('primary_parts', []))
            print(f"  Delta from Step 1: +{len(parts) - step1_count} parts")
        steps_complete += 1
    else:
        print("  Status: NOT STARTED")

    # === Step 3: Decisions ===
    print("\n[Step 3] Design Decisions")
    print("-" * 40)
    step3 = load_yaml(work_dir / "step3_decisions.yaml")
    if step3:
        decisions = step3.get('decisions', [])
        made = sum(1 for d in decisions if d.get('selected'))
        pending = len(decisions) - made
        print(f"  Status: {'COMPLETE' if pending == 0 else 'IN PROGRESS'}")
        print(f"  Total decisions: {len(decisions)}")
        print(f"    - Made: {made}")
        print(f"    - Pending: {pending}")
        if pending > 0:
            print("  Pending decisions:")
            for d in decisions:
                if not d.get('selected'):
                    print(f"    - {d.get('topic', 'unknown')}")
        steps_complete += 1
    else:
        print("  Status: NOT STARTED")

    # === Step 4: Final Parts ===
    print("\n[Step 4] Final Parts List")
    print("-" * 40)
    step4 = load_yaml(work_dir / "step4_final_parts.yaml")
    if step4:
        parts = step4.get('parts', [])
        total_qty = sum(p.get('quantity', 1) for p in parts)
        print(f"  Status: COMPLETE")
        print(f"  Unique parts: {len(parts)}")
        print(f"  Total components: {total_qty}")

        # Count by prefix
        by_prefix = {}
        for p in parts:
            pfx = p.get('prefix', '?')
            by_prefix[pfx] = by_prefix.get(pfx, 0) + p.get('quantity', 1)
        print(f"  By type:")
        for pfx in sorted(by_prefix.keys()):
            print(f"    {pfx}: {by_prefix[pfx]}")

        # Check for TBD values
        tbd_count = 0
        for p in parts:
            if 'TBD' in str(p.get('part', '')).upper():
                tbd_count += 1
            if 'TBD' in str(p.get('package', '')).upper():
                tbd_count += 1
        if tbd_count > 0:
            print(f"  WARNING: {tbd_count} unresolved TBD values")

        steps_complete += 1
    else:
        print("  Status: NOT STARTED")

    # === Step 5: Connections ===
    print("\n[Step 5] Connections/Netlist")
    print("-" * 40)
    step5 = load_yaml(work_dir / "step5_connections.yaml")
    if step5:
        nets = step5.get('nets', {})
        total_conns = sum(len(c) for c in nets.values() if isinstance(c, list))
        nc_count = len(step5.get('no_connect', []))
        tp_count = len(step5.get('test_points', []))
        print(f"  Status: COMPLETE")
        print(f"  Total nets: {len(nets)}")
        print(f"  Total connections: {total_conns}")
        print(f"  No-connect pins: {nc_count}")
        print(f"  Test points: {tp_count}")

        # Power nets
        power_nets = [n for n in nets.keys() if any(p in n.upper() for p in ['GND', 'VCC', 'VDD', 'BAT', '+3V', '+5V', '+12V'])]
        if power_nets:
            print(f"  Power nets: {', '.join(power_nets)}")

        steps_complete += 1
    else:
        print("  Status: NOT STARTED")

    # === Step 6: Validation ===
    print("\n[Step 6] Design Validation")
    print("-" * 40)
    step6 = load_yaml(work_dir / "step6_validation.yaml")
    if step6:
        summary = step6.get('summary', {})
        status = summary.get('status', 'UNKNOWN')
        issues = summary.get('issues_found', 0)
        critical = summary.get('critical_issues', 0)
        print(f"  Status: {status}")
        print(f"  Issues found: {issues}")
        print(f"  Critical issues: {critical}")

        if step6.get('issues'):
            print("  Issue summary:")
            for issue in step6.get('issues', []):
                severity = issue.get('severity', 'unknown')
                desc = issue.get('description', '')
                print(f"    [{severity}] {desc}")

        steps_complete += 1
    else:
        print("  Status: NOT STARTED")

    # === Overall Summary ===
    print("\n" + "=" * 70)
    print("OVERALL PROGRESS")
    print("=" * 70)
    print(f"Steps completed: {steps_complete}/{total_steps}")

    progress_bar = "[" + "#" * steps_complete + "." * (total_steps - steps_complete) + "]"
    print(f"Progress: {progress_bar} {steps_complete*100//total_steps}%")

    if steps_complete == total_steps:
        print("\nDesign pipeline COMPLETE. Ready for schematic generation.")
    else:
        next_step = steps_complete + 1
        print(f"\nNext step: Step {next_step}")
        step_names = {
            1: "Extract primary parts from FSD",
            2: "Research supporting parts",
            3: "Make design decisions",
            4: "Finalize parts list",
            5: "Generate connections",
            6: "Validate design"
        }
        print(f"  {step_names.get(next_step, 'Unknown step')}")

    return steps_complete == total_steps


def main():
    success = summarize()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
