# Step 7: Pin Model and KiCAD Schematic Generation

Generate the pin model from final parts and connections, then produce a KiCAD 9 schematic.

## Prerequisites Check

Before starting, verify:
- [ ] `design/work/step4_final_parts.yaml` exists and is valid
- [ ] `design/work/step5_connections.yaml` exists and is valid
- [ ] `design/work/step6_validation.yaml` shows status: PASS
- [ ] All LCSC part numbers are specified (no TBD values)

If any prerequisite fails, go back and fix the previous step.

## Input Files

- `design/work/step4_final_parts.yaml` - Final parts list with LCSC codes
- `design/work/step5_connections.yaml` - All electrical connections
- `design/work/step6_validation.yaml` - Validation report

## Output Files

- `design/work/pin_model.json` - Parts with pin-to-net mappings
- `design/output/Debug.kicad_sch` - Generated KiCAD 9 schematic
- `design/output/Debug.kicad_pro` - KiCAD project file
- `design/output/sym-lib-table` - Symbol library configuration
- `design/output/fp-lib-table` - Footprint library configuration

---

## Phase 3: Pin Model Generation

### 3.1 Ensure Symbols Exist

Download any missing symbols from JLCPCB/LCSC:

```bash
cd design
python ../../../KiCAD-Generator-tools/scripts/ensure_symbols.py \
    --parts work/step4_final_parts.yaml \
    --library ../../../KiCAD-Generator-tools/libs/JLCPCB/symbol/JLCPCB.kicad_sym
```

**Expected output:**
- Reports which symbols already exist
- Downloads missing symbols via JLC2KiCadLib
- Adds new symbols to central JLCPCB.kicad_sym library

**If symbol download fails:**
1. Check LCSC part number is correct
2. Part may not have EasyEDA symbol (add to `manual_symbol_pins.yaml`)
3. Add custom symbol to `custom_library_overrides.yaml`

### 3.2 Generate Pin Model

Create pin_model.json from parts and connections:

```bash
python ../../../KiCAD-Generator-tools/scripts/generate_pin_model.py \
    --parts work/step4_final_parts.yaml \
    --connections work/step5_connections.yaml \
    --output work/pin_model.json
```

### 3.3 Validate Pin Model

```bash
python ../../../KiCAD-Generator-tools/scripts/validate_pin_model.py \
    --input work/pin_model.json
```

**Validation checks:**
- [ ] All parts have symbol references
- [ ] All pins have coordinates (no `?,?,?`)
- [ ] All nets reference valid pins
- [ ] No duplicate pin assignments
- [ ] Power pins connected to power nets
- [ ] Ground pins connected to GND net

**If validation fails:**
- `?,?,?` coordinates → Symbol not found, run ensure_symbols.py
- Missing pins → Check pin names match symbol definition
- Duplicate pins → Fix connections.yaml

---

## Phase 4: KiCAD Schematic Generation

### 4.1 Generate Schematic

```bash
python ../../../KiCAD-Generator-tools/scripts/kicad9_schematic.py \
    --pin-model work/pin_model.json \
    --output output/Debug.kicad_sch \
    --debug
```

**Options:**
- `--debug` - Generate debug.csv with pin positions
- `--no-route` - Skip wire routing (net labels only)

**Expected output:**
```
output/
├── Debug.kicad_pro         # KiCAD project file
├── Debug.kicad_sch         # Generated schematic
├── sym-lib-table           # Symbol library paths
├── fp-lib-table            # Footprint library paths
├── debug.csv               # Pin positions (debug mode)
└── libs/
    └── JLCPCB/
        ├── symbol/
        │   └── JLCPCB.kicad_sym
        └── footprint/
            └── JLCPCB.pretty/
```

### 4.2 Run ERC (Electrical Rules Check)

**Linux:**
```bash
cd output
kicad-cli sch erc --output erc_report.txt Debug.kicad_sch
cat erc_report.txt
```

