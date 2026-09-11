#!/usr/bin/env python3
"""
Generate a KiCad 8 project of the reverse-engineered CUAV V6X FMUM schematic
from the same tables that drive gen_schematic.py.

Output (folder kicad/):
  cuav_v6x_fmum.kicad_pro       project file (open this one)
  cuav_v6x_fmum.kicad_sch       root sheet with five hierarchical sheets
  01_mcu.kicad_sch              U1 with every used pin, net via global labels
  02_bus_connectors.kicad_sch   X1, X2, J3, J4
  03_power_sensors.kicad_sch    regulator, sensor LDOs, dividers, IMU3, BARO2
  04_core.kicad_sch             FRAM, SE050, crystals, LEDs, RTC cell, ID ladder, pull-ups
  05_imu_board.kicad_sch        the IMU board on the other end of the flex

Connectivity is carried entirely by global labels, so KiCad's netlist/ERC reflect
the tables in gen_schematic.py.  Symbols are self-contained (embedded in each file);
pin *numbers* of U1 are the port names (PA0 ...) because no ball map is included.
Swap U1 for the official KiCad "MCU_ST_STM32H7:STM32H743IIKx" symbol when you
assign footprints (pins are named identically, so a change-symbol by name works).
"""
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_schematic as G  # noqa: E402

OUT = os.path.join(HERE, "kicad")
PROJECT = "cuav_v6x_fmum"
NS = uuid.UUID("6f1c2a8e-3d4b-4e5f-9a0b-1c2d3e4f5a6b")
VERSION = "20231120"


def U(*key):
    return str(uuid.uuid5(NS, "|".join(str(k) for k in key)))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


FONT = "(effects (font (size 1.27 1.27)))"
FONT_H = "(effects (font (size 1.27 1.27)) (hide yes))"


# ---------------------------------------------------------------------------
# Library symbols
# pins: list of (number, name, etype) ; side "L" or "R"
# ---------------------------------------------------------------------------
class Sym:
    def __init__(self, name, ref, value, left, right, width=25.4, hide_numbers=False, footprint=""):
        self.name, self.ref, self.value = name, ref, value
        self.left, self.right, self.width = left, right, width
        self.hide_numbers = hide_numbers
        self.footprint = footprint
        n = max(len(left), len(right))
        self.h = (n + 1) * 2.54
        self.top = (n - 1) * 1.27  # y of first pin (lib coords, +y up)

    def pin_pos(self, side, i):
        """lib-coordinates of the pin connection point"""
        y = self.top - i * 2.54
        if side == "L":
            return (-self.width / 2 - 2.54, y, 0)
        return (self.width / 2 + 2.54, y, 180)

    def sexp(self):
        lid = f"FMUM:{self.name}"
        o = [f"(symbol {q(lid)} (pin_names (offset 1.016))" + (" (pin_numbers hide)" if self.hide_numbers else "") +
             " (exclude_from_sim no) (in_bom yes) (on_board yes)"]
        o.append(f'(property "Reference" {q(self.ref)} (at 0 {f(self.h/2+1.27)} 0) {FONT})')
        o.append(f'(property "Value" {q(self.value)} (at 0 {f(-self.h/2-1.27)} 0) {FONT})')
        o.append(f'(property "Footprint" {q(self.footprint)} (at 0 0 0) {FONT_H})')
        o.append(f'(property "Datasheet" "" (at 0 0 0) {FONT_H})')
        o.append(f'(property "Description" "" (at 0 0 0) {FONT_H})')
        w2, h2 = self.width / 2, self.h / 2
        o.append(f'(symbol {q(self.name + "_0_1")} (rectangle (start {f(-w2)} {f(h2)}) (end {f(w2)} {f(-h2)}) '
                 f'(stroke (width 0.254) (type default)) (fill (type background))))')
        o.append(f'(symbol {q(self.name + "_1_1")}')
        for side, pins in (("L", self.left), ("R", self.right)):
            for i, (num, name, et) in enumerate(pins):
                x, y, a = self.pin_pos(side, i)
                o.append(f'(pin {et} line (at {f(x)} {f(y)} {a}) (length 2.54) '
                         f'(name {q(name)} {FONT}) (number {q(num)} {FONT}))')
        o.append("))")
        return "\n".join(o)


