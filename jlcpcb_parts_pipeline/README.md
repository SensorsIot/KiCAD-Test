# JLCPCB parts enrichment pipeline (LLM + Python)

This bundle provides a reproducible way to go from **design intent** to a **machine-readable, assembly-ready parts file**.

## Files
- `parts_requirements.yaml`
  - The “shopping list” your LLM produces (MPNs/specs per designator).
- `jlc_parts_enriched.schema.json`
  - JSON Schema describing the output structure.
- `enrich_parts.py`
  - A Python tool that queries component sources and writes `jlc_parts_enriched.json`.

## Data sources
1) **Official JLCPCB Components API** (recommended for production)
   - Requires approval via the JLCPCB developer portal.
2) **Fallback for prototyping (no auth): jlcsearch.tscircuit.com**
   - Public JSON endpoints derived from JLCPCB parts listings by appending `.json` to URLs.

## Usage
```bash
pip install requests pyyaml
python enrich_parts.py --in parts_requirements.yaml --out jlc_parts_enriched.json
```

## How the LLM fits
- The LLM reads your FSD and fills/updates `parts_requirements.yaml`.
- The Python program enriches those parts with LCSC/JLCPCB codes, stock, price tiers, package, datasheet URLs.
- Your downstream tooling uses `selection.lcsc` (and/or MPN) to generate BOM/CPL for JLCPCB assembly.
