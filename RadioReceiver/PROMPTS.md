# LLM Prompts for Schematic Generation

Use these prompts in sequence with Gemini, ChatGPT, or Claude.
Attach the FSD document to the first prompt.

---

## Step 1: Extract Core Components

```
You are an electronics design engineer. Analyze the attached Functional Specification Document (FSD) and extract all explicitly mentioned electronic components.

For each component, identify:
- Functional name (what it does in the design)
- Part number or type (if specified)
- Key specifications (voltage, current, package, etc.)
- Quantity needed

Output format (YAML):

```yaml
# core-parts.yaml
# Extracted from: [FSD filename]
# Date: [today]

components:
  - name: [functional_name]
    part: [part_number or type]
    description: [what it does]
    specifications:
      voltage: [if applicable]
      current: [if applicable]
      package: [if specified]
    quantity: [number]
    fsd_reference: [section/page where mentioned]
```

Rules:
1. Only include components explicitly mentioned in the FSD
2. Use semantic names (MCU, Battery_Charger, not U1, U2)
3. Note any ambiguities or missing specifications
4. If the FSD mentions alternatives, list them all

After the YAML, list any questions or clarifications needed about the components.
```

---

## Step 2: Research Supporting Components

```
You are an electronics design engineer. For each component in the attached core-parts.yaml, research the typical supporting components required for proper operation.

Use your knowledge and web search to find:
1. Official datasheet recommendations
2. Reference designs from manufacturers
3. Application notes
4. Best practice guidelines

For each core component, identify ALL required supporting parts:
- Bypass/decoupling capacitors (values, quantity, placement)
- Pull-up/pull-down resistors
- Protection components (ESD, reverse polarity, etc.)
- Crystal/oscillator components
- Filtering components
- Any other required external components

Output format (YAML):

```yaml
# component-research.yaml
# Research for: [project name]
# Date: [today]

research:
  - component: [name from core-parts]
    datasheet_url: [URL if found]
    reference_design_url: [URL if found]

    required_supporting_parts:
      - name: [descriptive name]
        type: [capacitor/resistor/etc]
        value: [value with unit]
        quantity: [number]
        purpose: [why needed]
        placement: [near pin X, etc]
        critical: [yes/no - will it fail without this?]
        source: [datasheet page/app note/best practice]

    recommended_supporting_parts:
      - name: [descriptive name]
        type: [type]
        value: [value]
        purpose: [why recommended]
        benefit: [what improvement it provides]
        source: [where this recommendation comes from]

    design_notes:
      - [any important notes about using this component]

    alternatives:
      - part: [alternative part number]
        pros: [advantages]
        cons: [disadvantages]
        pin_compatible: [yes/no]
```

Rules:
1. Always check for manufacturer-recommended bypass capacitors
2. Note voltage ratings (must exceed max operating voltage)
3. Consider temperature ratings if specified in FSD
4. Flag any components that need special consideration
5. If multiple valid approaches exist, note them as options

After the YAML, list:
1. Any questions about design choices
2. Options that need user decision
3. Potential issues or concerns discovered
```

---

## Step 3: Generate Complete Parts List

```
You are an electronics design engineer. Using the attached files:
- core-parts.yaml (main components from FSD)
- component-research.yaml (supporting components research)

Generate a complete, consolidated parts list.

Output format (YAML):

```yaml
# LLM-parts.yaml
# Project: [name]
# Generated: [date]
# Source FSD: [filename]

components:
  # === [Category: Power] ===
  - name: [semantic_name]
    part: [specific part number or generic type]
    value: [for passives: resistance, capacitance, etc]
    package: [0603, SOT-23, etc]
    prefix: [R/C/U/D/J/SW/etc]
    quantity: [number needed]
    description: [brief description]
    belongs_to: [parent component name, or null if core part]
    critical: [yes/no]

  # Example entries:
  - name: MCU
    part: ESP32-S3-MINI-1-N8
    package: SMD-Module
    prefix: U
    quantity: 1
    description: Main microcontroller
    belongs_to: null
    critical: yes

  - name: C_MCU_Bypass_3V3
    part: ceramic capacitor
    value: 100nF
    package: 0603
    prefix: C
    quantity: 3
    description: MCU 3.3V bypass capacitors
    belongs_to: MCU
    critical: yes

# Part options requiring decision:
options:
  - for_component: [component name]
    choice_needed: [what needs to be decided]
    options:
      - option: 1
        part: [part number]
        value: [if applicable]
        pros:
          - [advantage 1]
          - [advantage 2]
        cons:
          - [disadvantage 1]
        recommendation: [yes/no]
        reason: [why recommended or not]
      - option: 2
        part: [alternative]
        pros:
          - [advantage]
        cons:
          - [disadvantage]
        recommendation: [yes/no]
        reason: [why]

# Questions for designer:
questions:
  - component: [which component]
    question: [what needs clarification]
    impact: [how answer affects design]
    default: [suggested default if no answer]
