# Step 0: FSD Review & Clarification Gate

Perform a strict technical review of the FSD to ensure it is unambiguous, electrically feasible, safe, and compatible with the KiCad schematic generator.

---

## Purpose

Before parts extraction and schematic generation, validate the FSD against all technical requirements and generate questions where information is ambiguous, missing, or contradictory.
present this to the user and discoss until all isues are solved by the enhanced Functional Specification Document.

**The output must be:**
- A list of questions and required clarifications
- OR a statement that the FSD is ready for Step 1

**No further processing is allowed until all critical issues are resolved.**

---

## Required Inputs

- `design/input/FSD_*.md` - Functional Specification Document
- `KiCAD_Generator.md` - Defines all schematic-generation constraints

---

## Section A — Component & Electrical Requirements

### A1. Component Completeness

**Ask questions when:**
- Important ICs do not have a specific part number
- Supply voltages for components are missing
- Required peripherals (I²C, SPI, ADC, GPIO) are unspecified or incomplete

### A2. Voltage Levels

**Ask:**
- What are the exact operating voltages for each subsystem?
- Is every digital interface voltage-compatible with the MCU?

### A3. Current Requirements

**Ask:**
- What is the estimated current consumption of each subsystem?
- Is the chosen regulator able to supply the total load?

**If missing → generate questions.**

---

## Section B — Pin Assignments & Restrictions

### B1. Avoid MCU Strapping Pins

**The review must detect use of restricted pins such as:**

| MCU Family | Restricted Pins | Reason |
|------------|-----------------|--------|
| ESP32 | GPIO0, GPIO2, GPIO12, GPIO15 | Boot strapping |
| ESP32-S3 | GPIO0, GPIO3, GPIO45, GPIO46 | Boot strapping |
| ESP32-C3 | GPIO2, GPIO8, GPIO9 | Boot strapping |

**Ask:**
> The FSD assigns function X to a restricted/strapping pin. Do you want to reassign it?

**If the pin is avoidable → require reassignment.**

### B2. Clarify Reserved Pins

**Ask:**
- Are any GPIOs reserved for debugging, boot mode, or programming?
- Is JTAG/SWD debugging required? (reserves specific pins)
- Are USB D+/D- pins needed for USB functionality?

---

## Section C — Communication Buses

### C1. Verify I²C Address Space

For every I²C device, verify its I²C address:

**Ask:**
> Device X has I²C address 0xNN. Device Y also uses 0xNN. Should we change one device or add an I²C multiplexer?

**Also ask:**
- Are all I²C devices intended to share the same bus?
- Are there any devices with configurable addresses that should be changed?

### C2. Level Shifting

**Ask:**
> Device X operates at Vx but connects to MCU at Vy. Should we insert a level shifter?

**Or:**
> Can we safely avoid a level shifter by selecting a 3.3V-tolerant variant?

**If user wants to avoid level shifters → enforce 3.3V-compatible devices only.**

### C3. Bus Pull-ups

**Ask:**
- What pull-up resistor value should be used for I²C? (typical: 2.2kΩ - 10kΩ)
- Should pull-ups be on the MCU side or peripheral side?

---

## Section D — Protection, Bypass & Required Supporting Components

The FSD must include or allow the generation of:

| Component | Purpose | Required When |
|-----------|---------|---------------|
| Bypass capacitors | IC power filtering | Every IC |
| Bulk capacitor | Rail stability | Main power rails |
| ESD protection | Transient suppression | External connectors |
| USB TVS diodes | USB protection | USB present |
| Ferrite beads | EMI filtering | Per datasheet |
| Matching networks | RF impedance | RF components |

**Ask:**
> Do you approve the automatic insertion of datasheet-recommended bypass capacitors?

> Allow the generator to add mandatory protection elements such as TVS diodes, ferrite beads, and input filters?

**If not approved → require explicit definition in FSD.**

### D1. Reference Design Components

**Ask:**
- Should we include all components from the manufacturer's reference design?
- Are there any reference design components that should be omitted?

---

## Section E — Package Sizes

**Ask:**
> What is the preferred passive package size? (0402 / 0603 / 0805)

> What is the maximum acceptable package size for ICs?

> Are through-hole components acceptable, or SMD only?

**If not defined → request clarification.**

| Package | Use Case |
|---------|----------|
| 0402 | Space-constrained, reflow only |
| 0603 | Standard, hand-solderable |
| 0805 | Easy assembly, higher power |

---

## Section F — Conflict & Feasibility Checks

**Generate questions if:**

### F1. Power Budget
- Total current draw exceeds regulator capacity
- Total current draw exceeds USB power (500mA / 1.5A)
- LDO power dissipation exceeds thermal limits: `P = (Vin - Vout) × Iload`

### F2. Signal Integrity
- High-speed signals routed without consideration for impedance
- Analog signals sharing ground with noisy digital circuits

### F3. RF Requirements
- RF components lack required matching networks
- Antenna specifications incomplete

### F4. Internal Contradictions
- FSD contradicts itself across sections
- Pin assignments conflict with stated requirements
- Voltage levels inconsistent between sections

---

## Section G — Output Format

### If issues exist:

```markdown
## Step 0 Review Results — Issues Found

### Critical (must be resolved before Step 1)
1. **<Issue title>**
   - Section: <FSD section reference>
   - Problem: <Description>
   - Question: <What needs to be clarified?>

### Required Clarifications
1. **<Topic>**
   - Question: <Specific question>
   - Options: <Available choices if applicable>

### Optional Improvements
1. **<Topic>**
   - Recommendation: <Suggested improvement>
   - Benefit: <Why this helps>
```

### If ready:

```markdown
## Step 0 Review Results — READY

The FSD is complete, consistent, and satisfies all generator requirements.

**Verified:**
- [ ] All components have part numbers or clear specifications
- [ ] Voltage levels are compatible
- [ ] Current budget is within regulator capacity
- [ ] No I²C address conflicts
- [ ] No restricted pins used (or explicitly approved)
- [ ] Protection measures defined or auto-insertion approved
- [ ] Package sizes specified

**Proceed to Step 1.**
```

---

## Exit Criteria (Blocker Logic)

**Only proceed to Step 1 when ALL of the following are satisfied:**

| Check | Requirement |
|-------|-------------|
| Critical issues | None remaining |
| I²C addresses | Verified collision-free |
| Restricted pins | Not used (unless unavoidable and explicitly approved) |
| Voltage levels | Compatible, or level shifters accepted |
| Protection | Bypass capacitors, ESD, filters permitted or specified |
| Package sizes | Preferences defined |
| Electrical specs | All missing information clarified |
| Power budget | Verified feasible |

---

## If Issues Cannot Be Resolved

**DO NOT proceed to Step 1!**

1. Document all unresolved issues
2. Present questions to the user
3. Wait for clarification
4. Update FSD with answers
5. Re-run Step 0 review

```
⚠️  BLOCKER: Step 0 → Review → Get clarifications → Update FSD → Re-validate → Step 1

This gate ensures no ambiguity propagates into the schematic generation pipeline.
```
