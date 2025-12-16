#!/usr/bin/env python3
"""
Generate KiCAD netlist from DESIGN_SPEC connections.
Maps logical net names to component pins.
"""
import json
from pathlib import Path
from datetime import datetime

# Load symbol pin data
PINS_FILE = Path(__file__).parent / "symbol_pins.json"
OUTPUT_DIR = Path(__file__).parent

# Component to symbol mapping (from generate_schematic_v2.py)
COMPONENT_SYMBOL = {
    "U1": "ESP32-S3-MINI-1-N8",
    "U2": "TP4056",
    "U3": "AMS1117-3_3",
    # U4: SI4735 - not in JLCPCB library, will handle manually
    "D1": "WS2812B-B{slash}W",
    "D2": "WS2812B-B{slash}W",
    "D3": "WS2812B-B{slash}W",
    "J1": "TYPE-C16PIN",
    "J2": "B2B-PH-K-S(LF)(SN)",
    "J3": "PJ-227-5A",
    "J4": "Header-Male-2_54_1x40",
    "SW1": "K2-1102SP-C4SC-04",
    "ENC1": "EC11E18244A5",
    "ENC2": "EC11E18244A5",
    "Y1": "Q13FC1350000400",
    # Passives - generic 2-pin
    "C1": "CL21A106KOQNNNE",
    "C2": "CL21A106KOQNNNE",
    "C3": "CL21A106KOQNNNE",
    "C4": "CL21A226MQQNNNE",
    "C5": "CL21A226MQQNNNE",
    "C6": "CL10B104KB8NNNC",
    "C7": "CL10B104KB8NNNC",
    "C8": "CL10B104KB8NNNC",
    "C9": "CL10B104KB8NNNC",
    "C10": "CL10B104KB8NNNC",
    "C11": "CL10B104KB8NNNC",
    "C12": "CL10B104KB8NNNC",
    "C13": "CL10C220JB8NNNC",
    "C14": "CL10C220JB8NNNC",
    "C15": "CL10B104KB8NNNC",
    "C16": "CL10B104KB8NNNC",
    "C17": "CL10B104KB8NNNC",
    "R1": "0603WAF5101T5E",
    "R2": "0603WAF5101T5E",
    "R3": "0603WAF2001T5E",
    "R4": "0603WAF1002T5E",
    "R5": "0603WAF4701T5E",
    "R6": "0603WAF4701T5E",
    "R7": "0603WAF1000T5E",
    "R8": "0603WAF1000T5E",
}

# SI4735 pins (not in JLCPCB library - manual definition based on datasheet)
SI4735_PINS = {
    "1": "DOUT", "2": "DFS", "3": "GPO1", "4": "GPO2", "5": "GPO3",
    "6": "SCLK", "7": "SDIO", "8": "SSB", "9": "NC1", "10": "NC2",
    "11": "ROUT", "12": "LOUT", "13": "DBYP", "14": "VA", "15": "GND1",
    "16": "GND2", "17": "VD", "18": "RCLK", "19": "NC3", "20": "RST",
    "21": "FMI", "22": "RFGND", "23": "AMI", "24": "GND3"
}