```

Rules:
1. Group components by category (Power, MCU, Radio, UI, Connectors, Passives)
2. Use consistent naming: [Function]_[Qualifier] (e.g., C_MCU_Bypass, R_I2C_Pullup)
3. belongs_to: null for core FSD components, parent name for supporting parts
4. Prefix must match: R=resistor, C=capacitor, U=IC, D=diode/LED, J=connector, SW=switch, Y=crystal
5. Consolidate identical parts (e.g., "quantity: 3" not three separate entries)
6. Present options with clear pros/cons for any ambiguous choices

After the YAML:
1. Summary of total component count by type
2. List of decisions needed from designer
3. Any concerns or recommendations
```

---

## Step 4: Generate Connections

```
You are an electronics design engineer. Using the attached files:
- FSD document (original requirements)
- LLM-parts.yaml (complete parts list)
- component-research.yaml (pin information and typical connections)

Generate all electrical connections (nets) for the design.

Output format (YAML):

```yaml
# LLM-connections.yaml
# Project: [name]
# Generated: [date]

nets:
  # === Power Rails ===
  GND:
    - [Component.Pin]
    - [Component.Pin]

  +3V3:
    - [Component.Pin]
    - [Component.Pin]

  # === Signal Groups ===
  # Group: I2C Bus
  SDA:
    - MCU.GPIO4
    - Radio_IC.SDIO
    - R_I2C_SDA.2

  SCL:
    - MCU.GPIO5
    - Radio_IC.SCLK
    - R_I2C_SCL.2

# Connection format:
# - Use semantic component names (not designators)
# - Pin names should match datasheet or be descriptive
# - For passives: use pin 1 and 2
# - For ICs: use actual pin names from datasheet
# - Group related signals with comments

# Unconnected pins (directly to be connected to a power rail or left open)
explicit_no_connect:
  - component: [name]
    pin: [pin name]
    reason: [why not connected]

# Design notes
notes:
  - net: [net name]
    note: [important information about this connection]
```

Connection rules:
1. Every IC power pin must connect to appropriate rail
2. Every IC ground pin must connect to GND
3. Bypass capacitors connect between power pin and GND (place near the pin)
4. Pull-up resistors: one end to signal, one end to power rail
5. Pull-down resistors: one end to signal, one end to GND
6. Use consistent pin naming from datasheets

For each functional block, verify:
- [ ] All power connections present
- [ ] All ground connections present
- [ ] All signal connections per FSD requirements
- [ ] All bypass capacitors properly connected
- [ ] All pull-up/pull-down resistors connected

After the YAML:
1. Connection summary (total nets, signals per block)
2. List of any pins intentionally left unconnected
3. Any questions about signal routing or pin selection
4. Warnings about potential issues (e.g., signal integrity, power sequencing)
```

---

## Step 5: Validation Review

```
You are an electronics design engineer performing a design review. Analyze the attached files:
- FSD document
- LLM-parts.yaml
- LLM-connections.yaml

Perform these checks:

1. COMPLETENESS CHECK
   - Are all FSD requirements addressed?
   - Is every component connected?
   - Are all power pins connected to power?
   - Are all ground pins connected to ground?

2. ELECTRICAL CHECK
   - Are bypass capacitor values appropriate?
   - Are pull-up/pull-down values correct for the bus speed?
   - Are voltage levels compatible between connected components?
   - Are current requirements met?

3. BEST PRACTICE CHECK
   - Is ESD protection present on external interfaces?
   - Are test points available for debugging?
   - Are critical signals properly filtered?

Output format (YAML):

```yaml
# validation-report.yaml
# Project: [name]
# Date: [date]

summary:
  status: [PASS / PASS_WITH_WARNINGS / NEEDS_REVIEW]
  total_issues: [count]
  critical_issues: [count]

issues:
  - id: 1
    severity: [critical/warning/info]
    category: [completeness/electrical/best_practice]
    component: [affected component]
    description: [what's wrong]
    recommendation: [how to fix]

checklist:
  fsd_requirements_met: [yes/no/partial]
  all_components_connected: [yes/no]
  power_connections_complete: [yes/no]
  ground_connections_complete: [yes/no]
  bypass_caps_present: [yes/no]
  esd_protection_present: [yes/no/not_required]

recommendations:
  - [suggested improvement 1]
  - [suggested improvement 2]
```

Be thorough but practical. Flag real issues, not theoretical concerns.
```

---

## Usage Notes

1. **Run prompts in order** - each builds on previous outputs
2. **Attach relevant files** - always include outputs from previous steps
3. **Answer questions** - when LLM asks questions, provide answers before proceeding
4. **Review options** - make decisions on presented options before Step 4
5. **Iterate if needed** - re-run steps if significant changes are made

## File Flow

```
FSD.md
   ↓ [Step 1]
llm-research/core-parts.yaml
   ↓ [Step 2]
llm-research/component-research.yaml
   ↓ [Step 3]
LLM-parts.yaml + llm-research/options.yaml
   ↓ [User decisions]
   ↓ [Step 4]
LLM-connections.yaml
   ↓ [Step 5]
llm-research/validation-report.yaml
   ↓ [Fix issues if any]
   ↓ [Run pipeline scripts]
KiCAD schematic
```

## Directory Structure

```
RadioReceiver/
├── llm-research/           # LLM intermediate outputs
│   ├── core-parts.yaml
│   ├── component-research.yaml
│   ├── options.yaml
│   └── validation-report.yaml
├── LLM-parts.yaml          # Final parts list (pipeline input)
├── LLM-connections.yaml    # Final connections (pipeline input)
└── ...
```
