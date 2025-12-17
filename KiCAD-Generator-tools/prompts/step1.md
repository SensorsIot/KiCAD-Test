# Step 1: Extract Primary Parts from FSD

Extract ALL parts from the FSD, including optional parts where the FSD requests design options.

**IMPORTANT:** No new parts will be added after this step. This is the complete parts list.

**This step focuses on:**
1. WHAT parts are needed (not which specific JLCPCB variants to use)
2. WHAT design options exist (protection circuits, optional features, etc.)
3. Capturing ALL alternatives mentioned in the FSD

---

## Process

### 1. Read the FSD Thoroughly

Identify all components mentioned in:
- Bill of Materials sections
- Block diagrams
- Interface specifications
- Pin allocations
- Any "or equivalent" mentions

**Also identify design choices NOT explicitly in FSD but important for a robust design:**
- Protection circuits (ESD, reverse polarity, overcurrent)
- Optional features (debug headers, test points)
- Interface options (antenna type, connector variants)

### 2. Extract Required Parts

For each component, capture:
- **Functional role** (what it does in the circuit)
- **Part number** from FSD (if specified)
- **LCSC code** from FSD (if specified)
- **Package** from FSD (if specified)
- **Key specifications** (voltage, current, value, etc.)

### 3. Identify Functional Alternatives

Add alternatives where **functionally reasonable**:

| When to Add Alternatives | Examples |
|--------------------------|----------|
| FSD says "or equivalent" | "AMS1117 or equivalent LDO" |
| Multiple valid topologies | Linear LDO vs switching regulator |
| Package variants exist | SMD vs through-hole encoder |
| Common substitutes exist | ME6211 vs AMS1117 (both 3.3V LDOs) |
| FSD mentions options | "0603 minimum" implies 0805 is also OK |

**Do NOT add alternatives for:**
- Specific ICs with unique functionality (SI4735, ESP32-S3)
- Parts where FSD is explicit about requirements
- Standard passives (just use FSD values)

### 4. Group Options Together

Parts that are alternatives to each other share the same `option_group`.
Only ONE part from each option group will be selected in Step 2.

### 5. Identify Design Options

Design options are choices that affect the circuit but aren't explicit part alternatives.
These need user decisions before finalizing the design.

**Common design options to consider:**

| Category | Option | Typical Choices |
|----------|--------|-----------------|
| Protection | USB ESD | Yes (add TVS/ESD IC) / No (rely on MCU) |
| Protection | Battery reverse polarity | None / Schottky diode / P-FET |
| Protection | Overcurrent | Fuse / PTC / None |
| Debug | UART header | Yes / No |
| Debug | SWD/JTAG header | Yes / No |
| Interface | Antenna connection | Wire pad / SMA connector / Headphone cable |
| Assembly | Through-hole parts | Allow TH / SMD only |

**For each design option, capture:**
- What the option is
- Available choices with pros/cons
- Recommended choice with reasoning
- Parts that would be added if "yes" (include in parts list with `conditional: true`)

---

## Output Format

Write to `design/work/step1_primary_parts.yaml`:

