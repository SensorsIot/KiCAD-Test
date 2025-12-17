# Step 2: Generate Complete Parts List

**CRITICAL: Read `design/work/decisions.yaml` FIRST and use those exact values!**

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid before proceeding:**

```
□ design/work/decisions.yaml exists
□ design/work/step1_parts.csv exists
□ design/input/FSD_*.md exists
```

**Quick validation:**
```bash
# Check files exist
ls -la design/work/decisions.yaml design/work/step1_parts.csv

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('design/work/decisions.yaml'))"
```

**If prerequisites fail → Go back to Step 1 and complete it first!**

---

## Input Files (READ THESE FIRST!)

1. **`design/work/decisions.yaml`** - User's selected parts from Step 1
2. **`design/work/step1_parts.csv`** - All parts with LCSC codes and pricing
3. **`design/input/FSD_*.md`** - Original specification

## Process

### Step 2.1: Load Decisions

Read `decisions.yaml` and extract all selected parts:

```yaml
# Example decisions.yaml
component_choices:
  mcu: "ESP32-S3-MINI-1-N8"
  mcu_lcsc: "C2913206"

  ldo: "ME6211C33M5G"          # <-- USE THIS EXACT VALUE
  ldo_lcsc: "C82942"           # <-- USE THIS EXACT LCSC CODE
  ldo_package: "SOT-23-5"      # <-- USE THIS EXACT PACKAGE

  rotary_encoder: "EC11J1524413"  # <-- USE THIS, NOT ALTERNATIVES
  rotary_encoder_lcsc: "C370986"
  rotary_encoder_package: "SMD"
```

**YOU MUST USE THE EXACT VALUES FROM decisions.yaml!**
- Do NOT substitute different parts
- Do NOT use alternative LCSC codes
- Do NOT change package types

### Step 2.2: Research Supporting Parts

For each primary part from decisions.yaml:
1. Find official datasheet
2. Identify ALL required external components
3. Add supporting parts with `belongs_to` reference

### Step 2.3: Generate Output

Write to `design/work/step2_parts_complete.yaml`:

```yaml
# step2_parts_complete.yaml
# Generated from: decisions.yaml + FSD
# Date: [YYYY-MM-DD]

parts:
  # ===========================================================================
  # ICs - Active Components (FROM decisions.yaml!)
  # ===========================================================================
  - id: mcu
    name: "ESP32-S3-MINI-1 Module"
    part: "ESP32-S3-MINI-1-N8"      # FROM decisions.yaml
    package: "Module"
    prefix: U
    category: microcontroller
    quantity: 1
    lcsc: "C2913206"                # FROM decisions.yaml

  - id: ldo
    name: "3.3V LDO Regulator"
    part: "ME6211C33M5G"            # FROM decisions.yaml - NOT AMS1117!
    package: "SOT-23-5"             # FROM decisions.yaml
    prefix: U
    category: power
    quantity: 1
    lcsc: "C82942"                  # FROM decisions.yaml

  - id: encoder_tuning
    name: "Rotary Encoder - Tuning"
    part: "EC11J1524413"            # FROM decisions.yaml - NOT EC11E18244A5!
    package: "SMD"                  # FROM decisions.yaml
    prefix: ENC
    category: ui
    quantity: 1
    lcsc: "C370986"                 # FROM decisions.yaml

  # ===========================================================================
  # Supporting Parts (added based on datasheet research)
  # ===========================================================================
  - id: c_ldo_in
    name: "LDO Input Cap"
    part: "C"
    value: "10uF"
    package: "0805"                 # FROM decisions.yaml passive_size or 0805 for bulk
    prefix: C
    category: passive
    quantity: 1
    lcsc: "C15850"
    belongs_to: ldo                 # Links to parent part
```

## Validation Checklist

Before saving, verify:

- [ ] **Every part in decisions.yaml appears with EXACT same values**
- [ ] Every `part:` field matches decisions.yaml exactly
- [ ] Every `lcsc:` field matches decisions.yaml exactly
- [ ] Every `package:` field matches decisions.yaml exactly
- [ ] All supporting parts have `belongs_to:` reference
- [ ] Passive sizes match `passive_size` from decisions.yaml

## Common Mistakes to Avoid

**WRONG:**
```yaml
- id: ldo
  part: "AMS1117-3.3"      # WRONG! User chose ME6211C33M5G
  lcsc: "C6186"            # WRONG! Should be C82942
```

**CORRECT:**
```yaml
- id: ldo
  part: "ME6211C33M5G"     # Matches decisions.yaml
  lcsc: "C82942"           # Matches decisions.yaml
```

**WRONG:**
```yaml
- id: encoder_tuning
  part: "EC11E18244A5"     # WRONG! User chose SMD encoder
  package: "TH"            # WRONG! Should be SMD
```

**CORRECT:**
```yaml
- id: encoder_tuning
  part: "EC11J1524413"     # Matches decisions.yaml
  package: "SMD"           # Matches decisions.yaml
```

## Required Fields

| Field | Required | Description |
|-------|----------|-------------|
| id | Yes | Unique identifier (snake_case) |
| name | Yes | Human-readable name |
| part | Yes | Part number - **MUST MATCH decisions.yaml** |
| package | Yes | Footprint - **MUST MATCH decisions.yaml** |
| prefix | Yes | Schematic prefix (R/C/U/D/J/SW/ENC/Y) |
| category | Yes | microcontroller/power/radio/ui/connector/passive |
| quantity | Yes | Number needed |
| lcsc | Yes | LCSC code - **MUST MATCH decisions.yaml** |
| belongs_to | If supporting | Parent part id |
| value | If passive | Resistance/capacitance value |

