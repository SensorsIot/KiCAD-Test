# Step 1: Parts Extraction and Design Decisions

Read the FSD and:
1. Extract all components
2. Look up JLCPCB pricing and availability for each part
3. Present design choices as questions with pros/cons
4. Wait for user decisions
5. Document final selections in YAML and CSV
6. **STOP HERE** - Do not proceed to Step 2 until explicitly requested

---

## Process

### Part 1: Research Parts on JLCPCB

For each component, look up on JLCPCB (https://jlcpcb.com/parts):
- **LCSC code** (e.g., C12345)
- **Part type**: Basic or Extended
- **Unit price** (for qty 10-100)
- **Stock availability**

Use web search or JLCPCB parts database to get current pricing.

### Part 2: Present Design Choices

For each component or design decision where alternatives exist, present:

```
## [Component/Decision Name]

**Context:** [Why this choice matters]

**Option A: [Name]** (Recommended)
- Part: [part number]
- LCSC: [code]
- Type: Basic/Extended
- Price: $X.XX (qty 10)
- Pros: [list benefits]
- Cons: [list drawbacks]

**Option B: [Name]**
- Part: [part number]
- LCSC: [code]
- Type: Basic/Extended
- Price: $X.XX (qty 10)
- Pros: [list benefits]
- Cons: [list drawbacks]

**My recommendation:** [A or B] because [reason]

**Your choice?**
```

### Part 3: Collect Decisions and Generate Output

After user responds, create TWO output files:

#### File 1: `design/work/decisions.yaml`

```yaml
# decisions.yaml
# User decisions from Step 1 discussion
# Date: [YYYY-MM-DD]

component_choices:
  mcu: "ESP32-S3-MINI-1-N8"
  mcu_lcsc: "C2913206"
  mcu_type: "Extended"
  mcu_price: "3.50"

  ldo: "ME6211C33M5G"
  ldo_lcsc: "C82942"
  ldo_type: "Basic"
  ldo_price: "0.05"
  # ... all selected parts

design_choices:
  power_topology: "linear"
  passive_size: "0603"
  # ... all design decisions
```

#### File 2: `design/work/step1_parts.csv`

```csv
id,name,part_number,lcsc,type,price_qty10,package,category,quantity,selected,notes
mcu,Main Microcontroller,ESP32-S3-MINI-1-N8,C2913206,Extended,3.50,Module,microcontroller,1,X,WiFi/BLE dual-core
radio_ic,Radio Receiver IC,SI4735-D60-GU,C195417,Extended,2.80,SSOP-24,radio,1,X,AM/FM/SW receiver
ldo,3.3V LDO Regulator,ME6211C33M5G,C82942,Basic,0.05,SOT-23-5,power,1,X,Low quiescent current
ldo_alt,3.3V LDO Regulator,AMS1117-3.3,C6186,Basic,0.08,SOT-223,power,1,,Higher current capacity
encoder,Rotary Encoder,EC11J1524413,C370986,Extended,0.45,SMD,ui,2,X,SMD version
encoder_alt,Rotary Encoder,EC11E18244A5,C470747,Extended,0.35,TH,ui,2,,Through-hole version
# ... all parts with alternatives
```

**CSV Column Definitions:**
| Column | Description |
|--------|-------------|
| id | Unique identifier for the part |
| name | Human-readable description |
| part_number | Manufacturer part number |
| lcsc | JLCPCB/LCSC part code |
| type | Basic or Extended |
| price_qty10 | Unit price at qty 10 (USD) |
| package | Footprint/package type |
| category | microcontroller/power/radio/ui/connector/passive |
| quantity | Number needed |
| selected | X if this option was chosen, empty otherwise |
| notes | Brief note about the part |

---

## What to Present as Choices

### Always ask about:
- MCU variant (if options exist)
- Voltage regulator type (linear vs switching, specific part)
- Passive component size (0402 vs 0603 vs 0805)
- Protection level (minimal vs full ESD/overcurrent)
- Any part where FSD says "or equivalent"
- Encoder type (TH vs SMD)
- Connector variants

### Don't ask about (just use standard):
- Decoupling capacitor values (use 100nF)
- I2C pull-up values (use 4.7k)
- Standard resistor tolerances (use 1%)

### Prefer Basic Parts When Possible
- **Basic parts**: Lower assembly fee ($0.0017/joint vs $0.0173/joint for extended)
- **Extended parts**: May have minimum order quantities or setup fees
- When a Basic part meets requirements, recommend it over Extended

---

## JLCPCB Part Type Reference

| Type | Assembly Fee | Notes |
|------|--------------|-------|
| Basic | $0.0017/joint | No setup fee, preferred |
| Extended | $0.0173/joint | $3 setup fee per unique part |

**Cost example for 10 boards:**
- Basic part (8 pins): 10 boards × 8 joints × $0.0017 = $0.14
- Extended part (8 pins): 10 boards × 8 joints × $0.0173 + $3 = $4.38

---

## After Decisions

Once user has answered all questions:
1. Save `decisions.yaml`
2. Save `step1_parts.csv`
3. Display summary table of selected parts with total estimated cost
4. **STOP AND WAIT** - Do not proceed to Step 2
5. User will explicitly request Step 2 when ready

```
## Summary

| Category | Part | LCSC | Type | Price | Qty | Subtotal |
|----------|------|------|------|-------|-----|----------|
| MCU | ESP32-S3-MINI-1-N8 | C2913206 | Ext | $3.50 | 1 | $3.50 |
| Power | ME6211C33M5G | C82942 | Basic | $0.05 | 1 | $0.05 |
| ... | ... | ... | ... | ... | ... | ... |
| **Total** | | | | | | **$XX.XX** |

Basic parts: X
Extended parts: Y
Estimated assembly fee (10 boards): $Z.ZZ

Files saved:
- design/work/decisions.yaml
- design/work/step1_parts.csv

**Step 1 complete. Run Step 2 when ready to generate full parts list.**
```

---

## Exit Validation Checklist

**Before proceeding to Step 2, verify ALL of the following:**

### File Checks
- [ ] `design/work/decisions.yaml` exists and is valid YAML
- [ ] `design/work/step1_parts.csv` exists and is valid CSV

### decisions.yaml Validation
- [ ] Every component choice has: part name, lcsc code, type (Basic/Extended), price
- [ ] All LCSC codes start with "C" followed by digits (e.g., C82942)
- [ ] No TBD or placeholder values remain
- [ ] Design choices section is complete (passive_size, power_topology, etc.)

### step1_parts.csv Validation
- [ ] Every row has all required columns filled
- [ ] Exactly ONE part per category has "X" in the `selected` column
- [ ] All LCSC codes are valid format
- [ ] Prices are numeric (no currency symbols in data)

### Cross-Reference Check
- [ ] Every selected part in CSV matches a choice in decisions.yaml
- [ ] LCSC codes match between CSV and YAML

## If Validation Fails

**DO NOT proceed to Step 2!**

1. Identify which check(s) failed
2. Fix the issue in the appropriate file
3. Re-run the validation checklist
4. Only proceed when ALL checks pass

```
⚠️  VALIDATION LOOP: Step 1 → Validate → Fix if needed → Validate again → Step 2
```