def define_nets():
    """
    Define all nets based on DESIGN_SPEC.md connections.
    Returns: dict of {net_name: [(component, pin_number), ...]}
    """
    nets = {}

    def add_connection(net_name, component, pin):
        if net_name not in nets:
            nets[net_name] = set()
        nets[net_name].add((component, str(pin)))

    # ========== POWER NETS ==========

    # GND - Ground connections
    add_connection("GND", "J1", "A1B12")     # USB-C GND
    add_connection("GND", "J1", "B1A12")     # USB-C GND
    add_connection("GND", "U1", "1")         # ESP32 GND
    add_connection("GND", "U1", "2")         # ESP32 GND
    add_connection("GND", "U1", "42")        # ESP32 GND
    add_connection("GND", "U1", "43")        # ESP32 GND
    # ESP32 has many GND pins (46-60, GND) - add key ones
    add_connection("GND", "U1", "46")
    add_connection("GND", "U2", "3")         # TP4056 GND
    add_connection("GND", "U3", "1")         # AMS1117 GND
    add_connection("GND", "U4", "15")        # SI4735 GND
    add_connection("GND", "U4", "16")        # SI4735 GND
    add_connection("GND", "U4", "24")        # SI4735 GND
    add_connection("GND", "U4", "2")         # SI4735 DFS to GND (I2C mode)
    add_connection("GND", "U4", "22")        # SI4735 RFGND
    add_connection("GND", "J2", "2")         # Battery GND
    add_connection("GND", "J4", "1")         # OLED GND
    add_connection("GND", "D1", "3")         # WS2812B VSS
    add_connection("GND", "D2", "3")         # WS2812B VSS
    add_connection("GND", "D3", "3")         # WS2812B VSS
    add_connection("GND", "SW1", "2")        # Reset button to GND
    add_connection("GND", "ENC1", "C")       # Encoder common
    add_connection("GND", "ENC2", "C")       # Encoder common
    add_connection("GND", "Y1", "2")         # Crystal GND side

    # VBUS - USB 5V
    add_connection("VBUS", "J1", "A4B9")     # USB-C VBUS
    add_connection("VBUS", "J1", "B4A9")     # USB-C VBUS
    add_connection("VBUS", "U2", "4")        # TP4056 VCC (via diode typically)
    add_connection("VBUS", "C1", "1")        # Input cap
    # WS2812B can run from VBUS
    add_connection("VBUS", "D1", "1")        # WS2812B VDD
    add_connection("VBUS", "D2", "1")        # WS2812B VDD
    add_connection("VBUS", "D3", "1")        # WS2812B VDD

    # VBAT - Battery voltage
    add_connection("VBAT", "U2", "5")        # TP4056 BAT
    add_connection("VBAT", "J2", "1")        # Battery +
    add_connection("VBAT", "U3", "3")        # AMS1117 VIN
    add_connection("VBAT", "C3", "1")        # TP4056 output cap
    add_connection("VBAT", "C4", "1")        # AMS1117 input cap

    # +3V3 - 3.3V rail
    add_connection("+3V3", "U3", "2")        # AMS1117 VOUT
    add_connection("+3V3", "U3", "4")        # AMS1117 VOUT (second pin)
    add_connection("+3V3", "U1", "3")        # ESP32 3V3
    add_connection("+3V3", "U4", "14")       # SI4735 VA
    add_connection("+3V3", "U4", "17")       # SI4735 VD
    add_connection("+3V3", "J4", "2")        # OLED VCC
    add_connection("+3V3", "C5", "1")        # AMS1117 output cap
    add_connection("+3V3", "R4", "1")        # EN pullup
    add_connection("+3V3", "R5", "1")        # SDA pullup
    add_connection("+3V3", "R6", "1")        # SCL pullup

    # ========== SIGNAL NETS ==========

    # USB Data
    add_connection("USB_D+", "J1", "A6")     # USB-C DP1
    add_connection("USB_D+", "J1", "B6")     # USB-C DP2
    add_connection("USB_D+", "U1", "24")     # ESP32 IO20 (USB D+)

    add_connection("USB_D-", "J1", "A7")     # USB-C DN1
    add_connection("USB_D-", "J1", "B7")     # USB-C DN2
    add_connection("USB_D-", "U1", "23")     # ESP32 IO19 (USB D-)

    # USB CC pins
    add_connection("CC1", "J1", "A5")        # USB-C CC1
    add_connection("CC1", "R1", "1")         # CC1 resistor

    add_connection("CC2", "J1", "B5")        # USB-C CC2
    add_connection("CC2", "R2", "1")         # CC2 resistor

    # CC resistors to GND
    add_connection("GND", "R1", "2")
    add_connection("GND", "R2", "2")

    # I2C Bus
    add_connection("SDA", "U1", "8")         # ESP32 IO4
    add_connection("SDA", "U4", "7")         # SI4735 SDIO
    add_connection("SDA", "J4", "4")         # OLED SDA
    add_connection("SDA", "R5", "2")         # Pullup

    add_connection("SCL", "U1", "9")         # ESP32 IO5
    add_connection("SCL", "U4", "6")         # SI4735 SCLK
    add_connection("SCL", "J4", "3")         # OLED SCL
    add_connection("SCL", "R6", "2")         # Pullup

    # TP4056 PROG resistor
    add_connection("PROG", "U2", "2")        # TP4056 PROG
    add_connection("PROG", "R3", "1")        # PROG resistor
    add_connection("GND", "R3", "2")         # PROG to GND

    # TP4056 CE (Chip Enable) - tie to VCC
    add_connection("VBUS", "U2", "8")        # CE to VCC

    # ESP32 Enable
    add_connection("EN", "U1", "45")         # ESP32 EN pin
    add_connection("EN", "R4", "2")          # Pullup resistor
    add_connection("EN", "SW1", "1")         # Reset button

    # NeoPixel chain
    add_connection("NEOPIXEL", "U1", "10")   # ESP32 IO6
    add_connection("NEOPIXEL", "D1", "4")    # D1 DIN

    add_connection("LED_CHAIN1", "D1", "2")  # D1 DOUT
    add_connection("LED_CHAIN1", "D2", "4")  # D2 DIN

    add_connection("LED_CHAIN2", "D2", "2")  # D2 DOUT
    add_connection("LED_CHAIN2", "D3", "4")  # D3 DIN

    # SI4735 Reset
    add_connection("SI4735_RST", "U1", "11") # ESP32 IO7
    add_connection("SI4735_RST", "U4", "20") # SI4735 RST

    # Rotary Encoder 1
    add_connection("ENC1_A", "U1", "12")     # ESP32 IO8
    add_connection("ENC1_A", "ENC1", "A")

    add_connection("ENC1_B", "U1", "13")     # ESP32 IO9
    add_connection("ENC1_B", "ENC1", "B")

    add_connection("ENC1_SW", "U1", "14")    # ESP32 IO10
    add_connection("ENC1_SW", "ENC1", "D")   # Button pin D

    # Rotary Encoder 2
    add_connection("ENC2_A", "U1", "25")     # ESP32 IO21
    add_connection("ENC2_A", "ENC2", "A")

    add_connection("ENC2_B", "U1", "26")     # ESP32 IO26
    add_connection("ENC2_B", "ENC2", "B")

    add_connection("ENC2_SW", "U1", "28")    # ESP32 IO33
    add_connection("ENC2_SW", "ENC2", "D")   # Button pin D

    # Audio output
    add_connection("AUDIO_L", "U4", "12")    # SI4735 LOUT
    add_connection("AUDIO_L", "R7", "1")     # Series resistor

    add_connection("AUDIO_R", "U4", "11")    # SI4735 ROUT
    add_connection("AUDIO_R", "R8", "1")     # Series resistor

    add_connection("AUDIO_L_OUT", "R7", "2") # After resistor
    add_connection("AUDIO_L_OUT", "J3", "1") # Audio jack tip (L)

    add_connection("AUDIO_R_OUT", "R8", "2") # After resistor
    add_connection("AUDIO_R_OUT", "J3", "3") # Audio jack ring (R)

    add_connection("GND", "J3", "2")         # Audio jack sleeve (GND)
    add_connection("GND", "J3", "4")         # Audio jack GND
    add_connection("GND", "J3", "5")         # Audio jack GND

    # Crystal
    add_connection("XTAL", "U4", "18")       # SI4735 RCLK
    add_connection("XTAL", "Y1", "1")        # Crystal
    add_connection("XTAL", "C13", "1")       # Load cap

    add_connection("GND", "C13", "2")        # Load cap to GND
    add_connection("GND", "C14", "2")        # Load cap to GND
    # C14 is on crystal GND side, already connected via Y1

    # SI4735 bypass caps
    add_connection("+3V3", "C12", "1")       # SI4735 VDD bypass
    add_connection("GND", "C12", "2")

    add_connection("SI4735_DBYP", "U4", "13")# SI4735 DBYP
    add_connection("SI4735_DBYP", "C15", "1")# Bypass cap
    add_connection("GND", "C15", "2")

    add_connection("+3V3", "C16", "1")       # SI4735 VA bypass
    add_connection("GND", "C16", "2")

    add_connection("+3V3", "C17", "1")       # SI4735 VD bypass
    add_connection("GND", "C17", "2")

    # Decoupling caps
    add_connection("VBUS", "C1", "1")        # USB input
    add_connection("GND", "C1", "2")

    add_connection("VBUS", "C2", "1")        # TP4056 input
    add_connection("GND", "C2", "2")

    add_connection("VBAT", "C3", "1")        # TP4056 output
    add_connection("GND", "C3", "2")

    add_connection("VBAT", "C4", "1")        # AMS1117 input
    add_connection("GND", "C4", "2")

    add_connection("+3V3", "C5", "1")        # AMS1117 output
    add_connection("GND", "C5", "2")

    add_connection("+3V3", "C6", "1")        # ESP32 decoupling
    add_connection("GND", "C6", "2")

    add_connection("+3V3", "C7", "1")        # ESP32 decoupling
    add_connection("GND", "C7", "2")

    add_connection("+3V3", "C8", "1")        # ESP32 decoupling
    add_connection("GND", "C8", "2")

    add_connection("VBUS", "C9", "1")        # WS2812B D1 decoupling
    add_connection("GND", "C9", "2")

    add_connection("VBUS", "C10", "1")       # WS2812B D2 decoupling
    add_connection("GND", "C10", "2")

    add_connection("VBUS", "C11", "1")       # WS2812B D3 decoupling
    add_connection("GND", "C11", "2")

    return nets