class RSym(Sym):
    """two-terminal vertical part (resistor / capacitor / crystal / LED / cell)"""

    def __init__(self, name, ref, value, kind="R"):
        Sym.__init__(self, name, ref, value, [], [], 2.032)
        self.kind = kind
        self.h = 5.08

    def pin_pos(self, side, i):
        return (0, 3.81, 270) if i == 0 else (0, -3.81, 90)

    def sexp(self):
        lid = f"FMUM:{self.name}"
        o = [f"(symbol {q(lid)} (pin_numbers hide) (pin_names (offset 0)) (exclude_from_sim no) (in_bom yes) (on_board yes)"]
        o.append(f'(property "Reference" {q(self.ref)} (at 2.54 1.27 0) {FONT})')
        o.append(f'(property "Value" {q(self.value)} (at 2.54 -1.27 0) {FONT})')
        o.append(f'(property "Footprint" "" (at 0 0 0) {FONT_H})')
        o.append(f'(property "Datasheet" "" (at 0 0 0) {FONT_H})')
        o.append(f'(property "Description" "" (at 0 0 0) {FONT_H})')
        if self.kind == "R":
            body = f'(rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))'
        elif self.kind == "C":
            body = ('(polyline (pts (xy -2.032 0.508) (xy 2.032 0.508)) (stroke (width 0.508) (type default)) (fill (type none)))'
                    '(polyline (pts (xy -2.032 -0.508) (xy 2.032 -0.508)) (stroke (width 0.508) (type default)) (fill (type none)))')
        elif self.kind == "D":  # LED / diode, anode on top
            body = ('(polyline (pts (xy -1.27 1.27) (xy 1.27 1.27) (xy 0 -1.27) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))'
                    '(polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))')
        elif self.kind == "Y":
            body = ('(rectangle (start -1.143 1.778) (end 1.143 -1.778) (stroke (width 0.254) (type default)) (fill (type none)))'
                    '(polyline (pts (xy -2.032 2.54) (xy 2.032 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))'
                    '(polyline (pts (xy -2.032 -2.54) (xy 2.032 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))')
        else:  # battery
            body = ('(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))'
                    '(polyline (pts (xy -1.016 -0.762) (xy 1.016 -0.762)) (stroke (width 0.762) (type default)) (fill (type none)))')
        o.append(f'(symbol {q(self.name + "_0_1")} {body})')
        o.append(f'(symbol {q(self.name + "_1_1")}')
        n1, n2 = ("A", "K") if self.kind == "D" else ("+", "-") if self.kind == "B" else ("1", "2")
        pl = 1.27 if self.kind in ("R",) else 1.27
        o.append(f'(pin passive line (at 0 3.81 270) (length {f(pl)}) (name {q(n1)} {FONT}) (number "1" {FONT}))')
        o.append(f'(pin passive line (at 0 -3.81 90) (length {f(pl)}) (name {q(n2)} {FONT}) (number "2" {FONT}))')
        o.append("))")
        return "\n".join(o)


