# RadioReceiver KiCad Generator

Automates creating a KiCad project/schematic for the ESP32-S3 portable radio receiver: starting from semantic part/net definitions, it downloads JLCPCB libraries, maps pins, and emits a ready-to-open KiCad project.

## Prerequisites
- Python 3.10+ on Windows.
- KiCad installed (scripts assume the standard user path `%USERPROFILE%\Documents\KiCad`).
- JLC2KiCadLib installed; default path in `download_jlcpcb_libs.py` is `C:\Users\AndreasSpiess\AppData\Local\Programs\Python\Python312\Scripts\JLC2KiCadLib.exe` (adjust if yours differs).
- Internet access only for the library download step.

## Key inputs
- `parts.yaml`: Semantic parts list (with quantities/prefixes).
- `parts_options.csv`: Engineer selections; rows marked with `X` in the `selected` column are used.
- `connections.yaml`: Semantic nets using `Component.Pin` or `Component.Pin_Number`.
- KiCad JLCPCB library location: `%USERPROFILE%\Documents\KiCad\JLCPCB` (created by the download step).

## Outputs
- `parts_with_designators.json`: Parts with assigned reference designators.
- `symbol_pins.json`: Pin names/numbers/positions parsed from the JLCPCB symbol lib.
- `parts_with_netlabels.json`: Parts plus resolved net labels per pin.
- KiCad project artifacts: `RadioReceiver.kicad_pro`, `RadioReceiver.kicad_sch`, `RadioReceiver.kicad_pcb`, `sym-lib-table`, `fp-lib-table`.

## End-to-end flow
Run these from the repository root:

1) Assign designators based on `parts.yaml` and selected options in `parts_options.csv`:
```powershell
python assign_designators.py
```

2) Download JLCPCB symbols/footprints for selected LCSC parts (writes to `%USERPROFILE%\Documents\KiCad\JLCPCB`). Use `--force` to re-download or `--register` to add to global KiCad tables:
```powershell
python download_jlcpcb_libs.py
```

3) Parse the downloaded symbol library to extract pin metadata:
```powershell
python parse_library_pins.py
```

4) Map semantic nets to concrete pin numbers, producing `parts_with_netlabels.json`:
```powershell
python map_connections.py
```

5) Generate the KiCad project and schematic with all symbols, footprints, and net labels applied:
```powershell
python generate_schematic.py
```

## Updating the design
- Edit `parts.yaml` for part list/quantities/prefixes; edit `parts_options.csv` for chosen LCSC parts; edit `connections.yaml` for nets.
- Re-run the steps above in order. If you change the JLCPCB lib location or JLC2KiCadLib path, update the constants near the top of `download_jlcpcb_libs.py` and `generate_schematic.py` accordingly.
