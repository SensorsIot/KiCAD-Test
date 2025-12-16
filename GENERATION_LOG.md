# KiCAD 9 Schematic Generation Log

## Project: ESP32-S3 Portable Radio Receiver (Version2)

### Overview
Programmatic generation of KiCAD 9 schematics from `jlc_parts_enriched.json`.

---

## Quick Start (For Future Projects)

```bash
# 1. Download JLCPCB symbols/footprints (only downloads missing parts)
python download_jlcpcb_libs.py --register

# 2. Generate schematics from parts JSON
python generate_schematic_v2.py

# 3. Open in KiCAD 9 and run:
#    Tools > Update Schematic from Symbol Libraries...
```

### Files Created
| File | Purpose |
|------|---------|
| `download_jlcpcb_libs.py` | Downloads symbols/footprints from JLCPCB using LCSC codes |
| `generate_schematic_v2.py` | Generates .kicad_sch files from jlc_parts_enriched.json |
| `sym-lib-table` | Project-specific symbol library reference |
| `fp-lib-table` | Project-specific footprint library reference |

### Library Location
- **Symbols**: `%USERPROFILE%\Documents\KiCad\JLCPCB\symbol\JLCPCB.kicad_sym`
- **Footprints**: `%USERPROFILE%\Documents\KiCad\JLCPCB\JLCPCB\`
- **3D Models**: `%USERPROFILE%\Documents\KiCad\JLCPCB\JLCPCB\packages3d\`
- **Index**: `%USERPROFILE%\Documents\KiCad\JLCPCB\lcsc_index.json`

---

## Step 1: Generate Parts/Connections from FSD
- **Source**: `D:\Github\KiCAD-Test\FSD_ESP32_Radio_Receiver.md`
- **Outputs**: `parts.yaml` (semantic components), `connections.yaml` (semantic nets)
- **Status**: COMPLETE

---

## Step 2: Enrich Parts and Select Options
- **Input**: `parts.yaml`
- **Script**: `enrich_parts.py`
- **Output**: `parts_options.csv` (multiple JLC options per part; reviewer marks `selected='X'`)
- **Status**: COMPLETE

### Schematic Structure (2 sheets)
| Sheet | File | Components |
|-------|------|------------|
| Root | `Version2.kicad_sch` | Hierarchy only (links to sub-sheets) |
| Radio | `radio.kicad_sch` | U4 (SI4735), Y1 (crystal), J3 (audio jack), C12-C16 (SI4735 caps), C13-C14 (crystal caps) |
| Main | `main.kicad_sch` | Everything else: ESP32, power, LEDs, connectors, UI |

### Component Assignment
**Radio Sheet (radio.kicad_sch)**:
- U4: SI4735-D60-GU (radio IC)
- Y1: 32.768kHz crystal
- J3: 3.5mm audio jack
- C12: SI4735 VDD bypass
- C13, C14: Crystal load caps (22pF)
- C15: SI4735 VA bypass
- C16: SI4735 VD bypass
- R7, R8: Audio output resistors (100R)

**Main Sheet (main.kicad_sch)**:
- U1: ESP32-S3-MINI-1-N8
- U2: TP4056 (battery charger)
- U3: AMS1117-3.3 (LDO)
- D1-D3: WS2812B LEDs
- J1: USB-C connector
- J2: Battery connector (JST-PH)
- J4: OLED header
- SW1: Reset button
- ENC1, ENC2: Rotary encoders
- C1-C11, C17: Capacitors (power, decoupling)
- R1-R6: Resistors (CC, pullups)

---

## Step 3: Run Generator Script
```bash
python generate_schematic.py
```

**Output files**:
- `Version2.kicad_sch` (root with hierarchy)
- `radio.kicad_sch` (radio section)
- `main.kicad_sch` (main section)

---

## Step 4: Open in KiCAD 9
1. Open `Version2.kicad_pro`
2. Verify symbols loaded correctly
3. Check all properties (LCSC, footprint, datasheet)

---

## Step 5: Add Net Connections (Phase 2 - Later)
Options:
- Manual wiring in KiCAD
- Script-based net label generation from DESIGN_SPEC.md

---

## Files Reference

| File | Purpose |
|------|---------|
| `jlc_parts_enriched.json` | Parts data with KiCAD mappings |
| `generate_schematic.py` | Python generator script |
| `Version2.kicad_pro` | KiCAD project file |
| `Version2.kicad_sch` | Root schematic (hierarchy) |
| `radio.kicad_sch` | Radio sub-sheet |
| `main.kicad_sch` | Main sub-sheet |
| `GENERATION_LOG.md` | This file |

---

## Execution Log

| Step | Status | Notes |
|------|--------|-------|
| 1. Parts data prepared | COMPLETE | 40 parts in JSON |
| 2. Create generator script | COMPLETE | generate_schematic.py created |
| 3. Run generator | COMPLETE | 3 files generated |
| 4. Verify in KiCAD | PENDING | Open Version2.kicad_pro |
| 5. Add connections | PENDING | Phase 2 |

---

## Generation Results (2025-12-16)

### Files Generated

| File | Size | Components |
|------|------|------------|
| `Version2.kicad_sch` | 1.6 KB | Root with hierarchy (2 sheet refs) |
| `main.kicad_sch` | 26.5 KB | 30 components |
| `radio.kicad_sch` | 9.6 KB | 10 components |

### Component Distribution

**Radio Sheet (10 parts)**:
- U4: SI4735-D60-GU
- Y1: 32.768kHz crystal
- J3: Audio jack
- C12-C16: SI4735 bypass/crystal caps
- R7, R8: Audio resistors

**Main Sheet (30 parts)**:
- U1: ESP32-S3-MINI-1-N8
- U2: TP4056
- U3: AMS1117-3.3
- D1-D3: WS2812B LEDs
- J1, J2, J4: Connectors
- SW1, ENC1, ENC2: UI
- C1-C11, C17: Capacitors
- R1-R6: Resistors

### Properties Set Per Component
- Reference (designator)
- Value
- Footprint (KiCAD library path)
- Datasheet (URL)
- LCSC (part number)

---

## Phase 2: Download JLCPCB Symbols/Footprints

### Problem
Generated schematics show `??` because symbol libraries aren't installed.

### Solution
Use **JLC2KiCadLib** to download symbols, footprints, and 3D models directly from JLCPCB/EasyEDA using LCSC part numbers.

### Steps

1. **Install JLC2KiCadLib**
   ```bash
   pip install JLC2KiCadLib
   ```
   Status: COMPLETE

2. **Create download script** (`download_jlcpcb_libs.py`)
   - Reads `jlc_parts_enriched.json`
   - Extracts unique LCSC part numbers
   - Downloads symbols/footprints for each part
   - Creates local KiCAD library in `Version2/libs/`

3. **Run download script**
   ```bash
   python download_jlcpcb_libs.py
   ```

4. **Update schematic generator**
   - Point to local library instead of standard KiCAD libs
   - Regenerate schematics

5. **Configure KiCAD**
   - Add `Version2/libs/` to symbol/footprint library paths

### Output Files
```
%USERPROFILE%\Documents\KiCad\JLCPCB\
├── symbol/
│   └── JLCPCB.kicad_sym      (20 symbols, 61 KB)
├── JLCPCB/                   (14 footprints)
│   └── packages3d/           (14 STEP models)
└── lcsc_index.json           (tracks downloaded parts)
```

### Phase 2 Results
- **20/21 parts downloaded** (C195417/SI4735 not available on EasyEDA)
- Libraries registered in KiCAD 9.0 global library tables
- Schematics regenerated with `JLCPCB:symbol_name` references

### Regenerated Schematics (v2)
- `Version2.kicad_sch` - Root with hierarchy
- `main.kicad_sch` - 30 components using JLCPCB symbols
- `radio.kicad_sch` - 10 components (U4/SI4735 uses fallback)

### Manual Fix Required
- **U4 (SI4735)**: C195417 not on EasyEDA, uses `Interface_Expansion:SI4735-D60-GU`
- Install Espressif symbol libraries or manually create SI4735 symbol

---

## Troubleshooting: Symbol Resolution

### Problem
Generated schematics showed "??" for all symbols even though library was registered.

### Root Cause
1. **Library format version**: JLC2KiCadLib generates KiCAD 6 format (`version 20210201`)
   - KiCAD 9 expects `version 20241209`
2. **Property format**: Old format uses `(property "X" "Y" (id 0) ...)`
   - KiCAD 9 expects `(property "X" "Y" ...)` without `(id X)`
3. **Empty lib_symbols**: Generator created schematics with empty `(lib_symbols)` section
   - KiCAD 9 requires symbol definitions embedded in the schematic file

### Solution Applied
1. Updated library header to KiCAD 9 format:
   ```python
   old: (kicad_symbol_lib (version 20210201) (generator TousstNicolas/JLC2KiCad_lib)
   new: (kicad_symbol_lib
           (version 20241209)
           (generator "kicad_symbol_editor")
           (generator_version "9.0")
   ```

2. Removed `(id X)` from all property definitions:
   ```python
   content = re.sub(r'\(id \d+\) ', '', content)
   ```

3. Created project-specific library tables:
   - `Version2/sym-lib-table` - points to JLCPCB symbol library
   - `Version2/fp-lib-table` - points to JLCPCB footprint library

4. **Required manual step in KiCAD:**
   - **Tools → Update Schematic from Symbol Libraries...**
   - This populates the `lib_symbols` section in the schematic files
   - Files grow significantly (main.kicad_sch: 26KB → 123KB)

### Future Improvement
The schematic generator could embed symbol definitions directly in the `lib_symbols` section
to avoid the manual update step. This would require parsing the JLCPCB.kicad_sym file and
including relevant symbols in the generated schematic.

---

## Phase 2: Net Labels on All Pins

### Goal
Add unique net labels to every pin on every component. This enables:
1. Visual identification of all pins
2. Easy connection by renaming labels (same name = same net)
3. Foundation for programmatic connection assignment

### Implementation

#### Step 1: Generate Parts with Pin Data
- **Script**: `parts_with_pins.py`
- **Input**: `symbol_pins.json` (parsed from JLCPCB.kicad_sym)
- **Output**: `parts_with_netlabels.json`
- **Format**: Each pin gets unique label `{designator}_{pin_number}` (e.g., `U1_1`, `R3_2`)

#### Step 2: Parse Symbol Library for Pin Positions
- **Script**: `generate_schematic_with_labels.py`
- **Function**: `parse_symbol_pins()`
- Extracts from JLCPCB.kicad_sym:
  - Pin number and name
  - Pin position (x, y relative to symbol origin)
  - Pin rotation (direction pin line points)

#### Step 3: Calculate Label Positions
- **Function**: `get_label_position(pin_x, pin_y, pin_rotation)`
- Returns: `(x_offset, y_offset, label_rotation, justify)`

**Pin rotation mapping** (direction pin LINE points toward symbol body):
| Pin Rotation | Pin Position | Label Offset | Label Rot | Justify |
|--------------|--------------|--------------|-----------|---------|
| 0° | LEFT | 2mm left | 180° | right |
| 180° | RIGHT | 2mm right | 0° | left |
| 90° | BOTTOM | 2mm down | 270° | right |
| 270° | TOP | 2mm up | 270° | left |

**Y-axis inversion**: Symbol library uses Y+ = up, schematic uses Y+ = down.
Label Y position = `symbol_y - pin_y + y_offset`

#### Step 4: Generate Schematic
- **Script**: `generate_schematic_with_labels.py`
- **Output**: `radio_with_netlabels.kicad_sch`
- **Result**: 40 components, 243 net labels

### Files Created

| File | Purpose |
|------|---------|
| `parts_with_pins.py` | Generates parts list with unique pin labels |
| `parts_with_netlabels.json` | 40 parts, 243 pins with unique labels |
| `symbol_pins.json` | Pin data for 20 JLCPCB symbols |
| `generate_schematic_with_labels.py` | Main generator with label positioning |
| `radio_with_netlabels.kicad_sch` | Output schematic with all labels |

### Usage

```bash
# Generate schematic with net labels on all pins
python generate_schematic_with_labels.py

# Open in KiCAD
# 1. File > Open > radio_with_netlabels.kicad_sch
# 2. Tools > Update Schematic from Symbol Libraries
```

### Next Step: Phase B - Apply Connections
To connect pins, rename labels to the same net name:
- `U1_3` and `U3_2` both become `+3V3` → connected
- `connections.json` contains all net definitions from DESIGN_SPEC.md
- Script will rename labels based on connection data

---

## Phase B: Complete LLM→Schematic Workflow

### Overview
End-to-end workflow from FSD (Functional Specification Document) to KiCAD schematic with net connections. Uses LLM to extract parts and connections, with one human review step for part selection.

### Source Document
`D:\Github\KiCAD-Test\FSD_ESP32_Radio_Receiver.md` (662 lines)

### Workflow Steps

| Step | Input | Output | Tool | Human? |
|------|-------|--------|------|--------|
| 1 | FSD.md | `parts.yaml`, `connections.yaml` | **LLM** | No |
| 2 | `parts.yaml` | `parts_options.csv` | `enrich_parts.py` | No |
| 3 | `parts_options.csv` | `parts_options.csv` (edited) | Engineer review | **YES** |
| 4 | `parts_options.csv` + `parts.yaml` | `parts_with_designators.json` | `assign_designators.py` | No |
| 5 | LCSC codes | JLCPCB library | `download_jlcpcb_libs.py` | No |
| 6 | JLCPCB.kicad_sym | `symbol_pins.json` | `parse_library_pins.py` | No |
| 7 | `connections.yaml` + designators + pins | `parts_with_netlabels.json` | `map_connections.py` | No |
| 8 | All above | `.kicad_sch` files | `generate_schematic_with_labels.py` | No |

**Single human touchpoint: Step 3 (part selection)**

---

### Step 1: LLM Generates Parts and Connections

**Input**: FSD document (markdown)

**Output**: Two YAML files

**parts.yaml** (semantic names, no designators):
```yaml
components:
  - name: MCU
    part: ESP32-S3-MINI-1-N8
    prefix: U

  - name: Battery_Charger
    part: TP4056
    prefix: U

  - name: R_CC
    value: 5.1k
    package: 0603
    quantity: 2
    prefix: R

  - name: R_I2C_SDA
    value: 4.7k
    package: 0603
    quantity: 1
    prefix: R
```

**connections.yaml** (semantic references):
```yaml
nets:
  GND:
    - MCU.GND
    - Battery_Charger.GND
    - LDO.GND
    - R_CC.2

  SDA:
    - MCU.GPIO4
    - Radio_IC.SDIO
    - R_I2C_SDA.2
    - OLED_Header.3

  +3V3:
    - LDO.OUT
    - MCU.3V3
    - R_I2C_SDA.1
    - R_I2C_SCL.1
```

---

### Step 2: Enrich with JLCPCB Options

**Script**: `enrich_parts.py`

**Input**: `parts.yaml`

**Output**: `parts_options.csv`

```csv
name,query,option,lcsc,mpn,package,stock,price,is_basic,is_preferred,selected
MCU,ESP32-S3-MINI-1-N8,1,C2913206,ESP32-S3-MINI-1-N8,SMD,50000,2.50,false,false,
MCU,ESP32-S3-MINI-1-N8,2,C3567892,ESP32-S3-MINI-1-N4,SMD,30000,2.00,false,false,
Battery_Charger,TP4056,1,C16581,TP4056-42-ESOP8,ESOP-8,65000,0.16,false,true,
Battery_Charger,TP4056,2,C725790,TP4056,SOP-8,400000,0.06,false,false,
R_CC,5.1k 0603,1,C23186,0603WAF5101T5E,0603,500000,0.002,true,false,
R_CC,5.1k 0603,2,C22787,RC0603FR-075K1L,0603,300000,0.003,true,false,
```

Each part shows multiple JLCPCB options with:
- Stock availability
- Unit price
- Basic/preferred status (affects assembly fee)

---

### Step 3: Engineer Reviews and Selects Parts

**Human action**: Open CSV in Excel/LibreOffice, mark selections

1. Review options for each component
2. Consider: stock, price, basic vs extended (assembly fee)
3. Put `X` in `selected` column for chosen option
4. Save file

```csv
name,query,option,lcsc,mpn,package,stock,price,is_basic,is_preferred,selected
MCU,ESP32-S3-MINI-1-N8,1,C2913206,ESP32-S3-MINI-1-N8,SMD,50000,2.50,false,false,X
Battery_Charger,TP4056,1,C16581,TP4056-42-ESOP8,ESOP-8,65000,0.16,false,true,X
R_CC,5.1k 0603,1,C23186,0603WAF5101T5E,0603,500000,0.002,true,false,X
```

---

### Step 4: Assign Designators

**Script**: `assign_designators.py`

**Input**: `parts_options.csv` (with selections), `parts.yaml` (for quantity)

**Output**: `parts_with_designators.json`

```json
{
  "MCU": {
    "designators": ["U1"],
    "lcsc": "C2913206",
    "mpn": "ESP32-S3-MINI-1-N8"
  },
  "Battery_Charger": {
    "designators": ["U2"],
    "lcsc": "C16581",
    "mpn": "TP4056-42-ESOP8"
  },
  "R_CC": {
    "designators": ["R1", "R2"],
    "lcsc": "C23186",
    "mpn": "0603WAF5101T5E"
  }
}
```

Automatic assignment:
- Groups by prefix (U, R, C, D, J, etc.)
- Assigns sequential numbers (U1, U2, U3...)
- Handles quantity (R_CC qty=2 → R1, R2)

---

### Step 5-6: Download Symbols and Parse Pins

**Existing scripts** (no changes needed):
- `download_jlcpcb_libs.py` - Downloads from EasyEDA using LCSC codes
- `parse_library_pins.py` - Extracts pin name/number from symbols

---

### Step 7: Map Semantic Connections to Pin Labels

**Script**: `map_connections.py` (NEW)

**Input**:
- `connections.yaml` (semantic: `MCU.GPIO4`)
- `parts_with_designators.json` (MCU → U1)
- `symbol_pins.json` (GPIO4 → pin 6)

**Logic**:
```
connections.yaml says: SDA: [MCU.GPIO4, Radio_IC.SDIO, R_I2C_SDA.2]

Lookup chain:
  MCU → U1 (from designator assignment)
  GPIO4 → pin 6 (from symbol_pins.json, pin name "IO4")

Result: SDA net connects: U1_6, U4_7, R5_2
```

**Output**: `parts_with_netlabels.json`
```json
{
  "U1": {
    "symbol": "ESP32-S3-MINI-1-N8",
    "pins": [
      {"number": "1", "name": "GND", "net_label": "GND"},
      {"number": "6", "name": "IO4", "net_label": "SDA"},
      {"number": "45", "name": "IO19", "net_label": "U1_45"}
    ]
  }
}
```

- Connected pins get real net names: `"net_label": "GND"`, `"net_label": "SDA"`
- Unconnected pins keep unique IDs: `"net_label": "U1_45"` (for future manual connection)

---

### Step 8: Generate Schematic

**Script**: `generate_schematic_with_labels.py` (exists, minor modifications)

**Input**: `parts_with_netlabels.json`

**Output**: `.kicad_sch` files with:
- All components placed on grid
- Net labels on every pin
- Connected pins share same label name
- Unconnected pins have unique identifier labels

---

### Workflow Diagram

```
┌─────────────────┐
│   FSD.md        │
│  (662 lines)    │
└────────┬────────┘
         │ LLM
         ▼
┌─────────────────┐     ┌─────────────────┐
│  parts.yaml     │     │ connections.yaml│
│  (semantic)     │     │  (semantic)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       │
┌─────────────────┐              │
│parts_options.csv│              │
│ (JLCPCB search) │              │
└────────┬────────┘              │
         │                       │
         ▼  ◄── ENGINEER         │
┌─────────────────┐    REVIEWS   │
│parts_options.csv│              │
│  (selected)     │              │
└────────┬────────┘              │
         │                       │
         ▼                       │
┌─────────────────┐              │
│parts_with_      │              │
│designators.json │              │
│ (U1, R1, etc.)  │              │
└────────┬────────┘              │
         │                       │
         ▼                       ▼
┌─────────────────────────────────────┐
│         map_connections.py          │
│  MCU.GPIO4 → U1_6 → net "SDA"       │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│      parts_with_netlabels.json      │
│  (designators + net names on pins)  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   generate_schematic_with_labels.py │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         .kicad_sch files            │
│  (components + labeled connections) │
└─────────────────────────────────────┘
```

---

### Key Design Decisions

1. **Semantic names in LLM output**: LLM uses meaningful names (MCU, Battery_Charger, R_CC) not designators (U1, U2, R1). This keeps LLM reasoning at the logical level.

2. **Late designator assignment**: Designators assigned AFTER part selection, not by LLM. This allows proper sequential numbering.

3. **CSV for human review**: Spreadsheet-friendly format for engineer to compare options, sort by price/stock, make informed decisions.

4. **Single human touchpoint**: All automation except part selection. Engineer expertise applied where it matters most.

5. **Unconnected pins labeled**: Pins not in connections.yaml get unique IDs (U1_45) instead of being unlabeled. Enables future manual connections in KiCAD.

---

## Appendix: JLCPCB Parts Enrichment Pipeline

### Overview
Reproducible workflow from **design intent** to **machine-readable, assembly-ready parts file**.

### Files (in `jlcpcb_parts_pipeline/`)
| File | Purpose |
|------|---------|
| `parts_requirements.yaml` | Shopping list from LLM (MPNs/specs per designator) |
| `jlc_parts_enriched.schema.json` | JSON Schema for output validation |
| `enrich_parts.py` | Queries JLCPCB, writes enriched JSON |

### Data Sources
1. **Official JLCPCB Components API** (production) - Requires developer portal approval
2. **jlcsearch.tscircuit.com** (prototyping) - Public JSON endpoints, no auth required

### Usage
```bash
pip install requests pyyaml
python enrich_parts.py --in parts_requirements.yaml --out jlc_parts_enriched.json
```

### Pipeline Flow
1. LLM reads FSD → generates `parts_requirements.yaml`
2. Python enriches with LCSC codes, stock, prices, datasheets
3. Downstream tooling uses `selection.lcsc` for BOM/CPL generation

---

## Session Log: 2025-12-16

### Completed Steps

| Step | Script | Status | Notes |
|------|--------|--------|-------|
| 1 | `enrich_parts.py` | ✅ COMPLETE | Switched to official JLCPCB API, added logging |
| 2 | Human review | ✅ COMPLETE | `parts_options.csv` reviewed and selections marked |
| 3 | `assign_designators.py` | ✅ COMPLETE | 33 parts → 45 components with designators |
| 4 | `download_jlcpcb_libs.py` | ✅ COMPLETE | 22 unique LCSC parts, 16 footprints, 16 3D models |
| 5 | `parse_library_pins.py` | ✅ COMPLETE | 22 symbols, 202 pins with LCSC codes |
| 6 | `map_connections.py` | ✅ COMPLETE | 259 pins mapped, 29 nets, 128 unconnected |
| 7 | `generate_schematic.py` | ✅ COMPLETE | 45 components, 259 net labels |

### Part Substitutions
| Original | Issue | Replacement | LCSC |
|----------|-------|-------------|------|
| TS-1102S (C9900128854) | Not on EasyEDA | TS-1187A-B-A-B | C318884 |
| PJ-327A (C19712376) | Not on EasyEDA | PJ-3537S-SMT | C2689709 |

### Changes Made
- **enrich_parts.py**: Migrated from jlcsearch (tscircuit) to official JLCPCB BOM API
- **download_jlcpcb_libs.py**: Added Linux/macOS support, auto-detect JLC2KiCadLib location
- **assign_designators.py**: Added validation for duplicates, auto-select first option if none marked
- **parse_library_pins.py**: Added Linux/macOS support, extract LCSC codes from symbols
- **map_connections.py**: Removed hardcoded product mappings, derive LCSC→symbol from symbol_pins.json
- **generate_schematic.py**: Added Linux/macOS support

### Output Files
- `RadioReceiver.kicad_pro` - KiCAD 9 project
- `RadioReceiver.kicad_sch` - Schematic with 45 components, net labels on all pins
- `RadioReceiver.kicad_pcb` - Empty PCB (placeholder)
- `sym-lib-table` / `fp-lib-table` - Library references
