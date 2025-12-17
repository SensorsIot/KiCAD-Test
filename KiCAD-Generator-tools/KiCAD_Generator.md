# KiCAD Schematic Generator - Complete Guide

This guide documents the complete pipeline for generating KiCAD schematics from a Functional Specification Document (FSD).

## Prerequisites

### Software Requirements
- **Python 3.12+** - `C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe`
- **KiCad 9.0+** - Includes `kicad-cli` for ERC validation
- **Git** (optional, for version control)

### KiCad CLI

KiCad CLI (`kicad-cli`) is included with KiCad 7+ installations. Used for running ERC checks.

**Windows:** Add to PATH or use full path:
```cmd
set PATH=%PATH%;C:\Program Files\KiCad\9.0\bin
kicad-cli sch erc --help
```

**Linux:** Install KiCad from package manager:
```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:kicad/kicad-9.0-releases
sudo apt update
sudo apt install kicad

# Verify installation
kicad-cli --version
```

**macOS:**
```bash
brew install kicad
```

### Python Packages
```bash
pip install pyyaml JLC2KiCadLib
```

## Directory Structure

```
KiCAD-Generator-tools/              # Shared tools and libraries
├── KiCAD_Generator.md              # This file
├── libs/
│   └── JLCPCB/
│       └── symbol/
│           └── JLCPCB.kicad_sym    # CENTRAL symbol library (shared)
├── prompts/
│   └── step1-6.md                  # LLM prompts with validation
├── scripts/
│   ├── ensure_symbols.py           # Downloads missing symbols
│   ├── run_pipeline.py             # Orchestrates pipeline
│   ├── kicad9_schematic.py         # Main generator
│   └── validate_step*.py           # Validators
│
RadioReceiverV2/                    # Project directory
├── design/
│   ├── input/
│   │   └── FSD_*.md                # Functional Specification Document
│   ├── work/
│   │   ├── decisions.yaml          # User selections from Step 1
│   │   ├── step1_parts.csv         # Parts with JLCPCB pricing
│   │   ├── step2_parts_complete.yaml
│   │   ├── step3_connections.yaml
│   │   └── pin_model.json          # Generated pin model
│   └── output/
│       ├── Debug.kicad_pro         # KiCad project
│       ├── Debug.kicad_sch         # Generated schematic
│       └── sym-lib-table           # Points to central library
```

## Central Symbol Library

All projects share a central JLCPCB symbol library:
```
KiCAD-Generator-tools/libs/JLCPCB/symbol/JLCPCB.kicad_sym
```

The `ensure_symbols.py` script automatically:
1. Checks which symbols are needed for a project
2. Downloads missing symbols using JLC2KiCadLib
3. Adds them to the central library

This ensures symbols are downloaded once and reused across all projects.

---

## Pipeline Overview

```
FSD.md
   ↓ [Step 1] LLM extracts parts, presents options with JLCPCB pricing
decisions.yaml + step1_parts.csv
   ↓ [Step 2] LLM generates complete parts list (MUST match decisions.yaml!)
step2_parts_complete.yaml → ensure_symbols.py downloads missing symbols
   ↓ [Step 3] LLM generates connections
step3_connections.yaml
   ↓ [Python] Generate pin model + schematic
pin_model.json → Debug.kicad_sch
   ↓ [KiCad] Run ERC
ERC Report (0 errors expected)
```

## Validation Loop

**Each step has prerequisite checks and exit validation:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step N                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Prerequisites Check                                          │   │
│  │ □ Previous step outputs exist                                │   │
│  │ □ Required files valid                                       │   │
│  │ → If FAIL: Go back to previous step                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│                     [Step Content]                                  │
│                              ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Exit Validation                                              │   │
│  │ □ Output files exist and valid                               │   │
│  │ □ Content matches requirements                               │   │
│  │ □ Cross-references correct                                   │   │
│  │ → If FAIL: Fix and loop back                                 │   │
│  │ → If PASS: Proceed to Step N+1                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

Step 1 ──► Step 2 ──► Step 3 ──► Step 4 ──► Step 5 ──► Step 6 ──► Schematic
   ▲          ▲          ▲          ▲          ▲          ▲
   └──────────┴──────────┴──────────┴──────────┴──────────┘
                    Loop back if validation fails
```

**This prevents:**
- Proceeding with missing files
- Using wrong parts (mismatch with decisions.yaml)
- Missing symbols causing ?,?,? coordinates
- Invalid connections or pin references

---

## Phase 1: LLM Design Steps (1-6)

### Step 1: Extract Primary Parts

**Input:** `design/input/FSD_*.md`
**Output:** `design/work/step1_primary_parts.yaml`
**Prompt:** `design/prompts/step1.md`

```bash
# Validate output
python design/scripts/validate_step1.py
```

### Step 2: Extend with Supporting Parts

**Input:** `design/work/step1_primary_parts.yaml`
**Output:** `design/work/step2_parts_extended.yaml`
**Prompt:** `design/prompts/step2.md`

```bash
python design/scripts/validate_step2.py
```

### Step 3: Design Options

**Input:** `design/work/step2_parts_extended.yaml`
**Output:** `design/work/step3_design_options.yaml`
**Prompt:** `design/prompts/step3.md`

**⚠️ STOP HERE** - Create `design/work/decisions.yaml`:
```yaml
decisions:
  esp32_variant: "ESP32-S3-MINI-1-N8"
  power_topology: "linear_3v3"
  # ... add decisions based on step3 questions