# ---------------------------------------------------------------------------
# Sheet writer
# ---------------------------------------------------------------------------
class Sheet:
    def __init__(self, fname, root_uuid, sheet_uuid=None, paper="A3"):
        self.fname = fname
        self.uuid = sheet_uuid or U("file", fname)
        self.root_uuid = root_uuid
        self.path = f"/{root_uuid}" + (f"/{self.uuid}" if sheet_uuid else "")
        self.paper = paper
        self.syms = {}
        self.items = []
        self.refs = {}

    def place(self, sym, ref, x, y, nets, value=None, rot=0):
        """Place symbol `sym` at (x,y) [mm, sheet coords]; nets maps pin-number -> net name
        (None = leave open).  Adds a global label at every connected pin."""
        self.syms[sym.name] = sym
        lid = f"FMUM:{sym.name}"
        o = [f"(symbol (lib_id {q(lid)}) (at {f(x)} {f(y)} {rot}) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)"]
        o.append(f"(uuid {q(U(self.fname, 'sym', ref))})")
        o.append(f'(property "Reference" {q(ref)} (at {f(x)} {f(y - sym.h/2 - 1.27)} 0) {FONT})')
        o.append(f'(property "Value" {q(value or sym.value)} (at {f(x)} {f(y + sym.h/2 + 1.27)} 0) {FONT})')
        o.append(f'(property "Footprint" {q(sym.footprint)} (at {f(x)} {f(y)} 0) {FONT_H})')
        o.append(f'(property "Datasheet" "" (at {f(x)} {f(y)} 0) {FONT_H})')
        o.append(f'(property "Description" "" (at {f(x)} {f(y)} 0) {FONT_H})')
        pins = []
        if isinstance(sym, RSym):
            pins = [("1", (0, 3.81, 270)), ("2", (0, -3.81, 90))]
        else:
            for side, plist in (("L", sym.left), ("R", sym.right)):
                for i, (num, name, et) in enumerate(plist):
                    pins.append((num, sym.pin_pos(side, i)))
        for num, _ in pins:
            o.append(f'(pin {q(num)} (uuid {q(U(self.fname, "pin", ref, num))}))')
        o.append(f'(instances (project {q(PROJECT)} (path {q(self.path)} (reference {q(ref)}) (unit 1)))))')
        self.items.append("\n".join(o))
        # labels
        for num, (px, py, ang) in pins:
            net = nets.get(num)
            if not net:
                continue
            lx, ly = x + px, y - py  # lib +y is up, sheet +y is down
            if ang == 0:      # pin points right -> label to the left
                la, just = 180, "right"
            elif ang == 180:
                la, just = 0, "left"
            elif ang == 270:  # pin at top pointing down -> label above, vertical
                la, just = 90, "left"
            else:
                la, just = 270, "left"
            self.label(net, lx, ly, la, just, key=(ref, num))

    def label(self, net, x, y, ang=0, just="left", key=None):
        shape = "input" if net.startswith("GND") else "bidirectional"
        self.items.append(
            f"(global_label {q(net)} (shape {shape}) (at {f(x)} {f(y)} {ang}) (fields_autoplaced yes) "
            f"(effects (font (size 1.27 1.27)) (justify {just})) (uuid {q(U(self.fname, 'lbl', key or (net, x, y)))}) "
            f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {f(x)} {f(y)} 0) (effects (font (size 1.27 1.27)) (justify {just}) (hide yes))))')

    def text(self, s, x, y, size=1.5):
        self.items.append(f"(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid {q(U(self.fname, 'txt', s, x, y))}))")

    def header(self, generator="gen_kicad"):
        return [f"(kicad_sch (version {VERSION}) (generator {q(generator)}) (generator_version \"8.0\")",
                f"(uuid {q(self.uuid)})", f"(paper {q(self.paper)})"]

    def write(self, extra_items=(), root=False):
        o = self.header()
        o.append("(lib_symbols")
        for s in self.syms.values():
            o.append(s.sexp())
        o.append(")")
        o.extend(self.items)
        o.extend(extra_items)
        if root:
            o.append('(sheet_instances (path "/" (page "1")))')
        o.append(")")
        with open(os.path.join(OUT, self.fname), "w") as fh:
            fh.write("\n".join(o) + "\n")


# ---------------------------------------------------------------------------
# Sheet 1: MCU
# ---------------------------------------------------------------------------
def build_mcu(root_uuid, sheet_uuid):
    sh = Sheet("01_mcu.kicad_sch", root_uuid, sheet_uuid)
    port_pins = [p for p in G.PINS if p[0].startswith("P") and p[0][2:].isdigit()]
    extra = [p for p in G.PINS if p not in port_pins]
    left_ports, right_ports = ("PA", "PB", "PC", "PD"), ("PE", "PF", "PG", "PH", "PI")

    def etype(fn, net):
        fnl = fn.lower()
        if "adc" in fnl or "in" in fnl and "out" not in fnl or "rx" in fnl or "miso" in fnl or "vbus" in fnl or "osc" in fnl and "in" in fnl:
            return "input"
        if "out" in fnl or "tx" in fnl or "sck" in fnl or "mosi" in fnl or "ck" in fnl or "cmd" in fnl or "clk" in fnl or "ch" in fnl:
            return "output" if "capture" not in fnl else "input"
        return "bidirectional"

    left = [(p, p + "  " + fn, etype(fn, net)) for p, fn, net, d in port_pins if p[:2] in left_ports]
    right = [(p, fn + "  " + p, etype(fn, net)) for p, fn, net, d in port_pins if p[:2] in right_ports]
    # supply pins on the right, below
    supply_map = {"NRST": "input", "BOOT0": "input", "VBAT": "power_in", "PDR_ON": "input",
                  "VDD/VDDA/VDDUSB/VDDLDO": "power_in", "VCAP1/VCAP2": "passive", "VREF+": "power_in"}
    right += [(p, p, supply_map.get(p, "passive")) for p, fn, net, d in extra]
    u1 = Sym("STM32H743IIK6", "U", "STM32H743IIK6", left, right, width=76.2, hide_numbers=True,
             footprint="Package_BGA:ST_UFBGA-176_10x10mm_Layout15x15_P0.65mm")
    nets = {p: net for p, fn, net, d in G.PINS}
    nets["PD15"] = None  # spare, leave open
    nets["PI6"] = None   # BMI088 accel INT not wired on the flex
    sh.place(u1, "U1", 210, 148, nets)
    sh.text("U1 STM32H743IIK6 (STM32H753 for the crypto variant). Pin numbers = port names; assign the ST ball map via the KiCad library symbol MCU_ST_STM32H7:STM32H743IIKx.", 20, 285)
    sh.text("Every net is a global label; the same label on a connector or part pin on another sheet closes the connection.", 20, 289)
    sh.write()
    return sh


