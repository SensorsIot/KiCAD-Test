# Step 4: Apply Decisions and Finalize Parts

Apply decisions from `design/work/decisions.yaml` to create the final parts list.

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid:**

```
□ design/work/step2_parts_extended.yaml exists
□ design/work/step3_design_options.yaml exists
□ design/work/decisions.yaml exists and contains user choices
```

**Quick validation:**
```bash
ls -la design/work/step2_parts_extended.yaml design/work/step3_design_options.yaml design/work/decisions.yaml
python -c "import yaml; yaml.safe_load(open('design/work/decisions.yaml'))"
```

**If prerequisites fail → Go back to previous step and complete it first!**

---

## Input Files

- `design/work/step2_parts_extended.yaml` - Extended parts list
- `design/work/step3_design_options.yaml` - Options presented
- `design/work/decisions.yaml` - User decisions

## Output Format

Write to `design/work/step4_final_parts.yaml`:

```yaml
# step4_final_parts.yaml
# Finalized from: step2_parts_extended.yaml + decisions.yaml
# Date: [YYYY-MM-DD]

parts:
  # === Microcontroller ===
  - id: mcu
    name: "Main Microcontroller"
    part: "ESP32-S3-MINI-1-N8"
    package: "SMD-Module"
    prefix: U
    category: microcontroller
    quantity: 1
    belongs_to: null
    lcsc_hint: "ESP32-S3-MINI"

  - id: c_mcu_bypass_1
    name: "MCU 3V3 Bypass"
    part: "100nF"
    package: "0603"
    prefix: C
    category: passive
    quantity: 3
    belongs_to: mcu
    lcsc_hint: "100nF 0603 X7R"

  # === Power ===
  - id: ldo
    name: "3.3V LDO Regulator"
    part: "AMS1117-3.3"
    package: "SOT-223"
    prefix: U
    category: power
    quantity: 1
    belongs_to: null
    decision_applied: "power_topology=linear_ldo"
    lcsc_hint: "AMS1117-3.3"

  # ... all parts with final values
```

## Rules

1. **No TBD values** - all parts must have specific values/part numbers
2. **Apply all decisions** - reference which decision was applied
3. **Add prefix** - R, C, U, D, J, SW, Y, etc.
4. **Add lcsc_hint** - search term for JLCPCB lookup
5. **Consolidate identical parts** - combine into single entry with quantity
6. **Remove parts eliminated by decisions** - if decision removes an option

## Required Fields

| Field | Required | Description |
|-------|----------|-------------|
| id | Yes | Unique identifier |
| name | Yes | Human-readable name |
| part | Yes | Part number or value |
| package | Yes | Footprint package |
| prefix | Yes | Schematic prefix (R/C/U/etc) |
| category | Yes | Component category |
| quantity | Yes | Number needed |
| belongs_to | Yes | Parent id or null |
| lcsc_hint | Yes | JLCPCB search term |
| decision_applied | If applicable | Which decision affected this part |

## Prefix Reference

- `R` - Resistor
- `C` - Capacitor
- `U` - IC (integrated circuit)
- `D` - Diode, LED
- `J` - Connector
- `SW` - Switch
- `Y` - Crystal, oscillator
- `L` - Inductor
- `F` - Fuse
- `ENC` - Encoder
- `ANT` - Antenna

## After YAML

Run validator:
```bash
python design/scripts/validate_step4.py
```

If validation fails, fix errors and rerun.

---

## Exit Validation Checklist

**Before proceeding to Step 5, ALL checks must pass:**

### 1. File Exists and Valid
```bash
ls -la design/work/step4_final_parts.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step4_final_parts.yaml'))"
```
- [ ] `step4_final_parts.yaml` exists and is valid YAML

### 2. No TBD Values
```bash
grep -i "TBD\|TODO\|PLACEHOLDER" design/work/step4_final_parts.yaml
```
- [ ] No TBD, TODO, or placeholder values remain (grep should return nothing)

### 3. All Decisions Applied
- [ ] Every decision from decisions.yaml is reflected in the parts list
- [ ] `decision_applied` field references the decision for affected parts

### 4. Required Fields Present
Every part must have:
- [ ] `id` - unique identifier
- [ ] `name` - human-readable name
- [ ] `part` - specific part number (no generic values)
- [ ] `package` - footprint
- [ ] `prefix` - R/C/U/D/J/SW/ENC/Y
- [ ] `category` - component category
- [ ] `quantity` - number needed
- [ ] `belongs_to` - parent id or null
- [ ] `lcsc_hint` - JLCPCB search term

### 5. No Duplicate IDs
```bash
grep "^  - id:" design/work/step4_final_parts.yaml | sort | uniq -d
```
- [ ] No duplicate IDs (command should produce no output)

### 6. Symbols Exist
```bash
python scripts/ensure_symbols.py --parts work/step4_final_parts.yaml --dry-run
```
- [ ] All symbols present in library

---

## If Validation Fails

**DO NOT proceed to Step 5!**

1. Identify which check(s) failed
2. Fix the issue in step4_final_parts.yaml
3. Re-run ALL validation checks
4. Only proceed when ALL checks pass

```
⚠️  VALIDATION LOOP: Step 4 → Validate → Fix if needed → Validate again → Step 5
```
