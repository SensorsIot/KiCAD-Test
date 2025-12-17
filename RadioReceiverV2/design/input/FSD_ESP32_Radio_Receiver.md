# Functional Specification Document
## ESP32-S3 Portable Radio Receiver

| Document Info | |
|---------------|---|
| Project Name | ESP32-S3 Portable Radio Receiver |
| Version | 1.1 |
| Date | 2025-12-17 |
| Status | Draft |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Functional Requirements](#3-functional-requirements)
4. [Hardware Architecture](#4-hardware-architecture)
5. [Interface Specifications](#5-interface-specifications)
6. [Power Management](#6-power-management)
7. [User Interface](#7-user-interface)
8. [Communication Interfaces](#8-communication-interfaces)
9. [Performance Requirements](#9-performance-requirements)
10. [Environmental Requirements](#10-environmental-requirements)
11. [Manufacturing Requirements](#11-manufacturing-requirements)
12. [Bill of Materials](#12-bill-of-materials)
13. [Revision History](#13-revision-history)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional requirements for a portable radio receiver based on the ESP32-S3 microcontroller and SI4735 radio IC. The device is designed to receive AM, FM, and shortwave radio broadcasts with a user-friendly interface.

### 1.2 Scope

This specification covers:
- Hardware design and component selection
- Functional behavior of all subsystems
- User interface requirements
- Power management and battery operation
- Manufacturing considerations for JLCPCB assembly

### 1.3 Definitions and Acronyms

| Term | Definition |
|------|------------|
| MCU | Microcontroller Unit |
| I2C | Inter-Integrated Circuit (serial communication) |
| USB | Universal Serial Bus |
| LDO | Low Dropout Regulator |
| OLED | Organic Light Emitting Diode |
| NeoPixel | Addressable RGB LED (WS2812B) |
| PCB | Printed Circuit Board |
| BOM | Bill of Materials |
| JLCPCB | PCB manufacturer and assembly service |
| LCSC | Electronic component supplier |

### 1.4 References

- ESP32-S3-MINI-1 Datasheet (Espressif)
- SI4735-D60 Programming Guide (Silicon Labs)
- TP4056 Datasheet (TOPPOWER)
- AMS1117 Datasheet (Advanced Monolithic Systems)
- WS2812B Datasheet (Worldsemi)

---

## 2. System Overview

### 2.1 Product Description

The ESP32-S3 Portable Radio Receiver is a compact, battery-powered device capable of receiving AM, FM, and shortwave radio broadcasts. It features:

- Multi-band radio reception (AM/FM/SW)
- Rechargeable Li-ion battery with USB-C charging
- 1.3" OLED display for station information
- Dual rotary encoders for tuning and volume control
- RGB status LEDs
- Headphone audio output
- Wi-Fi and Bluetooth connectivity for future expansion

### 2.2 System Block Diagram

```
                                    ┌─────────────────┐
                                    │   FM Antenna    │
                                    └────────┬────────┘
                                             │
┌──────────┐     ┌──────────┐     ┌──────────┴────────┐     ┌──────────┐
│  USB-C   │────▶│  TP4056  │────▶│     SI4735       │────▶│  TDA1306 │────▶│ Headphone│
│Connector │     │ Charger  │     │   Radio IC       │     │  Amp IC  │     │   Jack   │
└──────────┘     └────┬─────┘     └──────────┬───────┘     └──────────┘
      │               │                      │
      │          ┌────┴─────┐          ┌─────┴─────┐
      │          │  Li-ion  │          │   I2C     │
      │          │ Battery  │          │   Bus     │
      │          └────┬─────┘          └─────┬─────┘
      │               │                      │
      │          ┌────┴─────┐          ┌─────┴─────────────┐
      │          │ AMS1117  │          │                   │
      │          │  3.3V    │          │   ESP32-S3-MINI   │
      │          └────┬─────┘          │                   │
      │               │                │   - Native USB    │
      └───────────────┼────────────────│   - Wi-Fi/BT      │
                      │                │   - GPIO Control  │
                      │                └───────┬───────────┘
                 ┌────┴────┐                   │
                 │  3.3V   │         ┌─────────┼─────────┐
                 │  Rail   │         │         │         │
                 └────┬────┘         │         │         │
                      │              │         │         │
              ┌───────┼───────┐      │         │         │
              │       │       │      │         │         │
          ┌───┴───┐ ┌─┴──┐ ┌──┴──┐ ┌─┴──┐   ┌──┴──┐   ┌──┴──┐
          │ OLED  │ │Enc1│ │Enc2 │ │LED1│   │LED2 │   │LED3 │
          │Display│ │    │ │     │ │    │   │     │   │     │
          └───────┘ └────┘ └─────┘ └────┘   └─────┘   └─────┘
```

### 2.3 Operating Modes

| Mode | Description |
|------|-------------|
| Radio Mode | Normal operation - receiving and playing radio |
| Charging Mode | Battery charging via USB-C (can operate simultaneously) |
| USB Mode | Connected to PC for firmware updates |
| Sleep Mode | Low power state with radio off |
| Scan Mode | Automatic station scanning |

---

## 3. Functional Requirements

### 3.1 Radio Reception

#### 3.1.1 FM Band
| Parameter | Requirement |
|-----------|-------------|
| Frequency Range | 64 - 108 MHz |
| Tuning Step | 100 kHz (configurable) |
| Sensitivity | -107 dBm typical |
| SNR | > 60 dB |
| Stereo Separation | > 30 dB |

#### 3.1.2 AM Band
| Parameter | Requirement |
|-----------|-------------|
| Frequency Range | 520 - 1710 kHz |
| Tuning Step | 9/10 kHz (configurable) |
| Sensitivity | 25 μV typical |

#### 3.1.3 Shortwave Band
| Parameter | Requirement |
|-----------|-------------|
| Frequency Range | 2.3 - 26.1 MHz |
| Tuning Step | 1/5 kHz (configurable) |

### 3.2 Audio Output

| Parameter | Requirement |
|-----------|-------------|
| Output Type | Stereo headphone (3.5mm TRS) |
| Audio Amplifier | TDA1306 stereo headphone amplifier (single-supply) |
| Output Impedance | 32 - 300 ohm headphones |
| Volume Control | Digital, 64 steps |
| Frequency Response | 20 Hz - 15 kHz |

### 3.3 Display

| Parameter | Requirement |
|-----------|-------------|
| Type | OLED, 1.3 inch diagonal |
| Resolution | 128 x 64 pixels (typical) |
| Interface | I2C |
| Controller | SSD1306 or SH1106 |
| Information Displayed | Frequency, band, signal strength, volume, stereo indicator |

### 3.4 User Controls

| Control | Function |
|---------|----------|
| Encoder 1 (rotate) | Frequency tuning |
| Encoder 1 (press) | Band selection / Menu confirm |
| Encoder 2 (rotate) | Volume control |
| Encoder 2 (press) | Mute toggle / Menu back |
| Reset Button | System reset |
| BFO Button | Toggle BFO/SSB fine-tune mode (GPIO input) |


### 3.5 Status Indicators (NeoPixel LEDs)

| LED | Color | Indication |
|-----|-------|------------|
| LED1 | Green | Power on |
| LED1 | Blue | Bluetooth active |
| LED2 | Amber | Charging |
| LED2 | Green | Fully charged |
| LED3 | Variable | Signal strength (red=weak, green=strong) |

### 3.6 Connectivity

| Interface | Purpose |
|-----------|---------|
| USB-C | Charging, firmware update, serial debug |
| Wi-Fi | Future: internet radio, firmware OTA |
| Bluetooth | Future: audio streaming output |

---

## 4. Hardware Architecture

### 4.1 Microcontroller - ESP32-S3-MINI-1-N8

| Parameter | Specification |
|-----------|---------------|
| Part Number | ESP32-S3-MINI-1-N8 |
| LCSC Part | C2913206 |
| CPU | Dual-core Xtensa LX7, 240 MHz |
| Flash | 8 MB |
| PSRAM | None |
| Wi-Fi | 802.11 b/g/n, 2.4 GHz |
| Bluetooth | BLE 5.0 |
| USB | Native USB 2.0 OTG |
| GPIO | 36 programmable |
| Operating Voltage | 3.0 - 3.6 V |
| Operating Current | 80 mA typical (radio active) |

### 4.2 Radio IC - SI4735-D60-GU

| Parameter | Specification |
|-----------|---------------|
| Part Number | SI4735-D60-GU |
| LCSC Part | C195417 |
| Package | SSOP-24 |
| Interface | I2C (400 kHz) |
| I2C Address | 0x11 (DFS pin low) |
| Supply Voltage | 2.7 - 5.5 V |
| Supply Current | 18 mA (FM receive) |
| Reference Clock | 32.768 kHz crystal |


### 4.3 Audio Amplifier - TDA1306 (Headphone Amplifier)

| Parameter | Specification |
|-----------|---------------|
| Part Number | TDA1306 |
| Function | Stereo headphone amplifier for SI4735 audio outputs |
| Supply Voltage | 2.7 - 5.5 V (powered from 3.3V rail) |
| Channels | 2 (L/R) |
| Control | Optional shutdown/enable from MCU GPIO (recommended for power saving) |

#### 4.3.1 Audio Signal Path (High-Level)
- SI4735 audio outputs (LOUT/ROUT) feed the TDA1306 inputs via AC coupling capacitors.
- TDA1306 outputs drive the 3.5mm headphone jack.
- Provide output coupling and local decoupling per the TDA1306 typical application circuit.

### 4.4 GPIO Allocation

| GPIO | Function | Direction | Notes |
|------|----------|-----------|-------|
| GPIO4 | I2C SDA | Bidirectional | OLED + SI4735 |
| GPIO5 | I2C SCL | Output | OLED + SI4735 |
| GPIO6 | NeoPixel Data | Output | WS2812B chain |
| GPIO7 | SI4735 Reset | Output | Active low |
| GPIO8 | Encoder1 A | Input | Internal pullup |
| GPIO9 | Encoder1 B | Input | Internal pullup |
| GPIO10 | Encoder1 SW | Input | Internal pullup |
| GPIO12 | BFO Button | Input | Internal pullup; active low recommended |
| GPIO13 | TDA1306 SHDN | Output | Optional amp enable/shutdown (polarity per selected part) |
| GPIO19 | USB D- | Bidirectional | Native USB |
| GPIO20 | USB D+ | Bidirectional | Native USB |
| GPIO21 | Encoder2 A | Input | Internal pullup |
| GPIO35 | Encoder2 B | Input | Internal pullup |
| GPIO36 | Encoder2 SW | Input | Internal pullup |

### 4.5 I2C Bus Devices

| Device | Address | Speed |
|--------|---------|-------|
| SI4735 | 0x11 | 400 kHz |
| OLED (SSD1306) | 0x3C | 400 kHz |

---

## 5. Interface Specifications

### 5.1 USB-C Connector

| Parameter | Specification |
|-----------|---------------|
| Part Number | TYPE-C-31-M-12 (or equivalent) |
| LCSC Part | C393939 |
| Pins Used | VBUS, D+, D-, GND, CC1, CC2 |
| Data Protocol | USB 2.0 Full Speed |
| Power Delivery | 5V @ 500mA (USB 2.0 default) |

#### 5.1.1 CC Pin Configuration
- CC1: 5.1k resistor to GND (indicates device, requests 5V)
- CC2: 5.1k resistor to GND

### 5.2 OLED Header

| Pin | Signal | Description |
|-----|--------|-------------|
| 1 | GND | Ground |
| 2 | VCC | 3.3V power |
| 3 | SCL | I2C clock |
| 4 | SDA | I2C data |

### 5.3 Battery Connector

| Parameter | Specification |
|-----------|---------------|
| Type | JST-PH 2-pin |
| Pin 1 | BAT+ (positive) |
| Pin 2 | GND (negative) |
| Compatible Batteries | Single cell Li-ion/Li-Po, 3.7V nominal |

### 5.4 Headphone Jack

| Parameter | Specification |
|-----------|---------------|
| Type | 3.5mm TRS stereo |
| Tip | Left channel |
| Ring | Right channel |
| Sleeve | Ground |
| Output Impedance | Driven by TDA1306; series resistors optional for protection/stability |

### 5.5 Antenna Connections

| Antenna | Connection | Notes |
|---------|------------|-------|
| FM | Wire antenna to FMI pin | ~75cm wire recommended |
| AM | Ferrite bar antenna or loop | Connect to AMI pin |

---

## 6. Power Management

AMS1117 and TP4056 are only examples. propose different chips if appropriate

### 6.1 Power Architecture

```
USB 5V ──┬──▶ TP4056 ──▶ Battery (4.2V max)
         │                    │
         │                    ▼
         │              ┌──────────┐
         └──────────────┤ AMS1117  ├──▶ 3.3V Rail
                        │   3.3V   │
                        └──────────┘
```

### 6.2 Battery Specifications

| Parameter | Specification |
|-----------|---------------|
| Type | Li-ion or Li-Po |
| Nominal Voltage | 3.7 V |
| Charge Voltage | 4.2 V |
| Minimum Voltage | 3.0 V (cutoff) |
| Recommended Capacity | 1000 - 2000 mAh |

### 6.3 Battery Charger - TP4056

| Parameter | Specification |
|-----------|---------------|
| Part Number | TP4056 |
| LCSC Part | C16581 |
| Charge Current | 500 mA (set by 2k PROG resistor) |
| Charge Voltage | 4.2 V ± 1% |
| Input Voltage | 4.5 - 5.5 V |
| Thermal Regulation | Yes (junction temp limit) |

#### 6.3.1 Charge Current Selection

| PROG Resistor | Charge Current |
|---------------|----------------|
| 10k | 130 mA |
| 5k | 250 mA |
| 2k | 500 mA |
| 1.2k | 780 mA |
| 1k | 1000 mA |

### 6.4 Voltage Regulator - AMS1117-3.3

| Parameter | Specification |
|-----------|---------------|
| Part Number | AMS1117-3.3 |
| LCSC Part | C6186 (Basic) |
| Output Voltage | 3.3 V ± 1% |
| Output Current | 1 A maximum |
| Dropout Voltage | 1.1 V typical |
| Input Voltage | 4.5 - 12 V |
| Quiescent Current | 5 mA typical |

### 6.5 Power Budget

| Component | Current (typical) | Current (max) |
|-----------|-------------------|---------------|
| ESP32-S3 (active) | 80 mA | 350 mA |
| ESP32-S3 (light sleep) | 2 mA | - |
| SI4735 (FM) | 18 mA | 24 mA |
| OLED Display | 20 mA | 30 mA |
| WS2812B (3x, white) | 60 mA | 180 mA |
| AMS1117 quiescent | 5 mA | 10 mA |
| **Total (typical)** | **183 mA** | **594 mA** |

### 6.6 Battery Life Estimate

| Battery Capacity | Estimated Runtime |
|------------------|-------------------|
| 1000 mAh | ~5 hours |
| 1500 mAh | ~8 hours |
| 2000 mAh | ~11 hours |

*Based on typical current of 183mA with LEDs at low brightness*

---

## 7. User Interface

### 7.1 Rotary Encoders

| Parameter | Specification |
|-----------|---------------|
| Type | Incremental, quadrature output |
| Package | SMD (EC11 compatible) |
| Pulses per Revolution | 20 typical |
| Switch | Momentary push button, integrated |
| Debounce | Software, 5ms typical |

### 7.2 Reset Button

| Parameter | Specification |
|-----------|---------------|
| Type | Tactile, momentary |
| Package | SMD 6x6mm |
| Function | Connects ESP32 EN pin to GND |
| Debounce | Hardware RC (10k + 100nF) |

### 7.3 NeoPixel LEDs

| Parameter | Specification |
|-----------|---------------|
| Part Number | WS2812B-B |
| LCSC Part | C2761795 |
| Package | 5050 SMD |
| Quantity | 3 |
| Data Protocol | Single-wire, 800 kHz |
| Color Depth | 24-bit (8-bit per color) |
| Operating Voltage | 3.5 - 5.3 V |

### 7.4 OLED Display

| Parameter | Specification |
|-----------|---------------|
| Size | 1.3 inch diagonal |
| Resolution | 128 x 64 pixels |
| Controller | SSD1306 or SH1106 |
| Interface | I2C, address 0x3C |
| Connection | 4-pin header (plug-in module) |

---

## 8. Communication Interfaces

### 8.1 I2C Bus

| Parameter | Specification |
|-----------|---------------|
| Speed | 400 kHz (Fast Mode) |
| Pull-up Resistors | 4.7k ohm to 3.3V |
| SDA Pin | GPIO4 |
| SCL Pin | GPIO5 |

### 8.2 USB Interface

| Parameter | Specification |
|-----------|---------------|
| Type | USB 2.0 Full Speed (12 Mbps) |
| Mode | Device only |
| Class | CDC (serial) for programming/debug |
| Connector | USB-C |

### 8.3 SI4735 Control Interface

| Command | Description |
|---------|-------------|
| POWER_UP | Initialize chip, select band |
| SET_FREQUENCY | Set tuning frequency |
| GET_REV | Read chip revision |
| FM_TUNE_FREQ | Tune FM frequency |
| AM_TUNE_FREQ | Tune AM frequency |
| GET_INT_STATUS | Read interrupt status |
| FM_RSQ_STATUS | Read FM signal quality |
| SET_PROPERTY | Configure chip properties |

---

## 9. Performance Requirements

### 9.1 Startup Time

| Event | Maximum Time |
|-------|--------------|
| Power on to radio playing | 3 seconds |
| Wake from sleep | 500 ms |
| Band change | 200 ms |

### 9.2 Tuning Performance

| Parameter | Requirement |
|-----------|-------------|
| Frequency change response | < 100 ms |
| Seek time (per station) | < 50 ms |
| Full band scan | < 30 seconds |

### 9.3 Display Update Rate

| Parameter | Requirement |
|-----------|-------------|
| Frequency display | < 50 ms after change |
| Signal strength | 200 ms update interval |
| Volume indicator | Immediate |

---

## 10. Environmental Requirements

### 10.1 Operating Conditions

| Parameter | Range |
|-----------|-------|
| Temperature | 0°C to +45°C |
| Humidity | 20% to 80% RH (non-condensing) |
| Altitude | 0 to 3000m |

### 10.2 Storage Conditions

| Parameter | Range |
|-----------|-------|
| Temperature | -20°C to +60°C |
| Humidity | 10% to 90% RH |

### 10.3 ESD Protection

| Parameter | Requirement |
|-----------|-------------|
| HBM (Human Body Model) | ± 2 kV on USB connector |
| Contact discharge | ± 4 kV on exposed metal |

---

## 11. Manufacturing Requirements

### 11.1 PCB Specifications

| Parameter | Specification |
|-----------|---------------|
| Layers | 2 (minimum) |
| Thickness | 1.6 mm |
| Copper Weight | 1 oz (35 μm) |
| Surface Finish | HASL or ENIG |
| Solder Mask | Green (default) |
| Silkscreen | White |
| Minimum Trace | 0.2 mm / 8 mil |
| Minimum Space | 0.2 mm / 8 mil |

### 11.2 Component Requirements

| Parameter | Specification |
|-----------|---------------|
| Minimum Passive Size | 0603 (1608 metric) |
| Assembly Service | JLCPCB SMT |
| Preferred Parts | JLCPCB Basic parts where possible |

### 11.3 Assembly Notes

1. USB-C connector requires careful alignment - use stencil
2. ESP32-S3-MINI module has exposed pad - ensure thermal via
3. SI4735 SSOP-24 requires fine pitch soldering
4. WS2812B LEDs are heat sensitive - reflow < 260°C, 10s max
5. Crystal Y1 requires clean pads - no flux residue

---

## 12. Bill of Materials

### 12.1 Active Components

| Ref | Description | Value/Part | Package | LCSC | Type |
|-----|-------------|------------|---------|------|------|
| U1 | MCU Module | ESP32-S3-MINI-1-N8 | Module | C2913206 | Extended |
| U2 | Battery Charger | TP4056 | ESOP-8 | C16581 | Extended |
| U3 | LDO Regulator | AMS1117-3.3 | SOT-223 | C6186 | Basic |
| U4 | Radio IC | SI4735-D60-GU | SSOP-24 | C195417 | Extended |
| U5 | Headphone Amplifier | TDA1306 | SOP-8 (typical) | (select LCSC) | Extended |
| D1-D3 | RGB LED | WS2812B-B | 5050 | C2761795 | Extended |

### 12.2 Connectors

| Ref | Description | Value/Part | Package | LCSC | Type |
|-----|-------------|------------|---------|------|------|
| J1 | USB Connector | USB-C 16-pin | SMD | C393939 | Basic |
| J2 | Battery Connector | JST-PH 2-pin | SMD | C131337 | Basic |
| J3 | Audio Jack | 3.5mm TRS | TH | C145819 | Extended |
| J4 | OLED Header | 1x04 2.54mm | TH | - | - |

### 12.3 Switches

| Ref | Description | Package | LCSC | Type |
|-----|-------------|---------|------|------|
| SW1 | Reset Button | 6x6mm SMD | C127509 | Basic |
| ENC1, ENC2 | Rotary Encoder | SMD EC11 | - | Extended |

### 12.4 Passive Components

| Ref | Value | Package | LCSC | Type | Purpose |
|-----|-------|---------|------|------|---------|
| R1, R2 | 5.1k | 0603 | C23186 | Basic | USB-C CC pulldown |
| R3 | 2k | 0603 | C22975 | Basic | TP4056 PROG |
| R4 | 10k | 0603 | C25804 | Basic | ESP32 EN pullup |
| R5, R6 | 4.7k | 0603 | C25900 | Basic | I2C pullup |
| R7, R8 | 100R | 0603 | C22775 | Basic | Audio output (optional, if used) |
| R9, R10 | 10k | 0603 | C25804 | Basic | TDA1306 gain/bias network (typical) |
| C17, C18 | 1uF | 0603/0805 | (select LCSC) | Basic | Audio input coupling (SI4735 -> TDA1306) |
| C19, C20 | 220uF | TH/SMD | (select LCSC) | Extended | Headphone output coupling (TDA1306 -> jack) |
| C21 | 1uF | 0603/0805 | (select LCSC) | Basic | TDA1306 local supply decoupling |
| C1-C3 | 10uF | 0805 | C15850 | Basic | Power filter |
| C4, C5 | 22uF | 0805 | C45783 | Basic | LDO caps |
| C6-C16 | 100nF | 0603 | C14663 | Basic | Bypass caps |
| C13, C14 | 22pF | 0603 | C1653 | Basic | Crystal load |
| Y1 | 32.768kHz | 3215 | C32346 | Basic | SI4735 reference |

### 12.5 Cost Estimate

| Category | Est. Cost (1 unit) |
|----------|-------------------|
| PCB (JLCPCB) | $2-5 |
| Basic Parts Assembly | $3-5 |
| Extended Parts | $8-12 |
| ESP32-S3-MINI | $3 |
| SI4735 | $4 |
| Battery (not included) | $5-10 |
| OLED Module (not included) | $3-5 |
| **Total (excl. battery/OLED)** | **$20-30** |

---

## 13. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | - | Initial release |
| 1.1 | 2025-12-17 | - | Added BFO button (GPIO) and TDA1306 headphone amplifier |

---

## Appendix A: Schematic Checklist

- [ ] USB-C connector with CC resistors
- [ ] TP4056 charger with PROG resistor
- [ ] AMS1117-3.3 with input/output caps
- [ ] Battery connector (JST-PH)
- [ ] ESP32-S3-MINI with decoupling
- [ ] EN pin RC circuit and reset button
- [ ] Native USB connections (D+/D-)
- [ ] SI4735 with crystal and bypass caps
- [ ] I2C bus with pullup resistors
- [ ] OLED header
- [ ] TDA1306 headphone amplifier stage with coupling and decoupling capacitors
- [ ] Headphone jack (driven by TDA1306; series resistors optional)
- [ ] 3x WS2812B with bypass caps
- [ ] 2x Rotary encoders
- [ ] BFO button (GPIO input with pull-up and debounce)
- [ ] Antenna connections (FM/AM)
- [ ] Power symbols and net labels

## Appendix B: PCB Layout Guidelines

1. **Power Section**: Place near USB-C connector, minimize high-current trace length
2. **ESP32-S3**: Central location, ground plane under module
3. **SI4735**: Keep analog section away from digital noise
4. **Crystal**: Close to SI4735, minimize trace length
5. **Antenna traces**: Keep FM antenna trace away from digital signals
6. **USB traces**: Match D+/D- length, keep short
7. **Decoupling caps**: Place close to IC power pins
8. **NeoPixels**: Can be placed along edge for visibility