```yaml
# step1_primary_parts.yaml
# Extracted from: FSD_*.md
# Date: [YYYY-MM-DD]
#
# This file contains ALL parts including optional parts and alternatives.
# NO NEW PARTS will be added after this step.
# Step 2 will enrich with JLCPCB data (pricing, stock, variants).

parts:
  # === Microcontroller (no alternatives - FSD specifies exact part) ===
  - id: mcu
    name: "ESP32-S3 MCU Module"
    function: "Main microcontroller with WiFi/BLE"
    part_number: "ESP32-S3-MINI-1-N8"
    lcsc: "C2913206"              # From FSD
    package: "Module"
    category: microcontroller
    quantity: 1
    option_group: null            # No alternatives
    specs:
      voltage: "3.0-3.6V"
      flash: "8MB"

  # === Radio IC (no alternatives - specific functionality) ===
  - id: radio_ic
    name: "AM/FM/SW Radio Receiver"
    function: "Multi-band radio reception"
    part_number: "SI4735-D60-GU"
    lcsc: "C195417"               # From FSD (verify in Step 2)
    package: "SSOP-24"
    category: radio
    quantity: 1
    option_group: null
    specs:
      interface: "I2C"
      bands: "AM/FM/SW"

  # === LDO Regulator (alternatives exist) ===
  - id: ldo_ams1117
    name: "3.3V LDO Regulator"
    function: "Voltage regulation from battery to 3.3V"
    part_number: "AMS1117-3.3"
    lcsc: "C6186"                 # From FSD
    package: "SOT-223"
    category: power
    quantity: 1
    option_group: ldo_3v3         # Alternatives share this group
    specs:
      output_voltage: "3.3V"
      max_current: "1A"
      dropout: "1.1V"
      quiescent: "5mA"
    pros: "High current capacity, widely available"
    cons: "Higher dropout, higher quiescent current"

  - id: ldo_me6211
    name: "3.3V LDO Regulator"
    function: "Voltage regulation from battery to 3.3V"
    part_number: "ME6211C33M5G-N"
    lcsc: "C82942"
    package: "SOT-23-5"
    category: power
    quantity: 1
    option_group: ldo_3v3         # Same group as above
    specs:
      output_voltage: "3.3V"
      max_current: "500mA"
      dropout: "0.1V"
      quiescent: "40uA"
    pros: "Low dropout, ultra-low quiescent current, smaller"
    cons: "Lower max current (500mA vs 1A)"

  # === Rotary Encoder (SMD vs TH options) ===
  - id: encoder_smd
    name: "Rotary Encoder with Switch"
    function: "User input for tuning and volume"
    part_number: "EC11J1525402"   # SMD variant
    lcsc: null                    # To be found in Step 2
    package: "SMD"
    category: ui
    quantity: 2
    option_group: encoder
    specs:
      type: "Incremental quadrature"
      switch: "Integrated momentary"
    pros: "SMD assembly, no manual soldering"
    cons: "May need assembly fixture, typically more expensive"

  - id: encoder_th
    name: "Rotary Encoder with Switch"
    function: "User input for tuning and volume"
    part_number: "EC11E18244A5"   # Through-hole variant
    lcsc: null                    # To be found in Step 2
    package: "TH"
    category: ui
    quantity: 2
    option_group: encoder
    specs:
      type: "Incremental quadrature"
      switch: "Integrated momentary"
    pros: "Easier to source, often cheaper, more mechanical options"
    cons: "Requires manual soldering or selective assembly"

  # === Parts without alternatives (standard values from FSD) ===
  - id: c_bypass_100n
    name: "Bypass Capacitor"
    function: "IC power supply filtering"
    part_number: "100nF"
    lcsc: "C14663"                # Common 0603 100nF
    package: "0603"
    category: passive
    quantity: 11                  # Count from FSD
    option_group: null
    specs:
      capacitance: "100nF"
      voltage: "16V+"
      dielectric: "X7R"

  # ... continue for all parts

# === Option Groups Summary ===
# List all option groups for Step 2 decision-making
option_groups:
  ldo_3v3:
    description: "3.3V voltage regulator"
    candidates: [ldo_ams1117, ldo_me6211]
    decision_factors:
      - "Current requirements (check power budget)"
      - "Battery life (quiescent current)"
      - "Cost and availability"

  encoder:
    description: "Rotary encoder type"
    candidates: [encoder_smd, encoder_th]
    decision_factors:
      - "Assembly method (full SMD vs manual)"
      - "Cost"
      - "Mechanical feel preference"

# === Design Options ===
# Design choices identified that need user decision
# Format: question, context, choices with pros/cons, recommendation
design_options:
  <option_id>:
    question: "<What is being decided?>"
    context: "<Why this matters for the design>"
    choices:
      - value: "<choice_value>"
        description: "<What this choice means>"
        pros: ["<advantage1>", "<advantage2>"]
        cons: ["<disadvantage1>", "<disadvantage2>"]
        adds_parts: [<part_id1>, <part_id2>]  # References conditional_parts
    recommendation: "<recommended_value>"
    reason: "<Why this is recommended>"

# === Conditional Parts ===
# Parts only included based on design_options decisions
# These get enriched in Step 2 along with regular parts
conditional_parts:
  - id: <part_id>
    name: "<Part name>"
    function: "<What it does>"
    part_number: "<Suggested part>"
    lcsc: null  # Will be found in Step 2
    package: "<Package>"
    category: protection|connector|passive
    quantity: 1
    condition: "<option_id> == <value>"
```

