# Step 3: Design Options and Questions

Analyze `design/work/step2_parts_extended.yaml` and identify all design choices that require user decisions.

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid:**

```
□ design/work/step2_parts_complete.yaml exists (or step2_parts_extended.yaml)
□ design/work/decisions.yaml exists
□ All symbols exist in JLCPCB library (run ensure_symbols.py --dry-run)
```

**Quick validation:**
```bash
ls -la design/work/step2_parts_complete.yaml
python scripts/ensure_symbols.py --parts work/step2_parts_complete.yaml --dry-run
```

**If prerequisites fail → Go back to Step 2 and complete it first!**

---

## Output Format

Write to `design/work/step3_design_options.yaml`:

```yaml
# step3_design_options.yaml
# Generated from: step2_parts_extended.yaml
# Date: [YYYY-MM-DD]

options:
  - id: power_topology
    question: "What power topology should be used?"
    context: "Battery-powered device needs efficient regulation"
    affects:
      - ldo
      - battery_charger
    choices:
      - value: "linear_ldo"
        description: "Linear LDO (AMS1117-3.3)"
        pros:
          - "Simple design"
          - "Low noise"
          - "Low cost"
        cons:
          - "Low efficiency (60-70%)"
          - "Heat dissipation at high current"
        recommendation: false

      - value: "buck_converter"
        description: "Switching buck converter"
        pros:
          - "High efficiency (85-95%)"
          - "Better battery life"
        cons:
          - "More complex design"
          - "Potential EMI issues"
          - "Higher cost"
        recommendation: true
        reason: "Better for battery-powered portable device"

  - id: usb_esd_protection
    question: "Add dedicated USB ESD protection?"
    context: "USB-C port exposed to external connections"
    affects:
      - usb_connector
    choices:
      - value: "yes"
        description: "Add TPD2E001 or similar ESD diodes"
        pros:
          - "Better protection"
          - "IEC 61000-4-2 compliance"
        cons:
          - "Additional cost"
          - "Two more components"
        recommendation: true
        reason: "Best practice for consumer devices"

      - value: "no"
        description: "Rely on MCU internal protection"
        pros:
          - "Simpler design"
          - "Lower cost"
        cons:
          - "Risk of ESD damage"
        recommendation: false

questions:
  - id: q_antenna_type
    question: "What type of FM antenna will be used?"
    context: "SI4735 needs antenna matching network"
    options:
      - "Wire whip antenna (simple)"
      - "PCB trace antenna (compact)"
      - "External connector (flexible)"
    default: "Wire whip antenna"
    impact: "Affects RF matching network design"

  - id: q_oled_interface
    question: "What OLED display will be used?"
    context: "Need to confirm I2C address and pin count"
    options:
      - "SSD1306 128x64 I2C"
      - "SSD1306 128x32 I2C"
      - "SH1106 128x64 I2C"
    default: "SSD1306 128x64 I2C"
    impact: "Affects header pinout and pull-up resistor values"

missing_info:
  - item: "Battery capacity"
    needed_for: "Charge current resistor calculation"
    default_assumption: "1000mAh, so PROG resistor = 1.2k for 1A charge"

  - item: "Operating temperature range"
    needed_for: "Component selection (standard vs extended temp)"
    default_assumption: "0-50°C consumer grade"
```

## Rules

1. **Identify ALL design choices** - anything with multiple valid approaches
2. **Provide pros/cons** for each option
3. **Give recommendations** with reasoning
4. **Note defaults** for questions without critical impact
5. **List missing info** that would improve the design

## Categories of Options

- **Architecture choices** - power topology, communication protocols
- **Component selection** - specific part vs alternatives
- **Protection features** - ESD, reverse polarity, overcurrent
- **Optional features** - test points, debug headers, status LEDs

## STOP HERE

After writing `step3_design_options.yaml`:

**STOP and wait for the user to create `design/work/decisions.yaml`**

Do not proceed to Step 4 until decisions are provided.

---

## Exit Validation Checklist

**Before proceeding to Step 4, ALL checks must pass:**

### 1. File Exists
```bash
ls -la design/work/step3_design_options.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step3_design_options.yaml'))"
```
- [ ] `step3_design_options.yaml` exists and is valid YAML

### 2. All Options Have Required Fields
- [ ] Every option has `id`, `question`, `context`, `affects`, `choices`
- [ ] Every choice has `value`, `description`, `pros`, `cons`
- [ ] At least one choice per option has `recommendation: true`

### 3. Questions Are Complete
- [ ] All questions have `id`, `question`, `options`, `default`
- [ ] Missing info section documents any assumptions

### 4. User Decisions Received
- [ ] User has provided decisions for all options
- [ ] decisions.yaml is updated with new choices (if any)

---

## If Validation Fails

**DO NOT proceed to Step 4!**

1. Identify which check(s) failed
2. Fix the issue in step3_design_options.yaml
3. Re-run validation
4. Only proceed when ALL checks pass

```
⚠️  VALIDATION LOOP: Step 3 → Validate → Fix if needed → Validate again → Step 4
```
