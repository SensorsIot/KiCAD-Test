# Step 6: Validation

Verify design completeness and correctness before schematic generation.

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid:**

```
□ design/work/step4_final_parts.yaml exists
□ design/work/step5_connections.yaml exists
□ design/input/FSD_*.md exists
□ All symbols exist in JLCPCB library
```

**Quick validation:**
```bash
ls -la design/work/step4_final_parts.yaml design/work/step5_connections.yaml
python scripts/ensure_symbols.py --parts work/step4_final_parts.yaml --dry-run
```

**If prerequisites fail → Go back to previous step and complete it first!**

---

## Input Files

- `design/input/FSD_*.md` - Original requirements
- `design/work/step4_final_parts.yaml` - Final parts
- `design/work/step5_connections.yaml` - All connections
- `design/sources/references.md` - Reference documents

## Output Format

Write to `design/work/step6_validation.yaml`:

```yaml
# step6_validation.yaml
# Design validation report
# Date: [YYYY-MM-DD]

summary:
  status: PASS  # PASS | PASS_WITH_WARNINGS | FAIL
  total_parts: <count>
  total_nets: <count>
  errors_found: <count>
  warnings_found: <count>

# === FSD Requirements Coverage ===
fsd_coverage:
  - requirement: "<FSD requirement description>"
    section: "<FSD section number>"
    status: COVERED  # COVERED | PARTIAL | MISSING
    implemented_by: <part_id>

  - requirement: "<FSD requirement description>"
    section: "<FSD section number>"
    status: COVERED
    implemented_by: [<part_id_1>, <part_id_2>]

  - requirement: "<FSD requirement description>"
    section: "<FSD section number>"
    status: PARTIAL
    implemented_by: <part_id>
    note: "<explanation of partial coverage>"

# === Electrical Checks ===
electrical_checks:
  power_rails:
    - rail: "<POWER_RAIL_NAME>"       # e.g., +3V3, +5V, VBAT
      source: <source_part_id>
      loads: [<part_id_1>, <part_id_2>, <part_id_3>]
      estimated_current_ma: <value>
      source_capacity_ma: <value>
      status: OK  # OK | WARNING | FAIL

    - rail: "<POWER_RAIL_NAME>"
      source: <source_part_id>
      loads: [<part_id_1>, <part_id_2>]
      voltage_range: "<min>-<max>V"
      status: OK

  bypass_capacitors:
    - component: <ic_part_id>
      required: <count>
      provided: <count>
      status: OK

  pull_resistors:
    - bus: <BUS_NAME>                 # e.g., I2C, SPI
      pull_ups_required: <count>
      pull_ups_provided: <count>
      value: "<resistance>"
      status: OK

# === Errors Found ===
# Only report actual errors that prevent schematic generation
errors:
  - id: 1
    severity: error  # warning | error | critical
    category: <category>  # electrical | connection | missing_part | missing_symbol
    description: "<error description>"
    affected: [<part_id or net_name>]

  - id: 2
    severity: warning
    category: <category>
    description: "<warning description>"
    affected: [<part_id>]

# === Statistics ===
statistics:
  by_category:
    <category_1>: <count>
    <category_2>: <count>
    # ... list all categories with counts

  by_prefix:
    U: <count>
    R: <count>
    C: <count>
    D: <count>
    J: <count>
    # ... list all prefixes with counts
```

## Validation Checks

### 1. Completeness
- [ ] All FSD requirements addressed
- [ ] Every part has at least one connection
- [ ] All IC power pins connected to power rail
- [ ] All IC ground pins connected to GND

### 2. Electrical
- [ ] No duplicate pin assignments (same pin on multiple nets)
- [ ] No single-pin nets (except test points)
- [ ] Bypass capacitors have both pins connected
- [ ] Voltage levels compatible between connected parts

## After YAML

Run summary script:
```bash
python design/scripts/summarize_progress.py
```

This generates a human-readable summary of the design.

---

## Exit Validation Checklist

**Before proceeding to Schematic Generation, ALL checks must pass:**

### 1. Validation Report Complete
```bash
ls -la design/work/step6_validation.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step6_validation.yaml'))"
```
- [ ] `step6_validation.yaml` exists and is valid YAML

### 2. No Critical Errors
```bash
grep -E "severity: critical|severity: error" design/work/step6_validation.yaml
```
- [ ] No critical or error severity items (grep should return nothing)
- [ ] Overall status is PASS or PASS_WITH_WARNINGS

### 3. FSD Coverage Complete
- [ ] All FSD requirements have status COVERED or PARTIAL
- [ ] No requirements have status MISSING or NOT_ADDRESSED
- [ ] Any PARTIAL items have explanatory notes

### 4. Electrical Checks Pass
- [ ] All power rails have sufficient capacity
- [ ] All bypass capacitors present
- [ ] All pull resistors present and correctly valued

### 5. Files Ready for Schematic Generation
```bash
# Final check of all required files
ls -la design/work/step4_final_parts.yaml \
       design/work/step5_connections.yaml \
       design/work/step6_validation.yaml

# Symbols check
python scripts/ensure_symbols.py --parts work/step4_final_parts.yaml --dry-run
```
- [ ] All YAML files exist and are valid
- [ ] All symbols present in library

---

## If Validation Fails

**DO NOT proceed to schematic generation!**

1. Review the errors in step6_validation.yaml
2. Go back to the appropriate step to fix:
   - Parts issues → Step 4
   - Connection issues → Step 5
   - Missing symbols → Run ensure_symbols.py
3. Re-run Step 6 validation
4. Only proceed when status is PASS or PASS_WITH_WARNINGS

```
⚠️  VALIDATION LOOP: Step 6 → Review Issues → Fix in earlier step → Re-validate → Generate Schematic

The pipeline ensures quality at every step:
Step 1 ──► Step 2 ──► Step 3 ──► Step 4 ──► Step 5 ──► Step 6 ──► Schematic
   ▲          ▲          ▲          ▲          ▲          ▲
   └──────────┴──────────┴──────────┴──────────┴──────────┘
                    Loop back if validation fails
```

---

## Ready for Schematic Generation

When all validations pass, proceed to generate the schematic:

```bash
python scripts/run_pipeline.py
```

This will:
1. Generate pin_model.json from parts + connections
2. Verify all symbols exist in library
3. Generate KiCAD schematic
4. Run ERC verification