def generate_netlist(nets):
    """Generate KiCAD netlist format."""
    # Convert sets to sorted lists
    nets = {k: sorted(list(v)) for k, v in nets.items()}

    lines = ['(export (version "E")']

    # Design section
    lines.append('  (design')
    lines.append(f'    (source "D:\\\\Github\\\\KiCAD-Test\\\\Version2\\\\Version2.kicad_sch")')
    lines.append(f'    (date "{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}")')
    lines.append('    (tool "Python netlist generator")')
    lines.append('    (sheet (number "1") (name "/") (tstamps "/")')
    lines.append('      (title_block')
    lines.append('        (title "ESP32-S3 Radio Receiver")')
    lines.append('        (rev "1.0"))))')

    # Components section
    lines.append('  (components')
    for ref, symbol in sorted(COMPONENT_SYMBOL.items()):
        lines.append(f'    (comp (ref "{ref}")')
        lines.append(f'      (value "{symbol}")')
        lines.append(f'      (libsource (lib "JLCPCB") (part "{symbol}"))')
        lines.append('      (sheetpath (names "/") (tstamps "/")))')
    # Add U4 (SI4735) manually
    lines.append('    (comp (ref "U4")')
    lines.append('      (value "SI4735-D60-GU")')
    lines.append('      (libsource (lib "manual") (part "SI4735-D60-GU"))')
    lines.append('      (sheetpath (names "/") (tstamps "/")))')
    lines.append('  )')

    # Nets section
    lines.append('  (nets')
    for i, (net_name, nodes) in enumerate(sorted(nets.items()), 1):
        lines.append(f'    (net (code "{i}") (name "{net_name}")')
        for ref, pin in nodes:
            lines.append(f'      (node (ref "{ref}") (pin "{pin}"))')
        lines.append('    )')
    lines.append('  )')

    lines.append(')')
    return '\n'.join(lines)


