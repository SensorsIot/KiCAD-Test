# Step 6: Validation and Summary

Perform comprehensive design review and generate validation report.

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
  status: PASS  # PASS | PASS_WITH_WARNINGS | NEEDS_REVIEW | FAIL
  total_parts: 45
  total_nets: 32
  issues_found: 2
  critical_issues: 0

# === FSD Requirements Coverage ===
fsd_coverage:
  - requirement: "ESP32-S3 microcontroller"
    section: "4.1"
    status: COVERED
    implemented_by: mcu

  - requirement: "USB-C for charging and programming"
    section: "5.1"
    status: COVERED
    implemented_by: [usb_connector, battery_charger]

  - requirement: "AM/FM radio reception"
    section: "4.2"
    status: COVERED
    implemented_by: [radio_ic, antenna_fm, antenna_am]

  - requirement: "OLED display"
    section: "7.1"
    status: PARTIAL
    implemented_by: oled_header
    note: "Header only, display not in BOM"

# === Electrical Checks ===
electrical_checks:
  power_rails:
    - rail: "+3V3"
      source: ldo
      loads: [mcu, radio_ic, oled_header, rgb_led]
      estimated_current_ma: 350
      source_capacity_ma: 800
      status: OK

    - rail: "VBAT"
      source: battery_connector
      loads: [ldo, battery_charger]
      voltage_range: "3.0-4.2V"
      status: OK

  bypass_capacitors:
    - component: mcu
      required: 3
      provided: 3
      status: OK

    - component: radio_ic
      required: 4
      provided: 4
      status: OK

  pull_resistors:
    - bus: I2C
      pull_ups_required: 2
      pull_ups_provided: 2
      value: "4.7k"
      status: OK

# === Best Practice Checks ===
best_practice:
  - check: "ESD protection on USB"
    status: PRESENT
    components: [esd_usb_dp, esd_usb_dm]

  - check: "Decoupling on all ICs"
    status: OK

  - check: "Test points for debug"
    status: MISSING
    recommendation: "Add test points for SDA, SCL, +3V3"
    severity: info

# === Issues Found ===
issues:
  - id: 1
    severity: warning
    category: best_practice
    description: "No test points defined"
    recommendation: "Add test points for power rails and I2C bus"
    affected: [design]

  - id: 2
    severity: info
    category: documentation
    description: "OLED display not in BOM"
    recommendation: "Add OLED module to BOM or note as user-supplied"
    affected: [oled_header]

# === Statistics ===
statistics:
  by_category:
    microcontroller: 1
    radio: 1
    power: 2
    connector: 4
    ui: 6
    passive: 31

  by_prefix:
    U: 4
    R: 8
    C: 18
    D: 3
    J: 4
    SW: 1
    ENC: 2
    Y: 1
    ANT: 2

# === Recommendations ===
recommendations:
  - "Consider adding reverse polarity protection on battery input"
  - "Add 0-ohm resistors for antenna tuning flexibility"
  - "Include programming header for development"
```

## Validation Checks

### 1. Completeness
- [ ] All FSD requirements addressed
- [ ] Every part connected
- [ ] All power pins connected
- [ ] All ground pins connected

### 2. Electrical
- [ ] Bypass capacitor values appropriate
- [ ] Pull-up/pull-down values correct
- [ ] Voltage levels compatible
- [ ] Current requirements met

### 3. Best Practice
- [ ] ESD protection on external interfaces
- [ ] Decoupling on all ICs
- [ ] Test points available
- [ ] Clear net naming

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

### 2. No Critical Issues
```bash
grep -E "severity: critical|severity: error" design/work/step6_validation.yaml
```
- [ ] No critical or error severity issues (grep should return nothing)
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

1. Review the issues in step6_validation.yaml
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
