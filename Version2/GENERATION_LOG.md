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

## Step 1: Prepare Parts Data
- **Source**: `D:\Github\KiCAD-Test\jlcpcb_parts_pipeline\jlc_parts_enriched.json`
- **Contains**: 40 components with LCSC codes, KiCAD symbols, footprints, datasheets
- **Status**: COMPLETE

---

## Step 2: Create Schematic Generator Script
- **Script**: `generate_schematic.py`
- **Location**: `D:\Github\KiCAD-Test\Version2\`
- **Input**: `jlc_parts_enriched.json`
- **Output**: KiCAD 9 schematic files

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
