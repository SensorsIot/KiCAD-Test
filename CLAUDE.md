# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KiCAD schematic generation pipeline that automates creating PCB designs from a Functional Specification Document (FSD). The project generates a KiCAD 9 schematic for an ESP32-S3 portable radio receiver with SI4735 radio IC.

The pipeline converts semantic part/net definitions into a complete KiCAD project with symbols, footprints, and net labels, ready for JLCPCB assembly.

## Pipeline Commands

Run from `RadioReceiver/` directory in order:

```bash
# 1. Assign reference designators (U1, R1, etc.) from parts.yaml + selected options
python assign_designators.py

# 2. Download JLCPCB symbols/footprints for selected LCSC parts
python download_jlcpcb_libs.py          # Downloads missing parts
python download_jlcpcb_libs.py --force  # Re-download all
python download_jlcpcb_libs.py --register  # Add to global KiCad tables

# 3. Parse downloaded symbols to extract pin metadata
python parse_library_pins.py

# 4. Map semantic nets to concrete pin numbers
python map_connections.py

# 5. Generate KiCAD project and schematic
python generate_schematic.py
```

After generation, open in KiCAD and run: **Tools > Update Schematic from Symbol Libraries**

## Key Input Files (RadioReceiver/)

- `parts.yaml` - Semantic parts list with quantities/prefixes (e.g., MCU, Battery_Charger)
- `parts_options.csv` - JLCPCB part options; mark `X` in `selected` column
- `connections.yaml` - Semantic nets using `Component.Pin` notation
- `custom_library_overrides.yaml` - Manual symbol/footprint mappings for parts not in JLCPCB library

## Key Output Files

- `parts_with_designators.json` - Parts with assigned reference designators
- `symbol_pins.json` - Pin names/numbers/positions from symbol library
- `parts_with_netlabels.json` - Parts with resolved net labels per pin
- `RadioReceiver.kicad_pro/sch/pcb` - KiCAD project files

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

## Library Locations (Windows)

- Symbols: `%USERPROFILE%\Documents\KiCad\JLCPCB\symbol\JLCPCB.kicad_sym`
- Footprints: `%USERPROFILE%\Documents\KiCad\JLCPCB\JLCPCB\`
- Index: `%USERPROFILE%\Documents\KiCad\JLCPCB\lcsc_index.json`

## Known Issues

- JLC2KiCadLib generates KiCAD 6 format; scripts patch to KiCAD 9 format
- SI4735 (C195417) not available on EasyEDA - requires manual symbol or override in `custom_library_overrides.yaml`
- After schematic generation, must run "Update Schematic from Symbol Libraries" in KiCAD to populate lib_symbols section