```

### Step 4: Apply Decisions

**Input:** `step3_design_options.yaml`, `decisions.yaml`
**Output:** `design/work/step4_final_parts.yaml`
**Prompt:** `design/prompts/step4.md`

```bash
python design/scripts/validate_step4.py
```

### Step 5: Generate Connections

**Input:** `design/work/step4_final_parts.yaml`
**Output:** `design/work/step5_connections.yaml`
**Prompt:** `design/prompts/step5.md`

```bash
python design/scripts/validate_step5.py
```

### Step 6: Validation

**Input:** All previous outputs
**Output:** `design/work/step6_validation.yaml`
**Prompt:** `design/prompts/step6.md`

```bash
python design/scripts/summarize_progress.py
```

---

## Phase 2: Pin Model Generation

Generate `pin_model.json` from step4 (parts) and step5 (connections):

```bash
cd design
python scripts/generate_pin_model.py
```

Validate the pin model:
```bash
python scripts/validate_pin_model.py
```

**Output:** `design/work/pin_model.json`

---

## Phase 3: KiCad Schematic Generation

### Generate Schematic

```bash
cd design
python scripts/kicad9_schematic.py --debug
```

**Outputs:**
- `design/output/Debug.kicad_sch` - Schematic with all parts and net labels
- `design/output/Debug.kicad_pro` - KiCad project file
- `design/output/debug.csv` - Pin positions for verification
- `design/output/sym-lib-table` - Symbol library configuration
- `design/output/fp-lib-table` - Footprint library configuration
- `design/output/libs/JLCPCB/` - Downloaded symbol/footprint libraries

### Run ERC (Electrical Rules Check)

**Windows:**
```cmd
cd design
run_erc.bat
```

Or manually:
```cmd
set PATH=%PATH%;C:\Program Files\KiCad\9.0\bin
kicad-cli sch erc --output output\erc_report.txt output\Debug.kicad_sch
type output\erc_report.txt
```

**Linux:**
```bash
cd design/output
kicad-cli sch erc --output erc_report.txt Debug.kicad_sch
cat erc_report.txt
```

### Open in KiCad

**Important:** Open the PROJECT file, not the schematic directly:
```
output/Debug.kicad_pro
```

This ensures KiCad loads the library tables correctly.

---

## Phase 4: Post-Generation Steps

### In KiCad GUI

1. Open `Debug.kicad_pro`
2. Run **Tools > Update Schematic from Symbol Libraries** (optional)
3. Run **Inspect > Electrical Rules Checker**
4. Review and fix any remaining issues

### Expected ERC Results

- **0 Errors** - All electrical issues resolved
- **Warnings** - Library configuration warnings (safe to ignore if libraries load correctly)

---

## Batch Files (Windows)

### generate_and_erc.bat
Regenerates schematic and runs ERC:
```cmd
@echo off
set PYTHON=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe
set KICAD_BIN=C:\Program Files\KiCad\9.0\bin
set PATH=%PATH%;%KICAD_BIN%

echo Generating schematic...
"%PYTHON%" scripts\kicad9_schematic.py --debug

echo Running ERC...
kicad-cli sch erc --output output\erc_report.txt output\Debug.kicad_sch
type output\erc_report.txt
pause
```

### run_erc.bat
Runs ERC on existing schematic:
```cmd
@echo off
set KICAD_BIN=C:\Program Files\KiCad\9.0\bin
set PATH=%PATH%;%KICAD_BIN%

copy /Y output\Debug.kicad_sch %TEMP%\Debug.kicad_sch >nul
kicad-cli sch erc --output output\erc_report.txt %TEMP%\Debug.kicad_sch
type output\erc_report.txt
pause
```

---

## Troubleshooting

### SMB Caching (Network Drives)

If using a network drive (e.g., `Y:\`), disable Windows SMB caching:
```cmd
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" /v DirectoryCacheLifetime /t REG_DWORD /d 0 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" /v FileNotFoundCacheLifetime /t REG_DWORD /d 0 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" /v FileInfoCacheLifetime /t REG_DWORD /d 0 /f
net stop workstation /y && net start workstation
```

### Library Not Found Warnings

If ERC shows "symbol/footprint library not found":
1. Make sure you open `Debug.kicad_pro`, NOT `Debug.kicad_sch`
2. Check `sym-lib-table` and `fp-lib-table` exist in output folder
3. Verify `libs/JLCPCB/` folder contains the symbol/footprint files

### ERC Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `pin_not_connected` | Unconnected pin | Add no-connect flag or wire |
| `pin_to_pin` | Power output conflict | Remove duplicate PWR_FLAG |
| `power_pin_not_driven` | No power source | Add PWR_FLAG to power net |

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `kicad9_schematic.py` | Main schematic generator |
| `generate_pin_model.py` | Creates pin model from parts/connections |
| `validate_*.py` | Validates each step output |
| `pin_model.json` | Parts with pin-to-net mappings |
| `Debug.kicad_sch` | Generated KiCad 9 schematic |
| `Debug.kicad_pro` | KiCad project file (open this!) |
| `sym-lib-table` | Symbol library paths |
| `fp-lib-table` | Footprint library paths |