# ---------------------------------------------------------------------------
# Sheet 2: connectors
# ---------------------------------------------------------------------------
def build_connectors(root_uuid, sheet_uuid):
    sh = Sheet("02_bus_connectors.kicad_sch", root_uuid, sheet_uuid, paper="A2")

    def conn(name, table, nc=set(), width=17.78, foot=""):
        et = lambda n: "power_out" if n == "VDD_5V_IN" else "passive"
        left = [(str(p), table[p], et(table[p])) for p in sorted(table) if p % 2 == 1]
        right = [(str(p), table[p], et(table[p])) for p in sorted(table) if p % 2 == 0]
        s = Sym(name, "X", name, left, right, width, footprint=foot)
        nets = {str(p): (None if table[p] in nc else table[p]) for p in table}
        if name.startswith("DF40C-50"):
            nets["50"] = "FMU_CH3"  # DS-010 calls this pin 'PH11'; it is the FMU_CH3 pin
        return s, nets

    x1, n1 = conn("DF40C-100DP-0.4V", G.X1, width=20.32, foot="Connector_Hirose:Hirose_DF40C-100DP-0.4V_2x50_P0.40mm")
    sh.place(x1, "X1", 120, 200, n1)
    x2, n2 = conn("DF40C-50DP-0.4V", G.X2, G.X2_NC, width=20.32, foot="Connector_Hirose:Hirose_DF40C-50DP-0.4V_2x25_P0.40mm")
    sh.place(x2, "X2", 300, 130, n2)
    j3, n3 = conn("BM20B(0.8)-34DP-0.4V", G.J3, width=20.32)
    sh.place(j3, "J3", 300, 300, n3)
    # microSD
    sd = Sym("microSD", "J", "Molex 5031821852", [("1", "DAT2", "passive"), ("2", "CD/DAT3", "passive"), ("3", "CMD", "passive"),
                                                  ("4", "VDD", "power_in"), ("5", "CLK", "passive"), ("6", "VSS", "passive"),
                                                  ("7", "DAT0", "passive"), ("8", "DAT1", "passive")],
             [("9", "SHIELD", "passive")], width=17.78, footprint="Connector_Card:microSD_HC_Molex_503182-1852")
    sh.place(sd, "J4", 480, 130, {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "4": "VDD_3V3_SD", "5": "SD_CLK", "6": "GND", "7": "SD_D0", "8": "SD_D1", "9": "GND"})
    sh.text("X1/X2: Pixhawk Autopilot Bus (DS-010). Base side mates DF40HC(3.0)-100DS-0.4V(58) / DF40HC(3.0)-50DS-0.4V(51). J3: IMU flex (DS-012 p.17). Unlabelled X2 pins are reserved by the standard but unconnected on FMUv6X.", 20, 410)
    sh.write()
    return sh


