#!/usr/bin/env python3
"""
Validate step3_decisions.yaml

Checks:
- YAML parses correctly
- Each decision has required fields
- Selected options are valid
- All decisions have been made (no pending)
"""

import sys
import yaml
from pathlib import Path

REQUIRED_DECISION_FIELDS = ['topic', 'options', 'selected', 'rationale']


def validate(filepath: Path) -> list:
    """Validate step3 file and return list of errors."""
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

    # Check decisions exists
    if 'decisions' not in data:
        return ["Missing 'decisions' key"]

    decisions = data['decisions']
    if not isinstance(decisions, list):
        return ["'decisions' must be a list"]

    if len(decisions) == 0:
        errors.append("WARNING: No decisions defined")

    # Track topics for uniqueness
    seen_topics = set()

    for i, decision in enumerate(decisions):
        prefix = f"decisions[{i}]"

        if not isinstance(decision, dict):
            errors.append(f"{prefix}: Must be a dictionary")
            continue

        topic = decision.get('topic', f'<no topic at index {i}>')

        # Check required fields
        for field in REQUIRED_DECISION_FIELDS:
            if field not in decision:
                errors.append(f"{prefix} ({topic}): Missing required field '{field}'")

        # Check topic uniqueness
        if topic in seen_topics:
            errors.append(f"{prefix}: Duplicate topic '{topic}'")
        seen_topics.add(topic)

        # Check options is a list
        options = decision.get('options', [])
        if not isinstance(options, list):
            errors.append(f"{prefix} ({topic}): 'options' must be a list")
        elif len(options) < 2:
            errors.append(f"{prefix} ({topic}): Should have at least 2 options")
        else:
            # Check each option has required fields
            for j, opt in enumerate(options):
                if not isinstance(opt, dict):
                    errors.append(f"{prefix} ({topic}): options[{j}] must be a dictionary")
                else:
                    if 'name' not in opt:
                        errors.append(f"{prefix} ({topic}): options[{j}] missing 'name'")

        # Check selected is valid
        selected = decision.get('selected')
        if selected is None:
            errors.append(f"PENDING: {prefix} ({topic}): No option selected yet")
        elif isinstance(options, list):
            option_names = [opt.get('name') for opt in options if isinstance(opt, dict)]
            if selected not in option_names:
                errors.append(f"{prefix} ({topic}): Selected '{selected}' not in options {option_names}")

        # Check rationale not empty
        rationale = decision.get('rationale', '')
        if selected and (not rationale or str(rationale).strip() == ''):
            errors.append(f"{prefix} ({topic}): Missing rationale for selection")

    return errors


def main():
    script_dir = Path(__file__).parent.parent
    filepath = script_dir / "work" / "step3_decisions.yaml"

    print(f"Validating: {filepath}")
    print("=" * 60)

    errors = validate(filepath)

    # Separate pending, warnings, and errors
    pending = [e for e in errors if e.startswith("PENDING")]
    warnings = [e for e in errors if e.startswith("WARNING")]
    real_errors = [e for e in errors if not e.startswith("WARNING") and not e.startswith("PENDING")]

    if real_errors:
        print("VALIDATION FAILED\n")
        for error in real_errors:
            print(f"  {error}")
        if pending:
            print("\nPending decisions:")
            for p in pending:
                print(f"  {p}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  {warning}")
        print(f"\nTotal errors: {len(real_errors)}")
        sys.exit(1)
    elif pending:
        print("VALIDATION INCOMPLETE - Decisions pending\n")
        for p in pending:
            print(f"  {p}")
        print(f"\nPending decisions: {len(pending)}")
        sys.exit(2)  # Special exit code for pending
    else:
        print("VALIDATION PASSED")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  {warning}")

        # Print summary
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        decisions = data.get('decisions', [])
        print(f"\nSummary: {len(decisions)} decisions documented")

        # List decisions
        for d in decisions:
            topic = d.get('topic', 'unknown')
            selected = d.get('selected', 'none')
            print(f"  - {topic}: {selected}")

        sys.exit(0)


if __name__ == "__main__":
    main()
