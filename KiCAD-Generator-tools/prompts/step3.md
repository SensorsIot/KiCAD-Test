# Step 3: Design Options

Present options with REAL pricing data and collect user decisions.

**Purpose:** Decide which optional parts to keep and which variant to select for each option_group.

---

## Prerequisites Check (MUST PASS BEFORE STARTING)

**Verify these files exist and are valid:**

```
[ ] design/work/step2_parts_extended.yaml exists
[ ] All parts have jlcpcb_price and jlcpcb_stock data
```

**Quick validation:**
```bash
ls -la design/work/step2_parts_extended.yaml
python -c "import yaml; yaml.safe_load(open('design/work/step2_parts_extended.yaml'))"
```

**If prerequisites fail -> Go back to Step 2 and complete it first!**

---

## Process Overview

```
step2_parts_extended.yaml (with pricing)
        |
        v
[Present option_groups with pricing]
        |
        v
[Present design_options]
        |
        v
User Decisions
        |
        v
step3_design_options.yaml + decisions.yaml
```

---

## Step 3.1: Present Option Groups

For each `option_group` in step2_parts_extended.yaml, present choices with REAL pricing:

```
## Option Group: <option_group_id>

**Description:** <description from step1>

| Option | Part Number | LCSC | Type | Price | Stock | Pros | Cons |
|--------|-------------|------|------|-------|-------|------|------|
| A | <part_number> | <lcsc> | <Basic/Ext> | $<price> | <stock> | <pros> | <cons> |
| B | <part_number> | <lcsc> | <Basic/Ext> | $<price> | <stock> | <pros> | <cons> |

**Recommendation:** Option <X> - <reason>

**Your choice?** [A/B/...]
```

**Selection criteria:**
1. In stock (jlcpcb_available: true)
2. Basic part preferred over Extended ($3 less assembly fee)
3. Adequate specs for the application
4. Cost-effective

---

## Step 3.2: Present Design Options

For each `design_option` in step1_primary_parts.yaml, present choices:

```
## Design Option: <option_id>

**Question:** <question>
**Context:** <context>

| Choice | Description | Adds Parts | Est. Cost |
|--------|-------------|------------|-----------|
| <value1> | <description> | <parts if any> | <cost> |
| <value2> | <description> | <parts if any> | <cost> |

**Recommendation:** <value> - <reason>

**Your choice?** [<value1>/<value2>/...]
```

---

## Step 3.3: Collect Decisions

After user responds, create TWO output files:

### File 1: `design/work/decisions.yaml`

```yaml
# decisions.yaml
# User decisions from Step 3
# Date: [YYYY-MM-DD]

component_selections:
  # For each option_group, record which candidate was selected
  <option_group_id>: <selected_part_id>

design_options:
  # For each design_option, record the user's choice
  <design_option_id>: "<selected_value>"

notes:
  - "<Reason for selection 1>"
  - "<Reason for selection 2>"
```

### File 2: `design/work/step3_design_options.yaml`

```yaml
# step3_design_options.yaml
# Design options presented and decisions made
# Date: [YYYY-MM-DD]

option_groups_presented:
  <option_group_id>:
    candidates_shown: [<id1>, <id2>]
    selected: <selected_id>
    reason: "<why selected>"

design_options_presented:
  <design_option_id>:
    choices_shown: [<value1>, <value2>]
    selected: "<selected_value>"
    reason: "<why selected>"
    parts_added: [<part_ids if any>]

summary:
  total_options: <count>
  decisions_made: <count>
  parts_from_options: <count>
```

---

## Step 3.4: Display Summary

Show cost summary with selected parts:

```
## Design Decisions Summary

### Option Group Selections
| Option Group | Selected | LCSC | Type | Price |
|--------------|----------|------|------|-------|
| <group_id> | <part_id> | <lcsc> | <type> | $<price> |

### Design Option Selections
| Design Option | Selected | Parts Added |
|---------------|----------|-------------|
| <option_id> | <value> | <parts or "none"> |

### Cost Impact
- Basic parts: <count>
- Extended parts: <count>
- Extended setup fee: $<count * 3>
```

---

## ⚠️ STOP HERE

**Create `design/work/decisions.yaml` with ALL user decisions before proceeding!**

Do NOT proceed to Step 4 until decisions.yaml is complete and validated.

---

## Exit Validation Checklist

**Before proceeding to Step 4, ALL checks must pass:**

### 1. Files Exist and Valid
```bash
ls -la design/work/decisions.yaml design/work/step3_design_options.yaml
python -c "import yaml; yaml.safe_load(open('design/work/decisions.yaml'))"
python -c "import yaml; yaml.safe_load(open('design/work/step3_design_options.yaml'))"
```
- [ ] Both files exist and are valid YAML

### 2. All Option Groups Decided
```bash
# List option_groups from step1
grep "option_group:" design/work/step1_primary_parts.yaml | grep -v "null" | sort -u

# Check decisions.yaml has selection for each
cat design/work/decisions.yaml
```
- [ ] Every option_group has a selection in decisions.yaml

### 3. All Design Options Decided
```bash
# List design_options from step1
grep -A1 "design_options:" design/work/step1_primary_parts.yaml

# Check decisions.yaml has selection for each
cat design/work/decisions.yaml
```
- [ ] Every design_option has a selection in decisions.yaml

### 4. Selected Parts Are Available
- [ ] All selected parts have jlcpcb_available: true
- [ ] Or documented plan for sourcing unavailable parts

---

## If Validation Fails

**DO NOT proceed to Step 4!**

1. Identify which check(s) failed
2. Get missing decisions from user
3. Update decisions.yaml
4. Re-run ALL validation checks
5. Only proceed when ALL checks pass

```
VALIDATION LOOP: Step 3 -> Validate -> Get decisions -> Validate again -> Step 4
```

---

## What Happens Next

Step 4 will:
1. Read decisions.yaml
2. Apply selections to create final parts list
3. Add conditional parts based on design_options
4. Output step4_final_parts.yaml with ONLY selected parts