# ---------------------------------------------------------------------------
# Sheet 3: power + on-module sensors
# ---------------------------------------------------------------------------
def build_power(root_uuid, sheet_uuid):
    sh = Sheet("03_power_sensors.kicad_sch", root_uuid, sheet_uuid)
    R = RSym("R", "R", "R", "R")
    C = RSym("C", "C", "C", "C")

    reg = Sym("Buck_3V3", "U", "3V3 step-down 1A", [("1", "VIN", "power_in"), ("2", "EN", "input"), ("3", "GND", "power_in")],
              [("4", "VOUT", "power_out")], 20.32)
    sh.place(reg, "U2", 60, 40, {"1": "VDD_5V_IN", "2": "VDD_5V_IN", "3": "GND", "4": "FMU_VDD_3V3"}, "TPS62A01 (substitute)")
    ldo = Sym("LDO_3V3_EN", "U", "LDO 3V3 300mA EN", [("1", "VIN", "power_in"), ("2", "EN", "input"), ("3", "GND", "power_in")],
              [("4", "VOUT", "power_out")], 20.32, footprint="Package_TO_SOT_SMD:SOT-23-5")
    doms = [("U3", "VDD_3V3_SENSORS1_EN", "VDD_3V3_SENSORS1", "SCALED_VDD_3V3_SENSORS1"),
            ("U4", "VDD_3V3_SENSORS2_EN", "VDD_3V3_SENSORS2", "SCALED_VDD_3V3_SENSORS2"),
            ("U5", "VDD_3V3_SENSORS3_EN", "VDD_3V3_SENSORS3", "SCALED_VDD_3V3_SENSORS3"),
            ("U6", "VDD_3V3_SENSORS4_EN", "VDD_3V3_SENSORS4", "SCALED_VDD_3V3_SENSORS4")]
    rn = 1
    for i, (ref, en, rail, sense) in enumerate(doms):
        y = 80 + i * 40
        sh.place(ldo, ref, 60, y, {"1": "VDD_5V_IN", "2": en, "3": "GND", "4": rail}, "TLV75533 (substitute)")
        sh.place(R, f"R{rn}", 120, y - 8, {"1": rail, "2": sense}, "10k"); rn += 1
        sh.place(R, f"R{rn}", 120, y + 8, {"1": sense, "2": "GND"}, "10k"); rn += 1
    # V5 sense
    sh.place(R, f"R{rn}", 160, 72, {"1": "VDD_5V_IN", "2": "SCALED_V5"}, "10k"); rn += 1
    sh.place(R, f"R{rn}", 160, 88, {"1": "SCALED_V5", "2": "GND"}, "10k"); rn += 1
    # SD load switch
    sw = Sym("LoadSwitch", "U", "load switch", [("1", "VIN", "power_in"), ("2", "EN", "input"), ("3", "GND", "power_in")], [("4", "VOUT", "power_out")], 20.32)
    sh.place(sw, "U7", 60, 250, {"1": "FMU_VDD_3V3", "2": "VDD_3V3_SD_CARD_EN", "3": "GND", "4": "VDD_3V3_SD"}, "TPS22918 (substitute)")
    # IMU3
    imu = Sym("ICM-20649", "U", "ICM-20649", [("1", "nCS", "input"), ("2", "SCLK", "input"), ("3", "SDI", "input"), ("4", "SDO/AD0", "output"), ("5", "INT1", "output"), ("6", "GND", "power_in")],
              [("7", "VDD", "power_in"), ("8", "VDDIO", "power_in"), ("9", "REGOUT", "passive"), ("10", "FSYNC", "input")], 25.4,
              footprint="Package_DFN_QFN:QFN-24-1EP_3x3mm_P0.4mm_EP1.7x1.7mm")
    sh.place(imu, "U8", 260, 60, {"1": "SPI1_nCS1_IMU3", "2": "SPI1_SCK_SENSOR1", "3": "SPI1_MOSI_SENSOR1", "4": "SPI1_MISO_SENSOR1",
                                  "5": "SPI1_DRDY1_IMU3_INT1", "6": "GND", "7": "VDD_3V3_SENSORS1", "8": "VDD_3V3_SENSORS1", "9": "IMU3_REGOUT", "10": "GND"})
    sh.place(C, "C1", 330, 60, {"1": "IMU3_REGOUT", "2": "GND"}, "100n")
    # BARO2
    baro = Sym("ICP-20100", "U", "ICP-20100", [("1", "SDA", "bidirectional"), ("2", "SCL", "input"), ("3", "INT", "output"), ("4", "GND", "power_in")],
               [("5", "VDD", "power_in"), ("6", "VDDIO", "power_in"), ("7", "AD0", "input"), ("8", "CSB", "input")], 25.4)
    sh.place(baro, "U9", 260, 130, {"1": "I2C2_SDA_BASE", "2": "I2C2_SCL_BASE", "3": "I2C2_DRDY1_BARO2", "4": "GND",
                                    "5": "VDD_3V3_SENSORS2", "6": "VDD_3V3_SENSORS2", "7": "GND", "8": "FMU_VDD_3V3"})
    # I2C pull-ups
    y = 200
    for k, net in enumerate(["I2C1_SCL_BASE", "I2C1_SDA_BASE", "I2C2_SCL_BASE", "I2C2_SDA_BASE", "I2C3_SCL_BASE", "I2C3_SDA_BASE", "I2C4_SCL_FMU", "I2C4_SDA_FMU"]):
        sh.place(R, f"R{rn}", 230 + k * 22, y, {"1": "FMU_VDD_3V3", "2": net}, "1k5"); rn += 1
    sh.text("I2C pull-ups 1.5k to FMU_VDD_3V3 on the module (DS-010 requirement).", 220, 215)
    # decoupling (representative)
    for k, (net, val) in enumerate([("FMU_VDD_3V3", "4u7"), ("FMU_VDD_3V3", "100n"), ("VCAP", "2u2"), ("VCAP", "2u2"), ("VDD_5V_IN", "10u"), ("VDD_5V_IN", "10u"),
                                    ("VDD_3V3_SENSORS1", "1u"), ("VDD_3V3_SENSORS2", "1u"), ("VDD_3V3_SENSORS3", "1u"), ("VDD_3V3_SENSORS4", "1u")]):
        sh.place(C, f"C{k+2}", 230 + k * 18, 250, {"1": net, "2": "GND"}, val)
    sh.text("Representative decoupling. Add 100 nF per VDD ball of U1 (about 20) at layout time.", 220, 265)
    sh.text("HEATER (PB10) goes straight to J3-30; MOSFET and heating resistors are on the IMU board.", 20, 285)
    sh.write()
    return sh


