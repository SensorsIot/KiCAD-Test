# ESP32-S3 Radio Receiver - Design Specification

## Bill of Materials (BOM)

### Main ICs
| Ref | Part | Package | LCSC/JLCPCB | Notes |
|-----|------|---------|-------------|-------|
| U1 | ESP32-S3-MINI-1-N8 | Module | C2913206 (LCSC) | Main MCU |
| U2 | TP4056 | ESOP-8 | C16581 | Li-ion charger |
| U3 | AMS1117-3.3 | SOT-223 | C6186 (Basic) | 3.3V LDO |
| U4 | SI4735-D60-GU | SSOP-24 | C195417 | AM/FM/SW Radio |
| D1-D3 | WS2812B-B | 5050 | C2761795 | NeoPixel LEDs |

### Connectors
| Ref | Part | Package | JLCPCB | Notes |
|-----|------|---------|--------|-------|
| J1 | USB-C 16-pin | SMD | C393939 (Basic) | Power + Data |
| J2 | JST-PH 2-pin | SMD | C131337 | Battery connector |
| J3 | 3.5mm Audio Jack | TH | C145819 | Headphone out |
| J4 | 4-pin Header | 2.54mm | - | OLED I2C |

### User Interface
| Ref | Part | Package | Notes |
|-----|------|---------|-------|
| SW1 | Reset Button | SMD 6x6mm | Connected to EN |
| ENC1, ENC2 | Rotary Encoder | SMD EC11 | With push button |

### Passives (0603 minimum)
| Ref | Value | Package | Purpose |
|-----|-------|---------|---------|
| C1 | 10uF | 0805 | USB-C VBUS input |
| C2 | 10uF | 0805 | TP4056 input |
| C3 | 10uF | 0805 | TP4056 output/battery |
| C4 | 22uF | 0805 | AMS1117 input |
| C5 | 22uF | 0805 | AMS1117 output |
| C6-C8 | 100nF | 0603 | ESP32 decoupling |
| C9-C11 | 100nF | 0603 | WS2812B decoupling |
| C12 | 100nF | 0603 | SI4735 VDD bypass |
| C13 | 22pF | 0603 | SI4735 crystal |
| C14 | 22pF | 0603 | SI4735 crystal |
| R1 | 5.1k | 0603 | USB-C CC1 |
| R2 | 5.1k | 0603 | USB-C CC2 |
| R3 | 2k | 0603 | TP4056 PROG (500mA) |
| R4 | 10k | 0603 | ESP32 EN pullup |
| R5 | 4.7k | 0603 | I2C SDA pullup |
| R6 | 4.7k | 0603 | I2C SCL pullup |
| Y1 | 32.768kHz | 3215 | SI4735 reference |

---

## Circuit Connections

### POWER SECTION

#### USB-C Connector (J1 - C393939)
```
Pin     Signal      Connection
A1,B12  GND         GND
A4,B9   VBUS        -> TP4056 VIN, AMS1117 VIN
A5      CC1         -> R1 (5.1k) -> GND
B5      CC2         -> R2 (5.1k) -> GND
A6      D+          -> ESP32 GPIO20 (USB_D+)
A7      D-          -> ESP32 GPIO19 (USB_D-)
B6      D+          -> ESP32 GPIO20 (USB_D+)
B7      D-          -> ESP32 GPIO19 (USB_D-)
```

#### TP4056 Battery Charger (U2)
```
Pin     Signal      Connection
1       TEMP        -> 10k NTC or float (no temp sense)
2       PROG        -> R3 (2k to GND) = 500mA charge
3       GND         -> GND
4       VCC         -> VBUS (5V from USB)
5       BAT         -> Battery+ via J2, -> AMS1117 VIN
6       STDBY       -> Optional LED (charging complete)
7       CHRG        -> Optional LED (charging)
8       CE          -> VCC (always enabled)
```

#### AMS1117-3.3 LDO (U3)
```
Pin     Signal      Connection
1       GND/ADJ     -> GND
2       VOUT        -> 3V3 rail (22uF to GND)
3       VIN         -> VBAT/VUSB (22uF to GND)
TAB     GND         -> GND
```

#### Battery Connector (J2 - JST-PH 2-pin)
```
Pin 1: BAT+ (to TP4056 BAT pin)
Pin 2: GND
```

---

### ESP32-S3-MINI-1-N8 (U1)

#### Power Pins
```
Pin     Signal      Connection
1       GND         -> GND
2       GND         -> GND
3       3V3         -> 3V3 rail (+ 100nF decoupling)
```

#### USB (Native)
```
Pin     Signal      Connection
13      GPIO19      -> USB D- (via J1)
14      GPIO20      -> USB D+ (via J1)
```

#### I2C Bus (OLED + SI4735)
```
Pin     Signal      Connection
6       GPIO4       -> SDA (+ 4.7k pullup to 3V3)
5       GPIO5       -> SCL (+ 4.7k pullup to 3V3)
```

#### Rotary Encoder 1 (ENC1)
```
Pin     Signal      Connection
9       GPIO8       -> ENC1_A
10      GPIO9       -> ENC1_B
11      GPIO10      -> ENC1_SW (button)
```