## Prefix Reference

| Prefix | Component Type |
|--------|---------------|
| U | IC (integrated circuit) |
| R | Resistor |
| C | Capacitor |
| D | Diode, LED |
| J | Connector |
| SW | Switch, Button |
| ENC | Encoder |
| Y | Crystal, Oscillator |
| TP | Test Point |
| L | Inductor |
| F | Fuse |

## After YAML Generation

### 1. Validate Parts List

```bash
python scripts/validate_step2.py
```

Verify:
- All LCSC codes match decisions.yaml
- All parts have required fields
- No duplicate IDs

### 2. Ensure All Symbols Exist in Library

**CRITICAL: Run this before proceeding!**

The central JLCPCB symbol library is located at:
`KiCAD-Generator-tools/libs/JLCPCB/symbol/JLCPCB.kicad_sym`

```bash
# From project directory - uses central library automatically
python /path/to/KiCAD-Generator-tools/scripts/ensure_symbols.py --parts work/step2_parts_complete.yaml

# Or specify library explicitly
python scripts/ensure_symbols.py --parts work/step2_parts_complete.yaml --library /path/to/KiCAD-Generator-tools/libs/JLCPCB/symbol/JLCPCB.kicad_sym
```

This script will:
1. Extract all LCSC codes from the parts list
2. Check which symbols are missing from JLCPCB.kicad_sym
3. Download missing symbols using JLC2KiCadLib
4. Append them to the library

**If ensure_symbols.py is not available**, manually download each missing symbol:

```bash
# For each LCSC code not in library:
JLC2KiCadLib C82942 -dir /tmp/jlc_temp

# Then manually add the symbol to JLCPCB.kicad_sym
```

### 3. Verify Library Contains All Parts

After running ensure_symbols.py, verify the central library:

```bash
# Count symbols in central library
grep -c '(symbol "' /path/to/KiCAD-Generator-tools/libs/JLCPCB/symbol/JLCPCB.kicad_sym

# List all LCSC codes in library
grep -oP 'LCSC"\s+"K?\K[^"]+' /path/to/KiCAD-Generator-tools/libs/JLCPCB/symbol/JLCPCB.kicad_sym | sort -u
```

### 4. Document Any Issues

List in step2 output:
- Parts where symbols could not be downloaded
- Parts requiring manual symbol creation
- Any pin name mismatches discovered

---

## Exit Validation Checklist

**Before proceeding to Step 3, ALL checks must pass:**

### 1. File Exists
```bash
ls -la design/work/step2_parts_complete.yaml
```
- [ ] `step2_parts_complete.yaml` exists and is valid YAML

### 2. Decisions Match (CRITICAL!)

For EVERY component in `decisions.yaml`, verify the EXACT values appear in `step2_parts_complete.yaml`:

```bash
# Extract key parts from decisions.yaml and verify they exist in step2
grep -E "(mcu|ldo|encoder|radio).*:" design/work/decisions.yaml
grep -E "(mcu|ldo|encoder|radio)" design/work/step2_parts_complete.yaml
```

- [ ] MCU part number matches decisions.yaml exactly
- [ ] MCU LCSC code matches decisions.yaml exactly
- [ ] LDO part number matches decisions.yaml exactly
- [ ] LDO LCSC code matches decisions.yaml exactly
- [ ] Encoder part number matches decisions.yaml exactly
- [ ] Encoder LCSC code matches decisions.yaml exactly
- [ ] All other selected parts match decisions.yaml exactly

### 3. Required Fields Present

Every part entry must have:
- [ ] `id` - unique identifier
- [ ] `name` - human-readable name
- [ ] `part` - part number (matching decisions.yaml for main parts)
- [ ] `package` - footprint
- [ ] `prefix` - R/C/U/D/J/SW/ENC/Y
- [ ] `category` - component category
- [ ] `quantity` - number needed
- [ ] `lcsc` - LCSC code (matching decisions.yaml for main parts)

### 4. Symbols Exist in Library

```bash
python scripts/ensure_symbols.py --parts work/step2_parts_complete.yaml --dry-run
```

- [ ] All symbols present (no "Missing X symbols" message)
- [ ] If missing, run without `--dry-run` to download them
- [ ] Re-verify after download

### 5. No Duplicate IDs

```bash
grep "^  - id:" design/work/step2_parts_complete.yaml | sort | uniq -d
```

- [ ] No duplicate IDs (command should produce no output)

---

## If Validation Fails

**DO NOT proceed to Step 3!**

1. Identify which check(s) failed
2. **If decisions don't match**: Re-read decisions.yaml and fix step2_parts_complete.yaml
3. **If symbols missing**: Run ensure_symbols.py to download them
4. **If fields missing**: Add the required fields
5. Re-run ALL validation checks
6. Only proceed when ALL checks pass

```
⚠️  VALIDATION LOOP: Step 2 → Validate → Fix if needed → Validate again → Step 3

Common failure: Using wrong part/LCSC from memory instead of reading decisions.yaml!
Always copy-paste values directly from decisions.yaml!
```
