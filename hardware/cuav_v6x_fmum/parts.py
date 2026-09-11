#!/usr/bin/env python3
"""
Parts database for the KiCad replica of the CUAV V6X FMUM + IMU board.

One entry per physical component with its REAL package pin numbers (from the
manufacturer datasheets, see docs/ notes in README) and the net on every pin.
gen_kicad.py turns this into schematic symbols + global labels;
gen_pcb.py turns it into placed, net-assigned footprints on the two boards.

Board coordinate system (both boards): millimetres, origin = top-left corner of
the board outline as seen from the TOP side (SD-card side for the FMUM, sensor
side for the IMU board), x to the right, y down.  side "F" = top, "B" = bottom.
Positions are measured from the photographs (about +-0.5 mm) except where the
Pixhawk DS-010 drawing gives them (connectors, holes, LEDs, outline).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, HERE)
import gen_schematic as G  # noqa: E402

# ---------------------------------------------------------------------------
# STM32H743IIKx ball map (ST "open pin data" XML -> pin name -> ball)
# ---------------------------------------------------------------------------
def load_ballmap():
    import xml.etree.ElementTree as ET
    fn = os.path.join(HERE, "kicad", "lib", "STM32H743IIKx.xml")
    root = ET.parse(fn).getroot()
    tag = root.tag.split('}')[0] + '}Pin' if root.tag.startswith('{') else 'Pin'
    balls = {}     # base name -> list of balls
    fullname = {}  # ball -> full ST pin name
    for p in root.iter(tag):
        name, pos = p.get("Name"), p.get("Position")
        base = re.split(r"[-/(]", name)[0].strip()
        balls.setdefault(base, []).append(pos)
        fullname[pos] = name
    return balls, fullname


BALLS, BALL_FULLNAME = load_ballmap()


def ball(name):
    b = BALLS.get(name)
    if not b:
        raise KeyError(name)
    return b[0]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def P(ref, value, fp, side, x, y, rot, pins, desc="", cls="", verify=""):
    """pins: list of (pad, pin_name, net, etype).  net "" = unconnected."""
    return dict(ref=ref, value=value, fp=fp, side=side, x=x, y=y, rot=rot, pins=pins, desc=desc, cls=cls, verify=verify)


def two(ref, value, fp, side, x, y, rot, n1, n2, desc="", names=("1", "2")):
    return P(ref, value, fp, side, x, y, rot, [("1", names[0], n1, "passive"), ("2", names[1], n2, "passive")], desc)


V33, V5, GND = "FMU_VDD_3V3", "VDD_5V_IN", "GND"

# ---------------------------------------------------------------------------
# U1 pins: every used port pin from gen_schematic.PINS, plus supplies by ball
# ---------------------------------------------------------------------------
def u1_pins():
    pins = []
    for pin, fn, net, dest in G.PINS:
        if not (pin.startswith("P") and pin[2:].isdigit()):
            continue
        if dest.startswith("NC"):
            net = ""
        if pin in ("PC2", "PC3"):           # only the _C balls exist on this package
            b = ball(pin + "_C")
        else:
            b = ball(pin)
        et = "bidirectional"
        fl = fn.lower()
        if "adc" in fl or fl.startswith("gpio in") or "rx" in fl or "miso" in fl or "vbus" in fl or "capture" in fl:
            et = "input"
        elif "out" in fl or "tx" in fl or "sck" in fl or "mosi" in fl or fl.startswith("tim") or "cmd" in fl or "ck" in fl:
            et = "output"
        pins.append((b, pin, net, et))
    # oscillators / special
    pins += [(ball("NRST"), "NRST", "FMU_nRST", "input"), (ball("BOOT0"), "BOOT0", "BOOT0", "input"),
             (ball("VBAT"), "VBAT", "V_RTC_BAT", "power_in"), (ball("PDR_ON"), "PDR_ON", V33, "input"),
             (ball("VDDA"), "VDDA", V33, "power_in"), (ball("VSSA"), "VSSA", GND, "power_in"),
             (ball("VREF+"), "VREF+", V33, "power_in"), (ball("VREF"), "VREF-", GND, "power_in"),
             (ball("VDD33_USB"), "VDD33_USB", V33, "power_in")]
    for b in sorted(set(BALLS["VCAP"])):
        pins.append((b, "VCAP", "VCAP", "passive"))
    for b in sorted(set(BALLS["VDD"])):
        pins.append((b, "VDD", V33, "power_in"))
    for b in sorted(set(BALLS["VSS"])):
        pins.append((b, "VSS", GND, "power_in"))
    used = {p[0] for p in pins}
    # every remaining ball: unconnected GPIO
    for b, full in BALL_FULLNAME.items():
        if b not in used:
            pins.append((b, re.split(r"[-/(]", full)[0].strip(), "", "bidirectional"))
    return pins


def conn_pins(table, nc=set(), power_out=()):
    out = []
    for p in sorted(table):
        net = table[p]
        et = "power_out" if net in power_out else "passive"
        out.append((str(p), net if net != "GND" else "GND", "" if net in nc else net, et))
    return out


# ---------------------------------------------------------------------------
# FMUM: 36.0 x 31.4 mm, 6 layers.  Positions: DS-010 drawing + photos.
# ---------------------------------------------------------------------------
FMUM_BOARD = dict(name="cuav_v6x_fmum", w=36.0, h=31.4, corner_r=2.3, layers=6,
                  holes=[(2.3, 2.3), (33.7, 2.3), (2.3, 29.1), (33.7, 29.1)],  # 2.0 drill, 3.6 pad, GND
                  # baro stress-relief slot (U shape, 0.6 wide), coordinates of the centre-line
                  slot=[(6.3, 0.9), (6.3, 4.3), (10.8, 4.3), (10.8, 0.9)])

X2_TABLE_FIXED = dict(G.X2)
X2_TABLE_FIXED[50] = "FMU_CH3"

FMUM_PARTS = [
    P("U1", "STM32H743IIK6", "gen:UFBGA176", "B", 13.0, 14.4, 0, u1_pins(), "480 MHz Cortex-M7, 2 MB flash", "mcu"),
    P("X1", "DF40C-100DP-0.4V(51)", "gen:DF40-100", "B", 31.9, 16.9, 270, conn_pins(G.X1, power_out={V5}), "Pixhawk Autopilot Bus, 100 pins", "conn",
      verify="pad geometry approximated from the DF40 series drawing; check against Hirose DF40C-100DP-0.4V recommended pattern"),
    P("X2", "DF40C-50DP-0.4V(51)", "gen:DF40-50", "B", 3.0, 16.9, 270, conn_pins(X2_TABLE_FIXED, G.X2_NC), "Pixhawk Autopilot Bus, 50 pins", "conn",
      verify="pad geometry approximated; check Hirose drawing"),
    P("J3", "BM20B(0.8)-34DP-0.4V(53)", "gen:BM20-34", "F", 3.3, 15.9, 270, conn_pins(G.J3, power_out=()), "IMU flex", "conn",
      verify="pad geometry approximated; check Hirose BM20B drawing"),
    P("J4", "microSD push-push", "lib:microSD_HC_Molex_104031-0811", "F", 17.8, 21.0, 0,
      [("1", "DAT2", "SD_D2", "passive"), ("2", "CD/DAT3", "SD_D3", "passive"), ("3", "CMD", "SD_CMD", "passive"), ("4", "VDD", "VDD_3V3_SD", "power_in"),
       ("5", "CLK", "SD_CLK", "passive"), ("6", "VSS", GND, "passive"), ("7", "DAT0", "SD_D0", "passive"), ("8", "DAT1", "SD_D1", "passive"),
       ("9", "SH", GND, "passive"), ("10", "SH", GND, "passive"), ("11", "SH", GND, "passive")],
      "original is Molex 5031821852; library footprint 104031-0811 has the same contact order", "conn",
      verify="footprint is a substitute microSD socket (Molex 104031-0811)"),
    P("U10", "FM25V02A-G", "lib:SOIC-8_3.9x4.9mm_P1.27mm", "F", 25.0, 3.3, 0,
      [("1", "nCS", "SPI5_nCS1_FRAM", "input"), ("2", "SO", "SPI5_MISO_FRAM", "output"), ("3", "nWP", V33, "input"), ("4", "VSS", GND, "power_in"),
       ("5", "SI", "SPI5_MOSI_FRAM", "input"), ("6", "SCK", "SPI5_SCK_FRAM", "input"), ("7", "nHOLD", V33, "input"), ("8", "VDD", V33, "power_in")],
      "256 kbit FRAM, PX4 parameters", "ic"),
    P("U11", "SE050C1 (likely)", "lib:QFN-20-1EP_3x3mm_P0.4mm_EP1.65x1.65mm", "F", 23.3, 11.4, 0,
      [(str(i), "?", "", "passive") for i in range(1, 22)],
      "secure element, I2C4 0x48. Pin assignment not available -> pads left unassigned", "ic",
      verify="SE050 HX2QFN20 pinout not verified; connect SDA=I2C4_SDA_FMU, SCL=I2C4_SCL_FMU, VDD/VIN=FMU_VDD_3V3, ENA=FMU_VDD_3V3 per NXP datasheet"),
    P("U8", "ICM-20649", "lib:QFN-24-1EP_3x3mm_P0.4mm_EP1.75x1.6mm", "B", 15.6, 2.3, 0,
      [("7", "AUX_CL", "", "passive"), ("8", "VDDIO", "VDD_3V3_SENSORS1", "power_in"), ("9", "SDO/AD0", "SPI1_MISO_SENSOR1", "output"),
       ("10", "REGOUT", "IMU3_REGOUT", "passive"), ("11", "FSYNC", GND, "input"), ("12", "INT1", "SPI1_DRDY1_IMU3_INT1", "output"),
       ("13", "VDD", "VDD_3V3_SENSORS1", "power_in"), ("18", "GND", GND, "power_in"), ("19", "INT2", "", "output"), ("20", "RESV", GND, "passive"),
       ("21", "AUX_DA", "", "passive"), ("22", "nCS", "SPI1_nCS1_IMU3", "input"), ("23", "SCL/SCLK", "SPI1_SCK_SENSOR1", "input"),
       ("24", "SDA/SDI", "SPI1_MOSI_SENSOR1", "input")] + [(str(i), "NC", "", "passive") for i in (1, 2, 3, 4, 5, 6, 14, 15, 16, 17)] + [("25", "EP", "", "passive")],
      "IMU 3, SPI1. Pinout: TDK DS-000192 table 9", "ic"),
    P("U9", "ICP-20100", "gen:LGA10-ICP", "B", 8.4, 1.9, 0,
      [("1", "CSB", V33, "input"), ("2", "SCL", "I2C2_SCL_BASE", "input"), ("3", "VSS", GND, "power_in"), ("4", "SDA", "I2C2_SDA_BASE", "bidirectional"),
       ("5", "VDD", "VDD_3V3_SENSORS2", "power_in"), ("6", "SDO/AD0", GND, "input"), ("7", "INT", "I2C2_DRDY1_BARO2", "output"),
       ("8", "RESV", GND, "passive"), ("9", "RESV", GND, "passive"), ("10", "VDDIO", "VDD_3V3_SENSORS2", "power_in")],
      "baro 2, I2C2 addr 0x63 (AD0 low). Pinout: TDK DS-000416 table 18. Sits in the stress-relief slot", "ic"),
    # power
    P("U2", "AP7361C-33 / AMS1117-3.3", "lib:SOT-223-3_TabPin2", "B", 19.0, 24.0, 0,
      [("1", "GND", GND, "power_in"), ("2", "VOUT", V33, "power_out"), ("3", "VIN", V5, "power_in"), ("4", "VOUT(tab)", V33, "passive")],
      "3.3 V main rail. ORIGINAL USES A SWITCHING REGULATOR (QFN + inductor); a 1 A LDO is the simple replica choice", "power",
      verify="substitute part"),
    P("U3", "TLV75533PDBV", "lib:SOT-23-5", "B", 2.6, 24.2, 0,
      [("1", "IN", V5, "power_in"), ("2", "GND", GND, "power_in"), ("3", "EN", "VDD_3V3_SENSORS1_EN", "input"), ("4", "NC", "", "passive"), ("5", "OUT", "VDD_3V3_SENSORS1", "power_out")],
      "sensor domain 1 LDO", "power", verify="substitute part"),
    P("U4", "TLV75533PDBV", "lib:SOT-23-5", "B", 2.6, 27.6, 0,
      [("1", "IN", V5, "power_in"), ("2", "GND", GND, "power_in"), ("3", "EN", "VDD_3V3_SENSORS2_EN", "input"), ("4", "NC", "", "passive"), ("5", "OUT", "VDD_3V3_SENSORS2", "power_out")],
      "sensor domain 2 LDO", "power", verify="substitute part"),
    P("U5", "TLV75533PDBV", "lib:SOT-23-5", "F", 33.0, 8.5, 0,
      [("1", "IN", V5, "power_in"), ("2", "GND", GND, "power_in"), ("3", "EN", "VDD_3V3_SENSORS3_EN", "input"), ("4", "NC", "", "passive"), ("5", "OUT", "VDD_3V3_SENSORS3", "power_out")],
      "sensor domain 3 LDO", "power", verify="substitute part"),
    P("U6", "TLV75533PDBV", "lib:SOT-23-5", "F", 33.0, 12.0, 0,
      [("1", "IN", V5, "power_in"), ("2", "GND", GND, "power_in"), ("3", "EN", "VDD_3V3_SENSORS4_EN", "input"), ("4", "NC", "", "passive"), ("5", "OUT", "VDD_3V3_SENSORS4", "power_out")],
      "sensor domain 4 LDO", "power", verify="substitute part"),
    P("U7", "TPS22919 / SiP32431 (load switch)", "lib:SOT-23-5", "F", 30.0, 15.0, 0,
      [("1", "IN", V33, "power_in"), ("2", "GND", GND, "power_in"), ("3", "ON", "VDD_3V3_SD_CARD_EN", "input"), ("4", "NC", "", "passive"), ("5", "OUT", "VDD_3V3_SD", "power_out")],
      "microSD power switch", "power", verify="substitute part; check the pinout of the load switch you buy"),
    # crystals
    P("Y1", "16 MHz", "lib:Crystal_SMD_3225-4Pin_3.2x2.5mm", "B", 19.3, 12.7, 90,
      [("1", "1", "16MHZ_IN", "passive"), ("2", "GND", GND, "passive"), ("3", "2", "16MHZ_OUT", "passive"), ("4", "GND", GND, "passive")], "HSE", "xtal"),
    P("Y2", "32.768 kHz", "lib:Crystal_SMD_3215-2Pin_3.2x1.5mm", "B", 23.2, 14.0, 0,
      [("1", "1", "32KHZ_IN", "passive"), ("2", "2", "32KHZ_OUT", "passive")], "LSE / RTC", "xtal"),
    # RTC cell
    P("BT1", "MS621FE (or 0.1 F supercap)", "gen:MS621", "F", 28.8, 25.7, 0,
      [("1", "+", "V_RTC_BAT", "power_out"), ("2", "-", GND, "passive")], "RTC backup cell", "misc"),
    two("D4", "BAT54", "gen:SOD323", "F", 31.5, 21.0, 0, V33, "RTC_CHG", "cell charge diode", ("A", "K")),
    two("R30", "1k", "lib:R_0402_1005Metric", "F", 31.5, 23.0, 0, "RTC_CHG", "V_RTC_BAT", "cell charge resistor"),
    # LEDs (DS-010 positions: blue 6.70, green 8.30, red 9.85 from left; 2.30 from bottom edge)
    P("D3", "LED blue", "lib:LED_0603_1608Metric", "F", 6.70, 29.1, 90, [("1", "K", "LED_BLUE_K", "passive"), ("2", "A", V33, "passive")], "", "led"),
    P("D2", "LED green", "lib:LED_0603_1608Metric", "F", 8.30, 29.1, 90, [("1", "K", "LED_GREEN_K", "passive"), ("2", "A", V33, "passive")], "", "led"),
    P("D1", "LED red", "lib:LED_0603_1608Metric", "F", 9.85, 29.1, 90, [("1", "K", "LED_RED_K", "passive"), ("2", "A", V33, "passive")], "", "led"),
    two("R31", "470", "lib:R_0402_1005Metric", "F", 6.70, 26.8, 90, "LED_BLUE_K", "nLED_BLUE"),
    two("R32", "470", "lib:R_0402_1005Metric", "F", 8.30, 26.8, 90, "LED_GREEN_K", "nLED_GREEN"),
    two("R33", "470", "lib:R_0402_1005Metric", "F", 9.85, 26.8, 90, "LED_RED_K", "nLED_RED"),
    # HW id ladder, boot, reset
    two("R40", "24k9", "lib:R_0402_1005Metric", "B", 9.0, 23.5, 0, "HW_VER_REV_DRIVE", "HW_REV_SENSE", "module ID ladder, upper"),
    two("R41", "442k", "lib:R_0402_1005Metric", "B", 9.0, 24.7, 0, "HW_REV_SENSE", GND, "module ID ladder, lower"),
    two("R42", "10k", "lib:R_0402_1005Metric", "F", 14.0, 9.0, 0, "BOOT0", GND, "BOOT0 pull-down"),
    P("TP1", "BT0", "gen:TP", "F", 15.6, 9.0, 0, [("1", "1", "BOOT0", "passive")], "BOOT0 pad", "tp"),
    two("C24", "100n", "lib:C_0402_1005Metric", "B", 29.0, 12.0, 0, "FMU_nRST", GND, "reset cap"),
    P("J1", "TRACE pads", "gen:TRACE", "F", 4.6, 24.6, 0,
      [("1", "TRACECLK", "TRACECLK", "passive"), ("2", "GND", GND, "passive"), ("3", "TRACED0", "nLED_RED", "passive"), ("4", "GND", GND, "passive"),
       ("5", "TRACED1", "nLED_GREEN", "passive"), ("6", "GND", GND, "passive"), ("7", "TRACED2", "nLED_BLUE", "passive"), ("8", "TRACED3", "nARMED", "passive"),
       ("M1", "M", GND, "passive"), ("M2", "M", GND, "passive")], "unpopulated ETM trace footprint", "conn"),
    # sense dividers (10k/10k) for the 4 sensor rails and V5
    two("R1", "10k", "lib:R_0402_1005Metric", "B", 7.2, 23.5, 0, "VDD_3V3_SENSORS1", "SCALED_VDD_3V3_SENSORS1"),
    two("R2", "10k", "lib:R_0402_1005Metric", "B", 7.2, 24.7, 0, "SCALED_VDD_3V3_SENSORS1", GND),
    two("R3", "10k", "lib:R_0402_1005Metric", "B", 7.2, 25.9, 0, "VDD_3V3_SENSORS2", "SCALED_VDD_3V3_SENSORS2"),
    two("R4", "10k", "lib:R_0402_1005Metric", "B", 7.2, 27.1, 0, "SCALED_VDD_3V3_SENSORS2", GND),
    two("R5", "10k", "lib:R_0402_1005Metric", "F", 30.0, 4.0, 0, "VDD_3V3_SENSORS3", "SCALED_VDD_3V3_SENSORS3"),
    two("R6", "10k", "lib:R_0402_1005Metric", "F", 30.0, 5.0, 0, "SCALED_VDD_3V3_SENSORS3", GND),
    two("R7", "10k", "lib:R_0402_1005Metric", "F", 30.0, 6.0, 0, "VDD_3V3_SENSORS4", "SCALED_VDD_3V3_SENSORS4"),
    two("R8", "10k", "lib:R_0402_1005Metric", "F", 30.0, 7.0, 0, "SCALED_VDD_3V3_SENSORS4", GND),
    two("R9", "10k", "lib:R_0402_1005Metric", "B", 23.0, 26.0, 0, V5, "SCALED_V5"),
    two("R10", "10k", "lib:R_0402_1005Metric", "B", 23.0, 27.0, 0, "SCALED_V5", GND),
    # I2C pull-ups 1.5k
    two("R11", "1k5", "lib:R_0402_1005Metric", "B", 10.8, 23.5, 0, V33, "I2C1_SCL_BASE"),
    two("R12", "1k5", "lib:R_0402_1005Metric", "B", 10.8, 24.7, 0, V33, "I2C1_SDA_BASE"),
    two("R13", "1k5", "lib:R_0402_1005Metric", "B", 12.4, 23.5, 0, V33, "I2C2_SCL_BASE"),
    two("R14", "1k5", "lib:R_0402_1005Metric", "B", 12.4, 24.7, 0, V33, "I2C2_SDA_BASE"),
    two("R15", "1k5", "lib:R_0402_1005Metric", "B", 14.0, 23.5, 0, V33, "I2C3_SCL_BASE"),
    two("R16", "1k5", "lib:R_0402_1005Metric", "B", 14.0, 24.7, 0, V33, "I2C3_SDA_BASE"),
    two("R17", "1k5", "lib:R_0402_1005Metric", "B", 9.0, 26.3, 0, V33, "I2C4_SCL_FMU"),
    two("R18", "1k5", "lib:R_0402_1005Metric", "B", 10.8, 26.3, 0, V33, "I2C4_SDA_FMU"),
    # SD pull-ups
    two("R20", "10k", "lib:R_0402_1005Metric", "F", 13.0, 15.5, 90, "VDD_3V3_SD", "SD_CMD"),
    two("R21", "10k", "lib:R_0402_1005Metric", "F", 14.0, 15.5, 90, "VDD_3V3_SD", "SD_D0"),
    two("R22", "10k", "lib:R_0402_1005Metric", "F", 15.0, 15.5, 90, "VDD_3V3_SD", "SD_D1"),
    two("R23", "10k", "lib:R_0402_1005Metric", "F", 16.0, 15.5, 90, "VDD_3V3_SD", "SD_D2"),
    two("R24", "10k", "lib:R_0402_1005Metric", "F", 17.0, 15.5, 90, "VDD_3V3_SD", "SD_D3"),
    # crystal caps
    two("C20", "10p", "lib:C_0402_1005Metric", "B", 21.0, 11.5, 90, "16MHZ_IN", GND),
    two("C21", "10p", "lib:C_0402_1005Metric", "B", 21.0, 14.0, 90, "16MHZ_OUT", GND),
    two("C22", "6p8", "lib:C_0402_1005Metric", "B", 23.2, 16.0, 0, "32KHZ_IN", GND),
    two("C23", "6p8", "lib:C_0402_1005Metric", "B", 25.2, 16.0, 0, "32KHZ_OUT", GND),
    # decoupling / bulk
    two("C1", "10u", "lib:C_0603_1608Metric", "B", 16.5, 24.0, 0, V5, GND),
    two("C2", "10u", "lib:C_0603_1608Metric", "B", 21.5, 24.0, 0, V5, GND),
    two("C3", "22u", "lib:C_0805_2012Metric", "B", 19.0, 27.0, 0, V33, GND),
    two("C4", "2u2", "lib:C_0402_1005Metric", "B", 9.5, 14.0, 90, "VCAP", GND),
    two("C5", "2u2", "lib:C_0402_1005Metric", "B", 16.5, 14.0, 90, "VCAP", GND),
    two("C6", "100n", "lib:C_0402_1005Metric", "B", 17.5, 4.0, 0, "IMU3_REGOUT", GND),
    two("C7", "100n", "lib:C_0402_1005Metric", "B", 13.2, 2.3, 90, "VDD_3V3_SENSORS1", GND),
    two("C8", "1u", "lib:C_0402_1005Metric", "B", 5.2, 23.0, 0, V5, GND),
    two("C9", "1u", "lib:C_0402_1005Metric", "B", 5.2, 25.4, 0, "VDD_3V3_SENSORS1", GND),
    two("C10", "1u", "lib:C_0402_1005Metric", "B", 5.2, 28.8, 0, "VDD_3V3_SENSORS2", GND),
    two("C11", "1u", "lib:C_0402_1005Metric", "F", 33.0, 10.3, 0, "VDD_3V3_SENSORS3", GND),
    two("C12", "1u", "lib:C_0402_1005Metric", "F", 33.0, 13.8, 0, "VDD_3V3_SENSORS4", GND),
    two("C13", "100n", "lib:C_0402_1005Metric", "B", 8.4, 3.4, 90, "VDD_3V3_SENSORS2", GND),
    two("C14", "100n", "lib:C_0402_1005Metric", "F", 25.0, 6.5, 0, V33, GND),
    two("C15", "1u", "lib:C_0402_1005Metric", "F", 25.5, 19.0, 0, "VDD_3V3_SD", GND),
    two("C16", "100n", "lib:C_0402_1005Metric", "F", 24.5, 14.0, 0, V33, GND),
] + [two(f"C{30+i}", "100n", "lib:C_0402_1005Metric", "B", 7.5 + (i % 6) * 1.4, 8.5 + (i // 6) * 1.4, 90, V33, GND, "U1 decoupling") for i in range(12)]

# test pads seen on the photos (nets unknown -> unconnected)
FMUM_PARTS += [P(f"TP{n}", f"TP{n}", "gen:TP", s, x, y, 0, [("1", "1", "", "passive")], "test pad, net unknown", "tp")
               for n, s, x, y in ((2, "F", 30.6, 14.2), (3, "F", 33.5, 21.1), (4, "F", 30.6, 9.3), (7, "F", 30.1, 1.5), (8, "B", 34.8, 8.0))]

# ---------------------------------------------------------------------------
# IMU board: octagon 25 x 18 mm (estimated from photos), 4 layers
# ---------------------------------------------------------------------------
IMU_BOARD = dict(name="cuav_v6x_imu", w=25.0, h=18.0, layers=4, chamfer=(4.8, 4.0), notch_r=1.5,
                 npth=[(2.2, 9.0), (22.8, 9.0)],     # 2.2 mm through holes
                 pads=[("M1", "F", 18.6, 15.2), ("M2", "F", 2.1, 6.5), ("M3", "B", 6.8, 2.2), ("M4", "B", 18.5, 16.9)])

S2, S3, S4 = "VDD_3V3_SENSORS2", "VDD_3V3_SENSORS3", "VDD_3V3_SENSORS4"
IMU_PARTS = [
    P("J1", "BM20B(0.8)-34DS-0.4V(53)", "gen:BM20-34", "B", 16.7, 9.4, 90,
      conn_pins(G.J3, power_out={V5, S2, S3, S4}), "mates FMUM J3 through the FPC jumper", "conn",
      verify="pad geometry approximated; check Hirose BM20B drawing"),
    P("U1", "BMI088", "gen:LGA16-BMI088", "F", 9.4, 4.0, 90,
      [("1", "INT2", "", "output"), ("2", "NC", GND, "passive"), ("3", "VDD", S3, "power_in"), ("4", "GNDA", GND, "power_in"),
       ("5", "CSB2", "SPI3_nCS2_BMI088_GYRO", "input"), ("6", "GNDIO", GND, "power_in"), ("7", "PS", GND, "input"),
       ("8", "SCK", "SPI3_SCK_SENSOR3", "input"), ("9", "SDI", "SPI3_MOSI_SENSOR3", "input"), ("10", "SDO2", "SPI3_MISO_SENSOR3", "output"),
       ("11", "VDDIO", S3, "power_in"), ("12", "INT3", "SPI3_DRDY2_BMI088_INT3_GYRO", "output"), ("13", "INT4", "", "output"),
       ("14", "CSB1", "SPI3_nCS1_BMI088_ACCEL", "input"), ("15", "SDO1", "SPI3_MISO_SENSOR3", "output"), ("16", "INT1", "", "output")],
      "IMU 1, SPI3 (PS = GND). Pinout: Bosch BST-BMI088-DS000 table 14", "ic"),
    P("U2", "ICM-42688-P", "lib:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y", "F", 8.2, 8.8, 0,
      [("1", "AP_SDO/AD0", "SPI2_MISO_SENSOR2", "output"), ("2", "RESV", "", "passive"), ("3", "RESV", "", "passive"), ("4", "INT1", "SPI2_DRDY2_IMU2_INT2", "output"),
       ("5", "VDDIO", S2, "power_in"), ("6", "GND", GND, "power_in"), ("7", "RESV", GND, "passive"), ("8", "VDD", S2, "power_in"),
       ("9", "INT2/FSYNC/CLKIN", GND, "input"), ("10", "RESV", "", "passive"), ("11", "RESV", "", "passive"), ("12", "AP_CS", "SPI2_nCS1_IMU2", "input"),
       ("13", "AP_SCLK", "SPI2_SCK_SENSOR2", "input"), ("14", "AP_SDI", "SPI2_MOSI_SENSOR2", "input")],
      "IMU 2, SPI2. Pinout: TDK DS-000347 table 10", "ic"),
    P("U3", "PNI MagI2C 13156", "gen:QFN28-MAGI2C", "F", 14.5, 6.4, 0,
      [("1", "SDA", "I2C4_SDA_FMU", "bidirectional"), ("2", "RES", GND, "passive"), ("3", "SA0", GND, "input"), ("4", "AVDD", S4, "power_in"),
       ("5", "AVSS", GND, "power_in"), ("6", "ZDRVP", "MAG_ZDRVP", "output"), ("7", "ZINP", "MAG_ZINP", "input"), ("8", "ZINN", "MAG_ZINN", "input"),
       ("9", "ZDRVN", "MAG_ZDRVN", "output"), ("10", "YDRVP", "MAG_YDRVP", "output"), ("11", "YINP", "MAG_YINP", "input"), ("12", "YINN", "MAG_YINN", "input"),
       ("13", "YDRVN", "MAG_YDRVN", "output"), ("14", "DVDD", S4, "power_in"), ("15", "XDRVP", "MAG_XDRVP", "output"), ("16", "XINP", "MAG_XINP", "input"),
       ("17", "XINN", "MAG_XINN", "input"), ("18", "XDRVN", "MAG_XDRVN", "output"), ("19", "DVSS", GND, "power_in"), ("20", "RES", GND, "passive"),
       ("21", "NC", "", "passive"), ("22", "I2CEN", S4, "input"), ("23", "DRDY", "", "output"), ("24", "NC", "", "passive"),
       ("25", "REXT", "MAG_REXT", "passive"), ("26", "DVDD", S4, "power_in"), ("27", "SCL", "I2C4_SCL_FMU", "input"), ("28", "SA1", GND, "input")],
      "RM3100 controller, I2C addr 0x20 (SA1=SA0=0). Pinout: PNI RM3100 user manual table 4-1; MLF 4x4 mm 0.4 mm pitch, do not solder the die pad", "ic"),
    two("L1", "PNI Sen-XY-f (X)", "gen:SENXY", "F", 15.5, 2.6, 0, "MAG_XINP", "MAG_XINN", "X coil"),
    two("L2", "PNI Sen-XY-f (Y)", "gen:SENXY", "F", 15.8, 13.6, 90, "MAG_YINP", "MAG_YINN", "Y coil, 90 deg to X"),
    two("L3", "PNI Sen-Z-f (Z)", "gen:SENZ", "F", 12.5, 12.3, 0, "MAG_ZINP", "MAG_ZINN", "Z coil; polarity mark toward the tail"),
    two("R11", "121", "lib:R_0402_1005Metric", "F", 18.0, 4.5, 90, "MAG_XDRVP", "MAG_XINP", "bias"),
    two("R12", "121", "lib:R_0402_1005Metric", "F", 19.2, 4.5, 90, "MAG_XINN", "MAG_XDRVN", "bias"),
    two("R13", "121", "lib:R_0402_1005Metric", "F", 18.0, 10.0, 90, "MAG_YDRVP", "MAG_YINP", "bias"),
    two("R14", "121", "lib:R_0402_1005Metric", "F", 19.2, 10.0, 90, "MAG_YINN", "MAG_YDRVN", "bias"),
    two("R15", "121", "lib:R_0402_1005Metric", "F", 11.0, 9.2, 90, "MAG_ZDRVP", "MAG_ZINP", "bias"),
    two("R16", "121", "lib:R_0402_1005Metric", "F", 10.0, 9.2, 90, "MAG_ZINN", "MAG_ZDRVN", "bias"),
    two("R17", "33k", "lib:R_0402_1005Metric", "F", 17.2, 8.5, 0, "MAG_REXT", GND, "MagI2C clock resistor"),
    P("U4", "ICP-20100", "gen:LGA10-ICP", "F", 8.6, 13.5, 0,
      [("1", "CSB", S4, "input"), ("2", "SCL", "I2C4_SCL_FMU", "input"), ("3", "VSS", GND, "power_in"), ("4", "SDA", "I2C4_SDA_FMU", "bidirectional"),
       ("5", "VDD", S4, "power_in"), ("6", "SDO/AD0", S4, "input"), ("7", "INT", "", "output"), ("8", "RESV", GND, "passive"), ("9", "RESV", GND, "passive"),
       ("10", "VDDIO", S4, "power_in")],
      "baro 1, I2C4 addr 0x64 (AD0 high). Pinout: TDK DS-000416", "ic"),
    P("U5", "24LC64", "lib:SOIC-8_3.9x4.9mm_P1.27mm", "B", 10.1, 5.7, 0,
      [("1", "A0", GND, "input"), ("2", "A1", GND, "input"), ("3", "A2", GND, "input"), ("4", "VSS", GND, "power_in"),
       ("5", "SDA", "I2C4_SDA_FMU", "bidirectional"), ("6", "SCL", "I2C4_SCL_FMU", "input"), ("7", "WP", GND, "input"), ("8", "VCC", S4, "power_in")],
      "calibration EEPROM, I2C4 0x50", "ic"),
    P("Q1", "AO3400A", "lib:SOT-23", "B", 5.6, 9.2, 0,
      [("1", "G", "HEATER", "input"), ("2", "S", GND, "passive"), ("3", "D", "HEATER_SW", "passive")], "heater low-side switch (marked 3400)", "ic"),
    two("R1", "470", "lib:R_0805_2012Metric", "B", 21.9, 4.3, 0, V5, "HEATER_SW", "heater"),
    two("R2", "470", "lib:R_0805_2012Metric", "B", 3.3, 3.7, 0, V5, "HEATER_SW", "heater"),
    two("R3", "470", "lib:R_0805_2012Metric", "B", 21.9, 13.7, 0, V5, "HEATER_SW", "heater"),
    two("R4", "470", "lib:R_0805_2012Metric", "B", 3.3, 13.3, 0, V5, "HEATER_SW", "heater"),
    two("R5", "100k", "lib:R_0402_1005Metric", "B", 5.6, 11.5, 0, "HEATER", GND, "gate pull-down"),
    two("C1", "100n", "lib:C_0402_1005Metric", "F", 6.5, 3.0, 90, S3, GND),
    two("C2", "100n", "lib:C_0402_1005Metric", "F", 6.5, 5.5, 90, S3, GND),
    two("C3", "100n", "lib:C_0402_1005Metric", "F", 5.5, 8.8, 90, S2, GND),
    two("C4", "100n", "lib:C_0402_1005Metric", "F", 11.0, 8.8, 90, S2, GND),
    two("C5", "100n", "lib:C_0402_1005Metric", "F", 12.0, 3.5, 90, S4, GND),
    two("C6", "10u", "lib:C_0603_1608Metric", "F", 17.6, 6.5, 90, S4, GND, "MagI2C AVDD bulk (PNI ref. design)"),
    two("C7", "100n", "lib:C_0402_1005Metric", "F", 6.0, 13.5, 90, S4, GND),
    two("C8", "100n", "lib:C_0402_1005Metric", "B", 12.5, 3.0, 0, S4, GND),
    two("C9", "10u", "lib:C_0603_1608Metric", "B", 12.5, 15.5, 0, V5, GND, "heater rail bulk"),
]


def netlist(parts):
    """set of net names used by a parts list"""
    nets = set()
    for p in parts:
        for pad, name, net, et in p["pins"]:
            if net:
                nets.add(net)
    return nets


if __name__ == "__main__":
    for nm, parts in (("FMUM", FMUM_PARTS), ("IMU", IMU_PARTS)):
        print(nm, len(parts), "parts,", len(netlist(parts)), "nets")
    u1 = [p for p in FMUM_PARTS if p["ref"] == "U1"][0]
    print("U1 balls:", len(u1["pins"]), "connected:", sum(1 for p in u1["pins"] if p[2]))
