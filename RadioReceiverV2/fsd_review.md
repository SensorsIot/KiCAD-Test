# FSD Review: ESP32-S3 Portable Radio Receiver

**Date:** 2025-12-18
**Status:** APPROVED (with consignment note)

---

## Proposed Parts Summary

| Module | Qty | LCSC | Part Number | Type | Notes |
|--------|-----|------|-------------|------|-------|
| MCU | 1 | C2913206 | ESP32-S3-MINI-1-N8 | Extended | In stock (6,353) |
| RADIO | 1 | CONSIGNMENT | SI4735-D60-GU | Extended | **Out of stock - user consignment** |
| AMP | 1 | C33233 | PAM8908JER | Extended | In stock (291) |
| CHARGER | 1 | C16581 | TP4056-42-ESOP8 | **Preferred** | In stock (54,957) |
| LDO | 1 | C82942 | ME6211C33M5G-N | Extended | In stock (192,509) |
| PFET | 1 | C10487 | SI2301CDS-T1-GE3 | **Basic** | In stock (137,210) |
| ESD | 1 | C2827654 | USBLC6-2SC6 | Extended | In stock (409,188) |
| LED | 3 | C2843785 | XL-5050RGBC-2812B | Extended | In stock (1,717,547) |
| XTAL | 1 | C32346 | Q13FC13500004 | **Basic** | In stock (667,935) |
| ENC | 2 | C470754 | EC11E15244B2 | Extended | In stock (4,304) |
| BATT | 1 | C173752 | S2B-PH-K-S(LF)(SN) | Extended | In stock (88,126) |
| SW | 1 | C2837531 | KH-6X6X5H-STM | Extended | In stock (234,051) |
| USB | 1 | C165948 | TYPE-C-31-M-12 | Extended | In stock (166,073) |
| JACK | 1 | C18185602 | PJ-320A-4P DIP | Extended | In stock (10,115) |

---

## JLCPCB Assembly Cost Estimate

| Type | Count | Assembly Fee |
|------|-------|--------------|
| Basic | 2 | $0.00 |
| Preferred | 1 | $0.50 |
| Extended | 11 | $33.00 |
| **Total** | **14** | **$33.50** |

*Note: SI4735 consignment not included in assembly fee calculation*

---

## Critical Checks

### Power System

| Check | Status | Notes |
|-------|--------|-------|
| LDO dropout vs battery minimum | MARGINAL | ME6211 100mV dropout at 3.3V cutoff - ESP32-S3 works down to 3.0V |
| Total current budget | OK | ~200mA typical, ME6211 provides 500mA |
| Reverse polarity protection | OK | SI2301 P-FET in high-side |
| USB power limits | OK | 500mA charging via TP4056 |

### Component Selection

| Check | Status | Notes |
|-------|--------|-------|
| SI4735 availability | CONSIGNMENT | All variants out of stock at JLCPCB |
| WS2812B at low battery | MARGINAL | Spec: 3.5-5.5V, Battery min: 3.3V - may glitch at low battery |
| PAM8908 stock | LOW | Only 291 units - order early |

### MCU Pin Assignment (ESP32-S3-MINI-1)

| Check | Status | Notes |
|-------|--------|-------|
| Strapping pins avoided | OK | GPIO0, GPIO3, GPIO45, GPIO46 not used |
| USB D+/D- | OK | GPIO19/GPIO20 for native USB |
| I2C pins | OK | GPIO4 (SDA), GPIO5 (SCL) |

---

## Power Architecture

```
USB 5V ──────────────────────────────> TP4056 VCC
                                           │
                                      ┌────┴────┐
                                      │ Battery │
                                      │3.3-4.2V │
                                      └────┬────┘
                                           │
                                      ┌────┴────┐
                                      │ SI2301  │ Reverse polarity
                                      │  P-FET  │ protection
                                      └────┬────┘
                                           │
                                    VBAT_PROTECTED
                                           │
          ┌──────────────┬─────────────────┼──────────────┐
          │              │                 │              │
     ┌────┴────┐    ┌────┴────┐      ┌────┴────┐    ┌────┴────┐
     │ TP4056  │    │ WS2812B │      │ ME6211  │    │   ...   │
     │  BAT+   │    │  LEDs   │      │  LDO    │    │         │
     └─────────┘    └─────────┘      └────┬────┘    └─────────┘
                                          │
                                       3.3V Rail
                                          │
          ┌──────────────┬────────────────┼──────────────┐
          │              │                │              │
     ┌────┴────┐    ┌────┴────┐      ┌────┴────┐    ┌────┴────┐
     │ESP32-S3 │    │ SI4735  │      │PAM8908  │    │ I2C bus │
     │  MCU    │    │  Radio  │      │  Amp    │    │ pullups │
     └─────────┘    └─────────┘      └─────────┘    └─────────┘
```

---

## GPIO Allocation Summary

| GPIO | Function | Direction |
|------|----------|-----------|
| GPIO4 | I2C SDA | Bidirectional |
| GPIO5 | I2C SCL | Output |
| GPIO6 | NeoPixel Data | Output |
| GPIO7 | SI4735 Reset | Output |
| GPIO8 | Encoder1 A | Input |
| GPIO9 | Encoder1 B | Input |
| GPIO10 | Encoder1 SW | Input |
| GPIO12 | BFO Button | Input |
| GPIO13 | PAM8908 SHDN | Output |
| GPIO19 | USB D- | Bidirectional |
| GPIO20 | USB D+ | Bidirectional |
| GPIO21 | Encoder2 A | Input |
| GPIO35 | Encoder2 B | Input |
| GPIO36 | Encoder2 SW | Input |

---

## User Decisions Required

1. **SI4735 Consignment** - User must provide SI4735-D60-GU separately for assembly
2. **Low Battery Behavior** - Accept potential WS2812B glitches at 3.3V battery
3. **PAM8908 Stock** - Order promptly due to low stock (291 units)

---

## Output Files

- `parts.csv` - Complete parts list with all variants and proposed selections
- Ready for circuit-analysis skill

---

## Next Steps

Run the `circuit-analysis` skill to:
1. Generate `modules.csv` and `module_connections.csv`
2. Generate `bom.csv` with designators
3. Generate `connections.csv` with all circuit connections
