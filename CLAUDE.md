# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KiCAD schematic generation pipeline that automates creating PCB designs from a Functional Specification Document (FSD). The project generates a KiCAD 9 schematic for an ESP32-S3 portable radio receiver with SI4735 radio IC.

The pipeline converts semantic part/net definitions into a complete KiCAD project with symbols, footprints, and net labels, ready for JLCPCB assembly.

## Pipeline Commands

Run from `RadioReceiver/llm-research-v2/design/` directory.

**Note:** On Windows, use `py` instead of `python`:

```bash
# 1. Generate KiCAD schematic with placement and routing
py scripts/kicad9_schematic.py              # Full schematic
py scripts/kicad9_schematic.py --debug      # Debug schematic + debug.csv

# 2. Verify connections using KiCad's netlist (requires KiCad 7+)
py scripts/verify_netlist.py output/Debug.kicad_sch
```

After generation, open in KiCAD and run: **Tools > Update Schematic from Symbol Libraries**

### Debug Mode

The `--debug` flag generates:
- `output/Debug.kicad_sch` - Schematic with all parts and wires
- `output/debug.csv` - CSV with pin positions for verification

### Verify Netlist

`verify_netlist.py` uses KiCad CLI to export a netlist and verify all connections:
- Compares actual netlist against expected connections from `pin_model.json`
- Reports missing nets, extra nets, and pin count mismatches
- Requires `kicad-cli` in PATH (included with KiCad 7+)

**Windows with Git Bash** (if Python/KiCad not in PATH):
```bash
PATH="$PATH:/c/Program Files/KiCad/9.0/bin" \
  /c/Users/*/AppData/Local/Programs/Python/Python312/python.exe \
  scripts/verify_netlist.py output/Debug.kicad_sch
```

**Windows CMD** (if Python/KiCad not in PATH):
```cmd
set PATH=%PATH%;C:\Program Files\KiCad\9.0\bin
"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" scripts/verify_netlist.py output/Debug.kicad_sch
```

**Typical Windows paths:**
- Python: `C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe`
- KiCad CLI: `C:\Program Files\KiCad\9.0\bin\kicad-cli.exe`

## Key Input Files (RadioReceiver/)

- `parts.yaml` - Semantic parts list with quantities/prefixes (e.g., MCU, Battery_Charger)
- `parts_options.csv` - JLCPCB part options; mark `X` in `selected` column
- `connections.yaml` - Semantic nets using `Component.Pin` notation
- `custom_library_overrides.yaml` - Manual symbol/footprint mappings for parts not in JLCPCB library

## Key Output Files

- `work/pin_model.json` - Parts with pin-to-net mappings (input to schematic generator)
- `output/Debug.kicad_sch` - Generated schematic (debug mode)
- `output/debug.csv` - Pin positions CSV for verification
- `output/libs/JLCPCB/symbol/JLCPCB.kicad_sym` - Symbol library with all parts

## Architecture

**Workflow**: FSD.md → (LLM) → parts.yaml + connections.yaml → (Python scripts) → .kicad_sch

1. **Semantic layer**: LLM generates `parts.yaml` (components by function) and `connections.yaml` (nets by logical name)
2. **Enrichment**: `enrich_parts.py` queries JLCPCB for part options
3. **Human review**: Engineer selects parts in CSV (single touchpoint)
4. **Resolution**: Scripts assign designators, download symbols, map connections to physical pins
5. **Generation**: Produces KiCAD schematic with net labels on every pin

**Key design decisions**:
- Semantic names in LLM output (MCU, not U1) - keeps reasoning at logical level
- Late designator assignment - enables proper sequential numbering
- Unconnected pins get unique labels (U1_45) for future manual connection
- Y-axis inverted between symbol library (Y+ up) and schematic (Y+ down)

## Wire Routing System

The schematic generator (`kicad9_schematic.py`) includes:

**Placement:**
- Force-directed algorithm groups related parts
- Decoupling capacitors placed in reserved area at bottom
- Parts placed on 2.54mm grid

**Routing:**
- Obstacle-aware Manhattan routing (avoids crossing parts)
- Stub wires extend from pins, then route between stubs
- Multi-pin nets (>3 connections) use net labels instead of wires

**KiCad Connection Detection:**
- KiCad uses coordinate matching - wire endpoint must exactly match pin position
- Small circle at pin = unconnected (coordinates don't match)
- Pin positions must NOT be snapped - use exact calculated values
- Python's `round()` uses banker's rounding; use `math.floor(x + 0.5)` instead

## Library Locations (Windows)

- Symbols: `%USERPROFILE%\Documents\KiCad\JLCPCB\symbol\JLCPCB.kicad_sym`
- Footprints: `%USERPROFILE%\Documents\KiCad\JLCPCB\JLCPCB\`
- Index: `%USERPROFILE%\Documents\KiCad\JLCPCB\lcsc_index.json`

## Known Issues

- JLC2KiCadLib generates KiCAD 6 format; scripts patch to KiCAD 9 format
- SI4735 (C195417) not available on EasyEDA - manually added to JLCPCB.kicad_sym with all 24 pins
- After schematic generation, must run "Update Schematic from Symbol Libraries" in KiCAD to populate lib_symbols section
- Closely placed parts may cause routing to fall back to crossing paths if no obstacle-free route exists