def print_summary(nets):
    """Print connection summary."""
    print("\n" + "=" * 60)
    print("NET CONNECTION SUMMARY")
    print("=" * 60)

    for net_name, nodes in sorted(nets.items()):
        print(f"\n{net_name}:")
        for ref, pin in sorted(nodes):
            print(f"  {ref}.{pin}")


def main():
    print("Generating netlist from DESIGN_SPEC connections...")

    # Define all nets
    nets = define_nets()

    print(f"\nDefined {len(nets)} nets")

    # Count total connections
    total_connections = sum(len(nodes) for nodes in nets.values())
    print(f"Total connections: {total_connections}")

    # Generate netlist
    netlist = generate_netlist(nets)

    # Save netlist
    output_path = OUTPUT_DIR / "Version2.net"
    output_path.write_text(netlist, encoding='utf-8')
    print(f"\nNetlist saved to: {output_path}")

    # Also save as JSON for easy inspection
    json_path = OUTPUT_DIR / "connections.json"
    # Convert sets to lists for JSON
    nets_json = {k: sorted(list(v)) for k, v in nets.items()}
    with open(json_path, 'w') as f:
        json.dump(nets_json, f, indent=2)
    print(f"Connections JSON saved to: {json_path}")

    # Print summary
    print_summary(nets)

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. Open Version2.kicad_sch in KiCAD")
    print("2. File > Import > Netlist...")
    print("3. Select Version2.net")
    print("4. Or: Open PCB editor and import netlist there")
    print("=" * 60)


if __name__ == "__main__":
    main()
