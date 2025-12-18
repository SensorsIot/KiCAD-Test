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
│  USB-C   │────▶│  TP4056  │────▶│     SI4735       │────▶│ PAM8908  │────▶│ Headphone│
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
| Audio Amplifier | PAM8908 stereo headphone amplifier (single-supply) |
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
| Package | SSOP-24 |
| Interface | I2C (400 kHz) |
| I2C Address | 0x11 (DFS pin low) |
| Supply Voltage | 2.7 - 5.5 V |
| Supply Current | 18 mA (FM receive) |
| Reference Clock | 32.768 kHz crystal |


### 4.3 Audio Amplifier - PAM8908 (Headphone Amplifier)

| Parameter | Specification |
|-----------|---------------|
| Part Number | PAM8908JER |
| Package | MSOP-10 |
| Function | Stereo headphone amplifier for SI4735 audio outputs |
| Supply Voltage | 2.5 - 5.5 V (powered from 3.3V rail) |
| Output Power | 25 mW × 2 @ 32Ω |
| Channels | 2 (L/R) |
| Features | Capless output, low quiescent current |

#### 4.3.1 Audio Signal Path
- SI4735 audio outputs (LOUT/ROUT) → 1µF coupling capacitors → PAM8908 inputs
- PAM8908 outputs → Direct to 3.5mm headphone jack (capless design)
- Supply decoupling: 100nF + 10µF on VDD pin

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
| GPIO13 | PAM8908 SHDN | Output | Amplifier shutdown control (active low) |
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
| Pins Used | VBUS, D+, D-, GND, CC1, CC2 |
| Data Protocol | USB 2.0 Full Speed |
| Power Delivery | 5V @ 500mA (USB 2.0 default) |

#### 5.1.1 CC Pin Configuration
- CC1: 5.1k resistor to GND (indicates device, requests 5V)
- CC2: 5.1k resistor to GND

#### 5.1.2 USB ESD Protection
| Parameter | Specification |
|-----------|---------------|
| Part Number | USBLC6-2SC6 |
| Package | SOT-23-6 |
| Function | ESD protection for USB D+/D- lines |
| ESD Rating | ±8kV contact, ±15kV air |
| Capacitance | 3.5pF (minimal signal impact) |

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
| Output Impedance | Driven by PAM8908 capless outputs |

### 5.5 Antenna Connections



only headers. Antennas are external and will be connected to this header

---

## 6. Power Management

AMS1117 and TP4056 are only examples. propose different chips if appropriate

### 6.1 Power Architecture

```
USB 5V ───────────────────────▶ TP4056 VCC (charging input)


                              ┌────────────┐
                              │  Battery   │
                              │ 3.3-4.2V   │
                              └─────┬──────┘
                                    │
                              ┌─────┴──────┐
                              │   P-FET    │ SI2301CDS
                              │  Reverse   │
                              │  Protect   │
                              └─────┬──────┘
                                    │
                             VBAT_PROTECTED
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
   ┌──────────┐               ┌──────────┐               ┌──────────┐
   │  TP4056  │               │  ME6211  │               │ WS2812B  │
   │  BAT+    │               │   LDO    │               │   LEDs   │
   └──────────┘               └────┬─────┘               └──────────┘
                                   │
                                   ▼
                              3.3V Rail
                                   │
         ┌────────────┬────────────┼────────────┬────────────┐
         │            │            │            │            │
         ▼            ▼            ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ ESP32-S3 │ │  SI4735  │ │ PAM8908  │ │   OLED   │ │  I2C     │
   │   MCU    │ │  Radio   │ │  Audio   │ │ Display  │ │ Pullups  │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**Notes:**
- P-FET sits between battery connector and all loads (VBAT_PROTECTED rail)
- TP4056 VCC receives USB 5V for charging; BAT+ connects to VBAT_PROTECTED
- When charging: current flows through P-FET body diode to battery
- When battery reversed: P-FET blocks, all loads protected

### 6.2 Reverse Polarity Protection

| Parameter | Specification |
|-----------|---------------|
| Part Number | SI2301CDS (or equivalent P-FET) |
| Package | SOT-23 |
| Function | Battery reverse polarity protection |
| Topology | P-channel FET in high-side |
| Rds(on) | < 100mΩ (minimal voltage drop) |
| Voltage Drop | < 50mV at 500mA |

**Circuit:** P-FET source to battery+, drain to load, gate to battery- via 10k resistor.
When battery correct: FET on, low Rds drop.
When battery reversed: FET off, circuit protected.

### 6.3 Battery Specifications

| Parameter | Specification |
|-----------|---------------|
| Type | Li-ion or Li-Po |
| Nominal Voltage | 3.7 V |
| Charge Voltage | 4.2 V |
| Minimum Voltage | 3.3 V (cutoff) |
| Recommended Capacity | 1000 - 2000 mAh |

### 6.4 Battery Charger - TP4056

| Parameter | Specification |
|-----------|---------------|
| Part Number | TP4056 |
| Charge Current | 500 mA (set by 2k PROG resistor) |
| Charge Voltage | 4.2 V ± 1% |
| Input Voltage | 4.5 - 5.5 V |
| Thermal Regulation | Yes (junction temp limit) |

### 6.5 Voltage Regulator - ME6211C33M5G-N

| Parameter | Specification |
|-----------|---------------|
| Part Number | ME6211 |
| Output Voltage | 3.3 V ± 1% |
| Output Current | 500 mA maximum |
| Dropout Voltage | 100 mV typical |
| Input Voltage | 2.0 - 6.0 V |
| Quiescent Current | 40 µA typical |

*Note: ME6211 selected over AMS1117 for low dropout (100mV vs 1.1V), enabling operation down to 3.4V battery.*

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