---

## Categories Reference

| Category | Description | Examples |
|----------|-------------|----------|
| microcontroller | Main MCU | ESP32-S3 |
| radio | RF/radio ICs | SI4735 |
| power | Voltage regulators, chargers | LDO, TP4056 |
| audio | Amplifiers, DACs | TDA1308 |
| ui | User interface | Encoders, buttons, LEDs |
| connector | Physical connectors | USB-C, JST, audio jack |
| passive | R, C, L, crystals | Resistors, capacitors |
| protection | ESD, fuses | TVS diodes |

---

## Checklist: When to Add Alternatives

- [ ] FSD explicitly mentions alternatives ("or equivalent")
- [ ] Different packages available (SMD vs TH)
- [ ] Different power topologies possible (linear vs switching)
- [ ] Common drop-in replacements exist
- [ ] FSD gives minimum spec (implies larger/better is OK)

## Checklist: When NOT to Add Alternatives

- [ ] FSD specifies exact part number for unique functionality
- [ ] Part has no common substitutes (specialized ICs)
- [ ] Standard passive values (use what FSD says)
- [ ] Adding alternatives would require circuit changes

---

## Exit Validation Checklist

**Before proceeding to Step 2, ALL checks must pass:**

### 1. File Exists and Valid
```bash
ls -la design/work/step1_primary_parts.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step1_primary_parts.yaml'))"
```
- [ ] `step1_primary_parts.yaml` exists and is valid YAML

### 2. All FSD Parts Captured
- [ ] Every component from FSD BOM is represented
- [ ] Every IC from block diagram is included
- [ ] All connectors are listed
- [ ] All passives are counted correctly

### 3. Required Fields Present
Every part must have:
- [ ] `id` - unique identifier
- [ ] `name` - human-readable name
- [ ] `function` - what it does in the circuit
- [ ] `part_number` - from FSD or suggested
- [ ] `package` - footprint type
- [ ] `category` - component category
- [ ] `quantity` - number needed
- [ ] `option_group` - null or group name

### 4. Option Groups Valid
- [ ] Each option_group has 2+ candidates
- [ ] All candidates in a group serve the same function
- [ ] decision_factors explain trade-offs
- [ ] No part belongs to multiple option_groups

### 5. Design Options Complete
- [ ] Common protection options considered (USB ESD, battery reverse polarity)
- [ ] Each design_option has question, context, choices, recommendation
- [ ] Each choice has value, description, pros, cons, adds_parts
- [ ] Conditional parts listed for each "adds_parts" reference
- [ ] Conditional parts have valid `condition` field

### 6. No Pricing Data (That's Step 2)
```bash
grep -E "price|cost|\\\$" design/work/step1_primary_parts.yaml
```
- [ ] No pricing information in file (grep should return nothing except comments)

---

## If Validation Fails

**DO NOT proceed to Step 2!**

1. Identify which check(s) failed
2. Fix the issue in step1_primary_parts.yaml
3. Re-run ALL validation checks
4. Only proceed when ALL checks pass

```
VALIDATION LOOP: Step 1 → Validate → Fix if needed → Validate again → Step 2
```

---

## What Happens Next

Step 2 will:
1. Run automated script to fetch JLCPCB data (pricing, stock, variants) for ALL parts
2. Select best variant for each part (in stock, Basic preferred)
3. Output enriched parts list with JLCPCB details

Step 3 will:
1. Present design options to user
2. Collect decisions on optional parts
3. Output final design options for Step 4