# ---------------------------------------------------------------------------
# Sheet 4: core
# ---------------------------------------------------------------------------
def build_core(root_uuid, sheet_uuid):
    sh = Sheet("04_core.kicad_sch", root_uuid, sheet_uuid)
    R = RSym("R", "R", "R", "R")
    C = RSym("C", "C", "C", "C")
    D = RSym("LED", "D", "LED", "D")
    Y = RSym("Crystal", "Y", "Crystal", "Y")
    B = RSym("Battery", "BT", "Battery", "B")
    fram = Sym("FM25V02A", "U", "FM25V02A", [("1", "nCS", "input"), ("2", "SO", "output"), ("3", "nWP", "input"), ("4", "VSS", "power_in")],
               [("8", "VDD", "power_in"), ("7", "nHOLD", "input"), ("6", "SCK", "input"), ("5", "SI", "input")], 22.86,
               footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    sh.place(fram, "U10", 60, 40, {"1": "SPI5_nCS1_FRAM", "2": "SPI5_MISO_FRAM", "3": "FMU_VDD_3V3", "4": "GND",
                                   "8": "FMU_VDD_3V3", "7": "FMU_VDD_3V3", "6": "SPI5_SCK_FRAM", "5": "SPI5_MOSI_FRAM"})
    se = Sym("SE050", "U", "SE050C1", [("1", "SDA", "bidirectional"), ("2", "SCL", "input"), ("3", "ENA", "input"), ("4", "GND", "power_in")],
             [("5", "VDD", "power_in"), ("6", "VIN", "power_in")], 22.86)
    sh.place(se, "U11", 60, 90, {"1": "I2C4_SDA_FMU", "2": "I2C4_SCL_FMU", "3": "FMU_VDD_3V3", "4": "GND", "5": "FMU_VDD_3V3", "6": "FMU_VDD_3V3"})
    # crystals
    sh.place(Y, "Y1", 160, 40, {"1": "16MHZ_IN", "2": "16MHZ_OUT"}, "16MHz")
    sh.place(C, "C20", 175, 34, {"1": "16MHZ_IN", "2": "GND"}, "10p")
    sh.place(C, "C21", 175, 48, {"1": "16MHZ_OUT", "2": "GND"}, "10p")
    sh.place(Y, "Y2", 200, 40, {"1": "32KHZ_IN", "2": "32KHZ_OUT"}, "32.768kHz")
    sh.place(C, "C22", 215, 34, {"1": "32KHZ_IN", "2": "GND"}, "6p8")
    sh.place(C, "C23", 215, 48, {"1": "32KHZ_OUT", "2": "GND"}, "6p8")
    # RTC cell + charge path
    sh.place(B, "BT1", 160, 90, {"1": "V_RTC_BAT", "2": "GND"}, "MS621FE")
    sh.place(R, "R30", 180, 90, {"1": "RTC_CHG", "2": "V_RTC_BAT"}, "1k")
    dchg = RSym("Diode", "D", "BAT54", "D")
    sh.place(dchg, "D4", 200, 90, {"1": "FMU_VDD_3V3", "2": "RTC_CHG"}, "BAT54")
    # LEDs
    for k, (ref, net, col) in enumerate([("D1", "nLED_RED", "red"), ("D2", "nLED_GREEN", "green"), ("D3", "nLED_BLUE", "blue")]):
        x = 250 + k * 20
        sh.place(D, ref, x, 40, {"1": "FMU_VDD_3V3", "2": f"LED_{col.upper()}_K"}, f"LED {col}")
        sh.place(R, f"R{31+k}", x, 56, {"1": f"LED_{col.upper()}_K", "2": net}, "470")
    # HW ID ladder
    sh.place(R, "R40", 160, 140, {"1": "HW_VER_REV_DRIVE", "2": "HW_REV_SENSE"}, "24k9")
    sh.place(R, "R41", 160, 156, {"1": "HW_REV_SENSE", "2": "GND"}, "442k")
    sh.text("Module ID ladder: 24.9k / 442k = ID 1 (PX4 V6X001, CUAV sensor set rev 1)", 150, 168)
    # BOOT0 / NRST
    sh.place(R, "R42", 250, 140, {"1": "BOOT0", "2": "GND"}, "10k")
    sh.place(C, "C24", 270, 140, {"1": "FMU_nRST", "2": "GND"}, "100n")
    tr = Sym("TRACE_pads", "J", "TRACE pads (unpopulated)", [("1", "TRACECLK", "passive"), ("3", "TRACED0", "passive"), ("5", "TRACED1", "passive"),
                                                          ("7", "TRACED2", "passive"), ("8", "TRACED3", "passive"), ("2", "GND", "passive")], [], 22.86)
    sh.place(tr, "J1", 60, 150, {"1": "TRACECLK", "3": "nLED_RED", "5": "nLED_GREEN", "7": "nLED_BLUE", "8": "nARMED", "2": "GND"})
    sh.text("BOOT0 pad 'BT0' and 10k pull-down; NRST 100 nF. Trace pads J1: TRACECLK PE2, TRACED0-3 PE3-PE6 (unpopulated).", 150, 180)
    sh.write()
    return sh



# ---------------------------------------------------------------------------
# Sheet 5: IMU board (V6X IMU RC10)
# ---------------------------------------------------------------------------
def build_imu(root_uuid, sheet_uuid):
    sh = Sheet("05_imu_board.kicad_sch", root_uuid, sheet_uuid)
    R = RSym("R", "R", "R", "R")
    C = RSym("C", "C", "C", "C")
    L = RSym("Coil", "L", "Coil", "R")
    parts = {p[0]: p for p in G.IMU_PARTS}

    def box(ref, split, width=25.4, foot="", etypes=None):
        r, part, pkg, pins = parts[ref]
        et = etypes or {}
        left = [(pn, pn, et.get(pn, "passive")) for pn, net in pins[:split]]
        right = [(pn, pn, et.get(pn, "passive")) for pn, net in pins[split:]]
        sym = Sym(ref + "_" + part.split()[1].replace("/", "-"), "U", part.split(" (")[0], left, right, width, footprint=foot)
        return sym, {pn: (net or None) for pn, net in pins}

    # mating connector, same numbering as J3
    et = lambda n: "power_out" if n in G.POWER_NETS else "passive"
    left = [(str(p), G.J3[p], et(G.J3[p])) for p in sorted(G.J3) if p % 2 == 1]
    right = [(str(p), G.J3[p], et(G.J3[p])) for p in sorted(G.J3) if p % 2 == 0]
    j1 = Sym("BM20B(0.8)-34DS-0.4V", "J", "BM20B(0.8)-34DS-0.4V", left, right, 20.32)
    sh.place(j1, "J1", 50, 80, {str(p): G.J3[p] for p in G.J3})

    sym, nets = box("U1", 9, 30.48, "Package_LGA:Bosch_LGA-16_3x4.5mm_P0.5mm")
    sh.place(sym, "U1", 150, 50, nets)
    sym, nets = box("U2", 7, 30.48, "Package_LGA:InvenSense_LGA-14_2.5x3mm_P0.5mm")
    sh.place(sym, "U2", 150, 110, nets)
    sym, nets = box("U3", 9, 30.48, "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm")
    sh.place(sym, "U3", 260, 50, nets)
    for k, ref in enumerate(("L1", "L2", "L3")):
        r, part, pkg, pins = parts[ref]
        sh.place(L, ref, 320 + k * 15, 50, {"1": pins[0][1], "2": pins[1][1]}, part.split(" coil")[0])
    sym, nets = box("U4", 5, 30.48)
    sh.place(sym, "U4", 260, 120, nets)
    sym, nets = box("U5", 6, 27.94, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    sh.place(sym, "U5", 260, 175, nets)
    # heater
    q = Sym("NMOS_SOT23", "Q", "AO3400", [("G", "G", "input")], [("D", "D", "passive"), ("S", "S", "passive")], 12.7,
            footprint="Package_TO_SOT_SMD:SOT-23")
    sh.place(q, "Q1", 150, 190, {"G": "HEATER", "D": "HEATER_SW", "S": "GND"})
    for k in range(4):
        sh.place(R, f"R{k+1}", 185 + k * 12, 175, {"1": "VDD_5V_IN", "2": "HEATER_SW"}, "470")
    sh.place(R, "R5", 130, 200, {"1": "HEATER", "2": "GND"}, "100k")
    for k, (net, val) in enumerate([("VDD_3V3_SENSORS3", "100n"), ("VDD_3V3_SENSORS3", "100n"), ("VDD_3V3_SENSORS2", "100n"), ("VDD_3V3_SENSORS2", "100n"),
                                    ("VDD_3V3_SENSORS4", "100n"), ("VDD_3V3_SENSORS4", "1u"), ("VDD_5V_IN", "10u")]):
        sh.place(C, f"C{k+1}", 150 + k * 15, 240, {"1": net, "2": "GND"}, val)
    sh.text("IMU board 'V6X IMU RC10' (2022-09-20), other end of the FPC from FMUM J3. No regulators here: rails SENSORS2/3/4 and VDD_5V_IN arrive over the flex.", 20, 280)
    sh.text("RM3100 = U3 MagI2C + L1/L2 Sen-XY-f + L3 Sen-Z-f. Heater: 4 x 470 R (marked 4700) low-side switched by Q1 (marked 3400).", 20, 285)
    sh.write()
    return sh

# ---------------------------------------------------------------------------
# Root sheet + project
# ---------------------------------------------------------------------------
def build_root(children):
    root_uuid = U("root")
    sh = Sheet(f"{PROJECT}.kicad_sch", root_uuid, None, paper="A4")
    sh.uuid = root_uuid
    items = []
    x, y = 25.4, 30
    for page, (title, child, cu) in enumerate(children, start=2):
        items.append(
            f"(sheet (at {f(x)} {f(y)}) (size 60 25) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0)) "
            f"(uuid {q(cu)}) "
            f'(property "Sheetname" {q(title)} (at {f(x)} {f(y-0.8)} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) '
            f'(property "Sheetfile" {q(child)} (at {f(x)} {f(y+25.6)} 0) (effects (font (size 1.27 1.27)) (justify left top))) '
            f"(instances (project {q(PROJECT)} (path {q('/' + root_uuid)} (page {q(str(page))})))))")
        y += 40
    sh.text("CUAV V6X FMUM (Pixhawk FMUv6X module) — reverse-engineered schematic. Not vendor data.", 100, 40, 2.0)
    sh.text("Sources: PX4 boards/px4/fmu-v6x board files (HW type V6X001), Pixhawk DS-010 / DS-012.", 100, 46)
    sh.text("All connectivity via global labels; ERC will flag the intentionally open X2 spare pins.", 100, 52)
    sh.write(items, root=True)
    pro = {
        "board": {"design_settings": {}, "layer_presets": [], "viewports": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.2, "track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3,
                                      "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "microvia_diameter": 0.3,
                                      "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12, "pcb_color": "rgba(0, 0, 0, 0.000)",
                                      "schematic_color": "rgba(0, 0, 0, 0.000)", "line_style": 0}], "meta": {"version": 3}, "net_colors": None,
                         "netclass_assignments": None, "netclass_patterns": []},
        "pcbnew": {"page_layout_descr_file": ""},
        "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0, "label_size_ratio": 0.375, "pin_symbol_size": 25.0, "text_offset_ratio": 0.15},
                      "legacy_lib_dir": "", "legacy_lib_list": [], "meta": {"version": 1}},
        "sheets": [[root_uuid, "Root"]] + [[cu, title] for title, child, cu in children],
        "text_variables": {},
    }
    with open(os.path.join(OUT, f"{PROJECT}.kicad_pro"), "w") as fh:
        json.dump(pro, fh, indent=2)
    return root_uuid


def main():
    os.makedirs(OUT, exist_ok=True)
    root_uuid = U("root")
    children = [("MCU", "01_mcu.kicad_sch", U("sheet", "mcu")),
                ("Bus connectors", "02_bus_connectors.kicad_sch", U("sheet", "conn")),
                ("Power and sensors", "03_power_sensors.kicad_sch", U("sheet", "power")),
                ("Core peripherals", "04_core.kicad_sch", U("sheet", "core")),
                ("IMU board (flex)", "05_imu_board.kicad_sch", U("sheet", "imu"))]
    build_mcu(root_uuid, children[0][2])
    build_connectors(root_uuid, children[1][2])
    build_power(root_uuid, children[2][2])
    build_core(root_uuid, children[3][2])
    build_imu(root_uuid, children[4][2])
    build_root(children)
    for fn in sorted(os.listdir(OUT)):
        print("wrote kicad/" + fn)


if __name__ == "__main__":
    main()
