#!/usr/bin/env python3
"""
Generate parts list with all pins and unique net labels.
Each pin gets a unique label: {designator}_{pin_number}
"""
import json
from pathlib import Path

PARTS_JSON = Path(__file__).parent.parent / "jlcpcb_parts_pipeline" / "jlc_parts_enriched.json"
PINS_JSON = Path(__file__).parent / "symbol_pins.json"
OUTPUT_JSON = Path(__file__).parent / "parts_with_netlabels.json"

# Component to symbol mapping
COMPONENT_TO_SYMBOL = {
    "U1": "ESP32-S3-MINI-1-N8",
    "U2": "TP4056",
    "U3": "AMS1117-3_3",
    "U4": None,  # SI4735 - manual
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

# Footprints
COMPONENT_TO_FOOTPRINT = {
    "U1": "JLCPCB:BULETM-SMD_ESP32-S3-MINI-1-N8",
    "U2": "JLCPCB:ESOP-8_L4.9-W3.9-P1.27-LS6.0-BL-EP",
    "U3": "JLCPCB:SOT-223-3_L6.5-W3.4-P2.30-LS7.0-BR",
    "U4": "Package_SO:SSOP-24_5.3x8.2mm_P0.65mm",
    "D1": "JLCPCB:LED-SMD_4P-L5.0-W5.0-TL_WS2812B-B",
    "D2": "JLCPCB:LED-SMD_4P-L5.0-W5.0-TL_WS2812B-B",
    "D3": "JLCPCB:LED-SMD_4P-L5.0-W5.0-TL_WS2812B-B",
    "J1": "JLCPCB:USB-C-SMD_TYPE-C16PIN",
    "J2": "JLCPCB:CONN-TH_B2B-PH-K-S",
    "J3": "JLCPCB:AUDIO-SMD_PJ-227-5A",
    "J4": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "SW1": "JLCPCB:KEY-SMD_4P-L6.0-W6.0-P4.50-LS9.5-BL",
    "ENC1": "JLCPCB:SW-TH_EC11E18244A5",
    "ENC2": "JLCPCB:SW-TH_EC11E18244A5",
    "Y1": "JLCPCB:FC-135R_L3.2-W1.5",
}

# SI4735 pins (manual - not in JLCPCB library)
SI4735_PINS = [
    {"name": "DOUT", "number": "1"},
    {"name": "DFS", "number": "2"},
    {"name": "GPO1", "number": "3"},
    {"name": "GPO2", "number": "4"},
    {"name": "GPO3", "number": "5"},
    {"name": "SCLK", "number": "6"},
    {"name": "SDIO", "number": "7"},
    {"name": "SSB", "number": "8"},
    {"name": "NC1", "number": "9"},
    {"name": "NC2", "number": "10"},
    {"name": "ROUT", "number": "11"},
    {"name": "LOUT", "number": "12"},
    {"name": "DBYP", "number": "13"},
    {"name": "VA", "number": "14"},
    {"name": "GND", "number": "15"},
    {"name": "GND", "number": "16"},
    {"name": "VD", "number": "17"},
    {"name": "RCLK", "number": "18"},
    {"name": "NC3", "number": "19"},
    {"name": "RST", "number": "20"},
    {"name": "FMI", "number": "21"},
    {"name": "RFGND", "number": "22"},
    {"name": "AMI", "number": "23"},
    {"name": "GND", "number": "24"},
]


def main():
    # Load symbol pins
    with open(PINS_JSON) as f:
        symbol_pins = json.load(f)

    parts = []

    for designator, symbol_name in sorted(COMPONENT_TO_SYMBOL.items()):
        # Get pins for this symbol
        if symbol_name is None:
            # SI4735 - manual pins
            if designator == "U4":
                pins_data = SI4735_PINS
            else:
                pins_data = []
        else:
            pins_data = symbol_pins.get(symbol_name, [])

        # Get footprint
        footprint = COMPONENT_TO_FOOTPRINT.get(designator, "")
        if not footprint and designator.startswith("C"):
            footprint = "JLCPCB:C0603" if designator not in ["C1","C2","C3","C4","C5"] else "JLCPCB:C0805"
        if not footprint and designator.startswith("R"):
            footprint = "JLCPCB:R0603"

        # Build pins with unique net labels
        pins = []
        for pin in pins_data:
            pin_num = pin["number"]
            pin_name = pin["name"]
            # Unique net label: designator_pinnumber
            net_label = f"{designator}_{pin_num}"

            pins.append({
                "number": pin_num,
                "name": pin_name,
                "net_label": net_label
            })

        part = {
            "designator": designator,
            "symbol": symbol_name or "SI4735-D60-GU",
            "footprint": footprint,
            "pins": pins
        }
        parts.append(part)

    # Save output
    output = {"parts": parts}
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"Generated parts list: {OUTPUT_JSON}")
    print(f"\nTotal parts: {len(parts)}")

    total_pins = sum(len(p["pins"]) for p in parts)
    print(f"Total pins: {total_pins}")
    print(f"Total unique net labels: {total_pins}")

    print("\n" + "="*60)
    print("PARTS WITH PINS AND NET LABELS")
    print("="*60)

    for part in parts:
        print(f"\n{part['designator']} ({part['symbol']})")
        print(f"  Footprint: {part['footprint']}")
        print(f"  Pins ({len(part['pins'])}):")
        for pin in part['pins'][:8]:  # Show first 8 pins
            print(f"    {pin['number']:>5} [{pin['name']:>10}] -> {pin['net_label']}")
        if len(part['pins']) > 8:
            print(f"    ... and {len(part['pins']) - 8} more pins")


if __name__ == "__main__":
    main()