**Windows:**
```cmd
set PATH=%PATH%;C:\Program Files\KiCad\9.0\bin
kicad-cli sch erc --output output\erc_report.txt output\Debug.kicad_sch
type output\erc_report.txt
```

**Expected results:**
- **0 Errors** - Design is electrically correct
- **Warnings** - Library path warnings (OK if symbols load)

### 4.3 Common ERC Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `pin_not_connected` | Unconnected pin | Add to `no_connect` in step5 or add wire |
| `pin_to_pin` | Multiple power outputs | Remove duplicate PWR_FLAG |
| `power_pin_not_driven` | No power source | Add PWR_FLAG to power net |
| `different_unit_net` | Net name mismatch | Check net naming consistency |

---

## Phase 5: Post-Generation Verification

### 5.1 Open in KiCAD

**Important:** Open the PROJECT file, not the schematic:
```
output/Debug.kicad_pro
```

This ensures library tables load correctly.

### 5.2 Visual Inspection Checklist

- [ ] All symbols visible (no missing library warnings)
- [ ] Net labels on all pins
- [ ] Power symbols present (+3V3, GND, VBAT, etc.)
- [ ] Components grouped logically
- [ ] No overlapping components
- [ ] Decoupling capacitors near IC power pins

### 5.3 Update from Symbol Libraries (Optional)

In KiCAD:
1. **Tools > Update Schematic from Symbol Libraries**
2. This populates the `lib_symbols` section for portability

### 5.4 Final ERC in KiCAD GUI

1. **Inspect > Electrical Rules Checker**
2. Run ERC
3. Review and resolve any remaining issues

---

## Output Format

Write to `design/work/step7_generation.yaml`:

```yaml
# step7_generation.yaml
# KiCAD Schematic Generation Report
# Date: [YYYY-MM-DD]

pin_model:
  status: GENERATED  # GENERATED | FAILED
  file: "work/pin_model.json"
  total_parts: 38
  total_pins: 256
  symbols_downloaded: 3
  symbols_existing: 35

schematic:
  status: GENERATED  # GENERATED | FAILED
  file: "output/Debug.kicad_sch"
  project: "output/Debug.kicad_pro"
  format: "KiCAD 9"

erc:
  status: PASS  # PASS | PASS_WITH_WARNINGS | FAIL
  errors: 0
  warnings: 2
  report: "output/erc_report.txt"

warnings:
  - type: "library_path"
    message: "Library path is relative"
    severity: info

errors: []

files_generated:
  - "work/pin_model.json"
  - "output/Debug.kicad_pro"
  - "output/Debug.kicad_sch"
  - "output/sym-lib-table"
  - "output/fp-lib-table"
  - "output/debug.csv"
```

---

## Troubleshooting

### Symbol Not Found (?,?,? coordinates)

1. Check LCSC code in step4_final_parts.yaml
2. Run `ensure_symbols.py` again
3. If part has no EasyEDA symbol:
   - Add to `manual_symbol_pins.yaml` with pin definitions
   - Or add custom symbol to `custom_library_overrides.yaml`

### Pins Not Connecting in KiCAD

KiCAD requires exact coordinate match between wire endpoint and pin position:
- Wire endpoint must exactly match pin position
- Small circle at pin = unconnected
- Check debug.csv for actual pin positions

### Library Not Loading

1. Open `Debug.kicad_pro`, NOT `Debug.kicad_sch`
2. Check `sym-lib-table` exists in output folder
3. Verify library path in sym-lib-table is correct

---

## Exit Validation

Before marking Step 7 complete:

- [ ] `pin_model.json` generated successfully
- [ ] `Debug.kicad_sch` generated successfully
- [ ] ERC reports 0 errors
- [ ] Schematic opens correctly in KiCAD
- [ ] All symbols load without errors
- [ ] `step7_generation.yaml` written

If any check fails, fix the issue and regenerate.