#### Rotary Encoder 2 (ENC2)
```
Pin     Signal      Connection
15      GPIO21      -> ENC2_A
16      GPIO26      -> ENC2_B (directly on chip)
17      GPIO33      -> ENC2_SW (button)
```

#### NeoPixel Data
```
Pin     Signal      Connection
7       GPIO6       -> WS2812B D1 DIN
```

#### SI4735 Reset
```
Pin     Signal      Connection
8       GPIO7       -> SI4735 RST
```

#### Enable/Reset
```
Pin     Signal      Connection
4       EN          -> 10k pullup to 3V3
                    -> SW1 (reset button to GND)
                    -> 100nF to GND (noise filter)
```

---

### SI4735-D60-GU Radio IC (U4)

```
Pin     Signal      Connection
1       DOUT        -> NC (I2C mode)
2       DFS         -> GND (I2C mode, addr 0x11)
3       GPO1/SCLK   -> NC
4       GPO2/INT    -> Optional (interrupt)
5       GPO3        -> NC
6       SCLK        -> ESP32 GPIO5 (SCL)
7       SDIO        -> ESP32 GPIO4 (SDA)
8       SSB         -> NC
9       NC          -> NC
10      NC          -> NC
11      ROUT        -> Headphone R (via 100R)
12      LOUT        -> Headphone L (via 100R)
13      DBYP        -> 100nF to GND
14      VA          -> 3V3 (+ 100nF)
15      GND         -> GND
16      GND         -> GND
17      VD          -> 3V3 (+ 100nF)
18      RCLK        -> 32.768kHz crystal
19      NC          -> NC
20      RST         -> ESP32 GPIO7
21      FMI         -> FM antenna input
22      RFGND       -> GND
23      AMI         -> AM antenna input (ferrite/loop)
24      GND         -> GND
```

#### 32.768kHz Crystal (Y1)
```
RCLK (pin 18) -> Crystal -> GND
Crystal load caps: 2x 22pF to GND
```

---

### OLED Header (J4 - 4-pin 2.54mm)
```
Pin 1: GND
Pin 2: VCC (3V3)
Pin 3: SCL (GPIO5)
Pin 4: SDA (GPIO4)
```

---

### WS2812B NeoPixels (D1, D2, D3)
```
Daisy chain configuration:
ESP32 GPIO6 -> D1 DIN
D1 DOUT -> D2 DIN
D2 DOUT -> D3 DIN
D3 DOUT -> NC

Each WS2812B:
- VDD -> 5V (VBUS) or 3V3
- VSS -> GND
- 100nF decoupling cap close to each LED
```
Note: WS2812B works at 3.3V logic level from ESP32.

---

### Headphone Jack (J3 - 3.5mm TRS)
```
Tip     -> SI4735 LOUT (via 100R)
Ring    -> SI4735 ROUT (via 100R)
Sleeve  -> GND
```

---

### Reset Button (SW1)
```
One side  -> ESP32 EN pin
Other side -> GND
```

---

### Rotary Encoders (ENC1, ENC2 - SMD EC11 compatible)
```
Each encoder has 5 pins:
- A (encoder output A)
- B (encoder output B)
- C (common - connect to GND)
- SW1 (button one side)
- SW2 (button other side - connect to GND)

Encoder signals go directly to ESP32 GPIOs.
Use internal pullups in software, or add external 10k pullups.
```

---

## GPIO Assignment Summary

| GPIO | Function | Notes |
|------|----------|-------|
| GPIO4 | I2C SDA | OLED + SI4735 |
| GPIO5 | I2C SCL | OLED + SI4735 |
| GPIO6 | NeoPixel Data | WS2812B chain |
| GPIO7 | SI4735 Reset | Active low |
| GPIO8 | Encoder 1 A | |
| GPIO9 | Encoder 1 B | |
| GPIO10 | Encoder 1 SW | Button |
| GPIO19 | USB D- | Native USB |
| GPIO20 | USB D+ | Native USB |
| GPIO21 | Encoder 2 A | |
| GPIO26 | Encoder 2 B | Direct chip pin |
| GPIO33 | Encoder 2 SW | Button |

---

## Power Architecture

```
USB-C (5V VBUS)
    |
    +---> TP4056 ---> Li-ion Battery (4.2V)
    |                      |
    +----------------------+
                           |
                      VBAT (3.7-4.2V)
                           |
                      AMS1117-3.3
                           |
                       3V3 Rail
                           |
    +----------+-----------+-----------+
    |          |           |           |
  ESP32     SI4735      OLED      Encoders

WS2812B: Can run from VBUS (5V) or 3V3
```

---

## JLCPCB Part Numbers Summary

| Component | JLCPCB # | Type |
|-----------|----------|------|
| USB-C 16-pin | C393939 | Basic |
| AMS1117-3.3 | C6186 | Basic |
| TP4056 | C16581 | Extended |
| SI4735-D60-GU | C195417 | Extended |
| WS2812B | C2761795 | Extended |
| ESP32-S3-MINI-1-N8 | C2913206 | LCSC |
| JST-PH 2-pin SMD | C131337 | Basic |
| 0603 Resistors | Various | Basic |
| 0603 Capacitors | Various | Basic |
