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
    - <part_id>.GND
    - <part_id>.GND
    - <capacitor_id>.2        # Capacitor pin 2 = GND side

  <POWER_RAIL_NAME>:          # e.g., VBAT, +3V3, +5V
    - <part_id>.<power_pin>
    - <capacitor_id>.1        # Capacitor pin 1 = power side

  # === Signal Buses ===
  <SIGNAL_NAME>:              # e.g., SDA, SCL, MOSI, CS
    - <part_id>.<signal_pin>
    - <part_id>.<signal_pin>
    - <pullup_resistor_id>.2  # Resistor pin 2 = signal side

# Format: component_id.PIN_NAME
# - Use component id from step4_final_parts.yaml
# - Use pin name from datasheet (or number for passives)
# - For passives: use .1 and .2

# Explicitly unconnected pins
no_connect:
  - component: <part_id>
    pin: <pin_name>
    reason: "<why not connected>"

# Test points (optional)
test_points:
  - net: <net_name>
    purpose: "<what this tests>"

# Net notes
notes:
  - net: <NET_NAME>
    note: "<description of the net, voltage range, current limit, etc.>"
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
