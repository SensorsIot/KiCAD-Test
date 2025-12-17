# Step 2: Enrich with JLCPCB Data

Fetch JLCPCB data (pricing, stock, variants) for all parts from step1_primary_parts.yaml.

**Purpose:** Find the best JLCPCB variant for each part (in stock, Basic preferred over Extended).

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid before proceeding:**

```
[ ] design/work/step1_primary_parts.yaml exists
[ ] design/input/FSD_*.md exists
```

**Quick validation:**
```bash
ls -la design/work/step1_primary_parts.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step1_primary_parts.yaml'))"
```

**If prerequisites fail -> Go back to Step 1 and complete it first!**

---

## Process Overview

```
step1_primary_parts.yaml
        |
        v
[Automated JLCPCB Enrichment Script]
        |
        v
step2_parts_extended.yaml (with pricing/availability/variants)
```

---

## Step 2.1: Run JLCPCB Enrichment

Run the enrichment script to fetch JLCPCB data for ALL parts:

```bash
python scripts/enrich_parts.py \
    --input work/step1_primary_parts.yaml \
    --output work/step2_parts_extended.yaml
```

The script will:
1. Read all parts from step1_primary_parts.yaml
2. Query JLCPCB API for each part (by LCSC code, part number, and base name)
3. Find all available variants
4. Select best variant (in stock, Basic > Preferred > Extended)
5. Add: price, stock, part_type (Basic/Extended), availability, datasheet URL
6. Flag parts that are out of stock or unavailable
7. Output enriched YAML

**If script is not available**, manually look up each part on jlcpcb.com/parts and add:
- `jlcpcb_price`: Unit price at qty 10
- `jlcpcb_stock`: Current stock quantity
- `jlcpcb_type`: "Basic" or "Extended"
- `jlcpcb_available`: true/false
- `jlcpcb_datasheet`: Datasheet URL

---

## Step 2.2: Review Enriched Data

After enrichment, `step2_parts_extended.yaml` will contain:

```yaml
meta:
  source: step1_primary_parts.yaml
  enriched_at: <timestamp>
  stats:
    total: <count>
    found: <count>
    not_found: <count>
    basic: <count>
    extended: <count>
    out_of_stock: <count>

parts:
  - id: <part_id>
    name: "<Part name>"
    part_number: "<Part number from FSD>"
    package: "<Package>"
    category: <category>
    quantity: <number>
    option_group: <group_id or null>
    # --- Added by enrichment script ---
    lcsc: "<Best LCSC code found>"
    jlcpcb_price: <price>
    jlcpcb_stock: <stock_count>
    jlcpcb_type: "<Basic|Preferred|Extended>"
    jlcpcb_available: <true|false>
    jlcpcb_package: "<JLCPCB package name>"
    jlcpcb_datasheet: "<URL>"
    jlcpcb_lookup:
      searched: true
      found: <true|false>
      search_queries: [...]
      all_candidates: [...]
      selected: {...}
```

**Check for issues:**
- Parts with `jlcpcb_available: false`
- Parts with `jlcpcb_stock: 0`
- LCSC codes that couldn't be found
- Parts where original LCSC differs from selected (mismatch)

---

## Step 2.3: Handle Out-of-Stock Parts

For parts with no stock:
1. Check if the enrichment script found alternatives (in `all_candidates`)
2. If alternatives exist with stock, the script will have selected the best one
3. If NO alternatives have stock, flag for manual sourcing (AliExpress, Mouser, DigiKey)

---

## Exit Validation Checklist

**Before proceeding to Step 3, ALL checks must pass:**

### 1. File Exists and Valid
```bash
ls -la design/work/step2_parts_extended.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step2_parts_extended.yaml'))"
```
- [ ] `step2_parts_extended.yaml` exists and is valid YAML

### 2. All Parts Enriched
```bash
# Check stats in meta section
grep -A5 "stats:" design/work/step2_parts_extended.yaml
```
- [ ] `found` equals `total` (or document why some parts not found)
- [ ] `not_found` is 0 or explained

### 3. Stock Status Reviewed
```bash
grep "jlcpcb_available: false" design/work/step2_parts_extended.yaml
grep "jlcpcb_stock: 0" design/work/step2_parts_extended.yaml
```
- [ ] All out-of-stock parts have been noted
- [ ] Decision made for each (wait, source elsewhere, use alternative)

### 4. LCSC Codes Valid
```bash
grep "lcsc:" design/work/step2_parts_extended.yaml | grep -v "C[0-9]"
```
- [ ] All LCSC codes match pattern C followed by digits (or null for manual source)

---

## If Validation Fails

**DO NOT proceed to Step 3!**

1. Identify which check(s) failed
2. Re-run enrichment or manually fix issues
3. Re-run ALL validation checks
4. Only proceed when ALL checks pass

```
VALIDATION LOOP: Step 2 -> Validate -> Fix if needed -> Validate again -> Step 3
```

---

## What Happens Next

Step 3 will:
1. Present option_groups with REAL pricing data from enrichment
2. Present design_options for user decision
3. Collect user decisions
4. Output step3_design_options.yaml

**STOP in Step 3** to create decisions.yaml before proceeding to Step 4.
