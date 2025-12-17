# Step 5: Generate Connections

Create all electrical connections based on `design/work/step4_final_parts.yaml` and FSD requirements.

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid:**

```
□ design/work/step4_final_parts.yaml exists
□ design/input/FSD_*.md exists
□ All symbols exist in JLCPCB library
□ No TBD values in step4_final_parts.yaml
```

**Quick validation:**
```bash
ls -la design/work/step4_final_parts.yaml
python scripts/ensure_symbols.py --parts work/step4_final_parts.yaml --dry-run
grep -i "TBD" design/work/step4_final_parts.yaml  # Should return nothing
```

**If prerequisites fail → Go back to Step 4 and complete it first!**

---

## Input Files

- `design/work/step4_final_parts.yaml` - Final parts list
- `design/input/FSD_*.md` - Original requirements

## Output Format

Write to `design/work/step5_connections.yaml`:

```yaml
# step5_connections.yaml
# Generated from: step4_final_parts.yaml
# Date: [YYYY-MM-DD]

nets:
  # === Power Rails ===
  GND:
    - mcu.GND
    - ldo.GND
    - battery_charger.GND
    - c_mcu_bypass_1.2
    - c_ldo_in.2
    - c_ldo_out.2

  VBAT:
    - battery_charger.BAT
    - battery_connector.1
    - ldo.VIN
    - c_ldo_in.1

  +3V3:
    - ldo.VOUT
    - mcu.3V3
    - c_ldo_out.1
    - c_mcu_bypass_1.1
    - r_i2c_sda.1
    - r_i2c_scl.1

  # === I2C Bus ===
  SDA:
    - mcu.GPIO4
    - radio_ic.SDIO
    - oled_header.SDA
    - r_i2c_sda.2

  SCL:
    - mcu.GPIO5
    - radio_ic.SCLK
    - oled_header.SCL
    - r_i2c_scl.2

  # === USB ===
  USB_DP:
    - mcu.GPIO20
    - usb_connector.DP

  USB_DM:
    - mcu.GPIO19
    - usb_connector.DM

# Format: component_id.PIN_NAME
# - Use component id from step4_final_parts.yaml
# - Use pin name from datasheet (or number for passives)
# - For passives: use .1 and .2

# Explicitly unconnected pins
no_connect:
  - component: mcu
    pin: GPIO0
    reason: "Strapping pin, directly connected internally"

  - component: radio_ic
    pin: GPO2
    reason: "General purpose output, not used in this design"

# Test points (optional)
test_points:
  - net: +3V3
    purpose: "Power rail monitoring"

  - net: SDA
    purpose: "I2C debug"

# Net notes
notes:
  - net: VBAT
    note: "Battery voltage, 3.0-4.2V from Li-ion cell"

  - net: +3V3
    note: "Main logic supply, max 500mA from AMS1117"
```

## Connection Rules

1. **Every IC power pin must connect to power rail**
2. **Every IC ground pin must connect to GND**
3. **Bypass capacitors**: one pin to power, one pin to GND
4. **Pull-up resistors**: one pin to signal, one pin to power rail
5. **Pull-down resistors**: one pin to signal, one pin to GND
6. **No single-pin nets** (unless marked as test point or NC)

## Pin Reference Format

- `component_id.PIN_NAME` - IC pins use datasheet pin names
- `component_id.1` or `component_id.2` - Passive component pins
- Pin names should match datasheet (e.g., `GND`, `VCC`, `GPIO4`, `SDIO`)

## Verification Checklist

For each functional block, verify:
- [ ] All power pins connected
- [ ] All ground pins connected
- [ ] All signal connections per FSD
- [ ] Bypass capacitors properly connected
- [ ] Pull-up/pull-down resistors connected
- [ ] No duplicate pin usage (same pin on multiple nets)

## After YAML

Run validator:
```bash
python design/scripts/validate_step5.py
```

If validation fails, fix errors and rerun.

---

## Exit Validation Checklist

**Before proceeding to Step 6 (Schematic Generation), ALL checks must pass:**

### 1. File Exists and Valid
```bash
ls -la design/work/step5_connections.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step5_connections.yaml'))"
```
- [ ] `step5_connections.yaml` exists and is valid YAML

### 2. All Power Connections Present
- [ ] Every IC has VCC/VDD connected to appropriate power rail
- [ ] Every IC has GND pin(s) connected to GND net
- [ ] All bypass capacitors connected (one pin to power, one to GND)

### 3. Component IDs Match
```bash
# Extract all component IDs from parts file
grep "^  - id:" design/work/step4_final_parts.yaml | cut -d: -f2 | sort > /tmp/parts_ids.txt

# Extract all component references from connections
grep -oE "[a-z_]+\." design/work/step5_connections.yaml | sed 's/\.//' | sort -u > /tmp/conn_ids.txt

# Check for mismatches
diff /tmp/parts_ids.txt /tmp/conn_ids.txt
```
- [ ] All component IDs in connections exist in parts list
- [ ] No typos in component IDs

### 4. Pin Names Valid
- [ ] IC pin names match datasheet (e.g., GPIO4, SDIO, VCC)
- [ ] Passive component pins use `.1` and `.2` format
- [ ] No invalid pin references

### 5. No Single-Pin Nets
- [ ] Every net has at least 2 connections (except test points and NC pins)
- [ ] Single-pin items are explicitly marked as `test_points` or `no_connect`

### 6. No Duplicate Pin Usage
```bash
# Check for pins appearing in multiple nets
grep -E "^\s+-\s+\w+\.\w+" design/work/step5_connections.yaml | sort | uniq -d
```
- [ ] No pin appears in multiple nets (grep should return nothing)

### 7. FSD Requirements Met
Cross-reference with FSD:
- [ ] All I2C connections per FSD
- [ ] All SPI connections per FSD
- [ ] All GPIO assignments per FSD
- [ ] All power rails per FSD

---

## If Validation Fails

**DO NOT proceed to Step 6!**

1. Identify which check(s) failed
2. Fix the issue in step5_connections.yaml
3. Re-run ALL validation checks
4. Only proceed when ALL checks pass

```
⚠️  VALIDATION LOOP: Step 5 → Validate → Fix if needed → Validate again → Step 6

Common failures:
- Typo in component ID (use exact id from step4_final_parts.yaml)
- Wrong pin name (check datasheet)
- Missing power/ground connections
```
