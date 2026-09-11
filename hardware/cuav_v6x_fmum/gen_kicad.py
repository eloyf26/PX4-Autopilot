#!/usr/bin/env python3
"""
Generate the two KiCad 8 schematic projects (FMU module, IMU board) from parts.py.

  kicad/fmum/cuav_v6x_fmum.kicad_pro   root + 4 hierarchical sheets
  kicad/imu/cuav_v6x_imu.kicad_pro     root + 1 sheet

Symbols are generated with the REAL package pin numbers (ball names for U1),
so they match the footprints that gen_pcb.py places.  Connectivity is carried
by global labels; every part pin with a net gets one.  Run gen_pcb.py after
this to produce the boards.
"""
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts as PR  # noqa: E402

NS = uuid.UUID("6f1c2a8e-3d4b-4e5f-9a0b-1c2d3e4f5a6b")
VERSION = "20231120"
FONT = "(effects (font (size 1.27 1.27)))"
FONT_H = "(effects (font (size 1.27 1.27)) (hide yes))"


def U(*key):
    return str(uuid.uuid5(NS, "|".join(str(k) for k in key)))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


FP_LIB = {  # parts.py footprint key -> KiCad footprint id written into the symbol
    "gen:UFBGA176": "FMUM:ST_UFBGA-176+25_10x10mm_Layout15x15_P0.65mm",
    "gen:DF40-100": "FMUM:Hirose_DF40C-100DP-0.4V", "gen:DF40-50": "FMUM:Hirose_DF40C-50DP-0.4V",
    "gen:BM20-34": "FMUM:Hirose_BM20B-34-0.4V", "gen:LGA10-ICP": "FMUM:TDK_LGA-10_2x2mm_P0.5mm",
    "gen:LGA16-BMI088": "FMUM:Bosch_LGA-16_4.5x3mm_P0.5mm", "gen:QFN28-MAGI2C": "FMUM:PNI_MLF-28_4x4mm_P0.4mm",
    "gen:SENXY": "FMUM:PNI_Sen-XY-f", "gen:SENZ": "FMUM:PNI_Sen-Z-f", "gen:MS621": "FMUM:Seiko_MS621FE",
    "gen:SOD323": "FMUM:D_SOD-323", "gen:TP": "FMUM:TestPad_1.0mm", "gen:TRACE": "FMUM:TRACE_8+2",
}
LIB_DIRS = {"SOIC": "Package_SO", "TSSOP": "Package_SO", "QFN": "Package_DFN_QFN", "LGA": "Package_LGA", "SOT": "Package_TO_SOT_SMD",
            "R_": "Resistor_SMD", "C_": "Capacitor_SMD", "LED": "LED_SMD", "Crystal": "Crystal", "microSD": "Connector_Card", "L_": "Inductor_SMD"}


def fp_id(key):
    if key in FP_LIB:
        return FP_LIB[key]
    name = key.split(":", 1)[1]
    for pre, lib in LIB_DIRS.items():
        if name.startswith(pre):
            return f"{lib}:{name}"
    return "FMUM:" + name


# ---------------------------------------------------------------------------
# symbol geometry
# ---------------------------------------------------------------------------
class Sym:
    """Box symbol. left/right: lists of (pad, name, etype)."""

    def __init__(self, name, left, right, width, value, footprint, hide_numbers=False):
        self.name, self.left, self.right, self.width = name, left, right, width
        self.value, self.footprint, self.hide_numbers = value, footprint, hide_numbers
        n = max(len(left), len(right), 1)
        self.h = (n + 1) * 2.54
        self.top = (n - 1) * 1.27

    def pin_pos(self, side, i):
        y = self.top - i * 2.54
        return (-self.width / 2 - 2.54, y, 0) if side == "L" else (self.width / 2 + 2.54, y, 180)

    def pins(self):
        out = []
        for side, pl in (("L", self.left), ("R", self.right)):
            for i, (pad, name, et) in enumerate(pl):
                out.append((pad, name, et, self.pin_pos(side, i)))
        return out

    def sexp(self):
        o = [f"(symbol {q('FMUM:' + self.name)} (pin_names (offset 1.016))" + (" (pin_numbers hide)" if self.hide_numbers else "") + " (exclude_from_sim no) (in_bom yes) (on_board yes)"]
        o.append(f'(property "Reference" "U" (at 0 {f(self.h/2+1.27)} 0) {FONT})')
        o.append(f'(property "Value" {q(self.value)} (at 0 {f(-self.h/2-1.27)} 0) {FONT})')
        o.append(f'(property "Footprint" {q(self.footprint)} (at 0 0 0) {FONT_H})')
        o.append(f'(property "Datasheet" "" (at 0 0 0) {FONT_H})')
        o.append(f'(property "Description" "" (at 0 0 0) {FONT_H})')
        w2, h2 = self.width / 2, self.h / 2
        o.append(f'(symbol {q(self.name + "_0_1")} (rectangle (start {f(-w2)} {f(h2)}) (end {f(w2)} {f(-h2)}) (stroke (width 0.254) (type default)) (fill (type background))))')
        o.append(f'(symbol {q(self.name + "_1_1")}')
        for pad, name, et, (x, y, a) in self.pins():
            o.append(f'(pin {et} line (at {f(x)} {f(y)} {a}) (length 2.54) (name {q(name)} {FONT}) (number {q(pad)} {FONT}))')
        o.append("))")
        return "\n".join(o)


class TwoPin(Sym):
    """vertical 2-terminal symbol (R, C, L, LED, crystal, cell, diode, test pad)"""
    KIND = {"R": "R", "C": "C", "L": "L", "D": "D", "Y": "Y", "BT": "B", "TP": "T"}

    def __init__(self, name, kind, value, footprint, pads=("1", "2"), names=("1", "2")):
        Sym.__init__(self, name, [], [], 2.032, value, footprint, True)
        self.kind, self.padnums, self.pinnames = kind, pads, names
        self.h = 5.08

    def pins(self):
        out = [(self.padnums[0], self.pinnames[0], "passive", (0, 3.81, 270))]
        if len(self.padnums) > 1:
            out.append((self.padnums[1], self.pinnames[1], "passive", (0, -3.81, 90)))
        return out

    def sexp(self):
        body = {
            "R": '(rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))',
            "C": '(polyline (pts (xy -2.032 0.508) (xy 2.032 0.508)) (stroke (width 0.508) (type default)) (fill (type none)))(polyline (pts (xy -2.032 -0.508) (xy 2.032 -0.508)) (stroke (width 0.508) (type default)) (fill (type none)))',
            "L": '(arc (start 0 2.54) (mid 0.8 1.27) (end 0 0) (stroke (width 0.254) (type default)) (fill (type none)))(arc (start 0 0) (mid 0.8 -1.27) (end 0 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))',
            "D": '(polyline (pts (xy -1.27 1.27) (xy 1.27 1.27) (xy 0 -1.27) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))(polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
            "Y": '(rectangle (start -1.143 1.778) (end 1.143 -1.778) (stroke (width 0.254) (type default)) (fill (type none)))(polyline (pts (xy -2.032 2.54) (xy 2.032 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))(polyline (pts (xy -2.032 -2.54) (xy 2.032 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))',
            "B": '(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))(polyline (pts (xy -1.016 -0.762) (xy 1.016 -0.762)) (stroke (width 0.762) (type default)) (fill (type none)))',
            "T": '(circle (center 0 2.54) (radius 0.762) (stroke (width 0.254) (type default)) (fill (type none)))',
        }[self.kind]
        o = [f"(symbol {q('FMUM:' + self.name)} (pin_numbers hide) (pin_names (offset 0)) (exclude_from_sim no) (in_bom yes) (on_board yes)"]
        o.append(f'(property "Reference" "R" (at 2.54 1.27 0) {FONT})')
        o.append(f'(property "Value" {q(self.value)} (at 2.54 -1.27 0) {FONT})')
        o.append(f'(property "Footprint" {q(self.footprint)} (at 0 0 0) {FONT_H})')
        o.append(f'(property "Datasheet" "" (at 0 0 0) {FONT_H})')
        o.append(f'(property "Description" "" (at 0 0 0) {FONT_H})')
        o.append(f'(symbol {q(self.name + "_0_1")} {body})')
        o.append(f'(symbol {q(self.name + "_1_1")}')
        for pad, name, et, (x, y, a) in self.pins():
            o.append(f'(pin passive line (at {f(x)} {f(y)} {a}) (length 1.27) (name {q(name)} {FONT}) (number {q(pad)} {FONT}))')
        o.append("))")
        return "\n".join(o)


def make_symbol(part):
    """Build the symbol for a parts.py entry."""
    ref, pins = part["ref"], part["pins"]
    fp = fp_id(part["fp"])
    con = [p for p in pins if p[2]] if ref == "U1" else pins
    prefix = ref.rstrip("0123456789")
    name = f"{ref}_{part['value']}".replace(" ", "_").replace("/", "-").replace("(", "").replace(")", "")
    if prefix == "TP":
        return TwoPin(name, "T", part["value"], fp, (pins[0][0],), (pins[0][1],))
    if len(pins) == 2 and prefix in TwoPin.KIND:
        return TwoPin(name, TwoPin.KIND[prefix], part["value"], fp, (pins[0][0], pins[1][0]), (pins[0][1], pins[1][1]))
    if ref == "U1":
        ports_l, ports_r = ("PA", "PB", "PC", "PD"), ("PE", "PF", "PG", "PH", "PI")

        def key(p):
            n = p[1][2:].split("-")[0]
            return (p[1][:2], int(n) if n.isdigit() else 0)
        L = sorted([p for p in con if p[1][:2] in ports_l], key=key)
        R = sorted([p for p in con if p[1][:2] in ports_r], key=key)
        sup = sorted([p for p in con if p[1][:2] not in ports_l + ports_r], key=lambda p: (p[1], p[0]))
        (L if len(L) <= len(R) else R).extend(sup)
        return Sym(name, [(b, f"{n}  [{b}]", et) for b, n, net, et in L], [(b, f"[{b}]  {n}", et) for b, n, net, et in R], 71.12, part["value"], fp, True)
    if prefix in ("X", "J"):
        left = [(pad, nm, et) for pad, nm, net, et in pins if pad.isdigit() and int(pad) % 2 == 1]
        right = [(pad, nm, et) for pad, nm, net, et in pins if not (pad.isdigit() and int(pad) % 2 == 1)]
        return Sym(name, left, right, 22.86, part["value"], fp)
    left = [(pad, nm, et) for pad, nm, net, et in pins if et in ("input", "power_in", "bidirectional")]
    right = [(pad, nm, et) for pad, nm, net, et in pins if et not in ("input", "power_in", "bidirectional")]
    if not right or not left:
        half = (len(pins) + 1) // 2
        left, right = [(a, b, d) for a, b, c, d in pins[:half]], [(a, b, d) for a, b, c, d in pins[half:]]
    return Sym(name, left, right, 30.48, part["value"], fp)


# ---------------------------------------------------------------------------
# sheet writer
# ---------------------------------------------------------------------------
class Sheet:
    def __init__(self, project, fname, root_uuid, sheet_uuid=None, paper="A3"):
        self.project, self.fname = project, fname
        self.uuid = sheet_uuid or root_uuid
        self.path = f"/{root_uuid}" + (f"/{sheet_uuid}" if sheet_uuid else "")
        self.paper = paper
        self.syms, self.items = {}, []
        self.pw, self.ph = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420)}[paper]

    def place(self, part, x, y):
        sym = make_symbol(part)
        self.syms[sym.name] = sym
        ref = part["ref"]
        o = [f"(symbol (lib_id {q('FMUM:' + sym.name)}) (at {f(x)} {f(y)} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)"]
        o.append(f"(uuid {q(U(self.project, self.fname, 'sym', ref))})")
        o.append(f'(property "Reference" {q(ref)} (at {f(x)} {f(y - sym.h/2 - 1.27)} 0) {FONT})')
        o.append(f'(property "Value" {q(part["value"])} (at {f(x)} {f(y + sym.h/2 + 1.27)} 0) {FONT})')
        o.append(f'(property "Footprint" {q(sym.footprint)} (at {f(x)} {f(y)} 0) {FONT_H})')
        o.append(f'(property "Datasheet" "" (at {f(x)} {f(y)} 0) {FONT_H})')
        o.append(f'(property "Description" {q(part.get("desc", ""))} (at {f(x)} {f(y)} 0) {FONT_H})')
        nets = {pad: net for pad, nm, net, et in part["pins"]}
        for pad, name, et, pos in sym.pins():
            o.append(f'(pin {q(pad)} (uuid {q(U(self.project, self.fname, "pin", ref, pad))}))')
        o.append(f'(instances (project {q(self.project)} (path {q(self.path)} (reference {q(ref)}) (unit 1)))))')
        self.items.append("\n".join(o))
        for pad, name, et, (px, py, ang) in sym.pins():
            net = nets.get(pad)
            if not net:
                continue
            lx, ly = x + px, y - py
            la, just = {0: (180, "right"), 180: (0, "left"), 270: (90, "left"), 90: (270, "left")}[ang]
            shape = "input" if net == "GND" else "bidirectional"
            self.items.append(
                f"(global_label {q(net)} (shape {shape}) (at {f(lx)} {f(ly)} {la}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) "
                f"(uuid {q(U(self.project, self.fname, 'lbl', ref, pad))}) "
                f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {f(lx)} {f(ly)} 0) (effects (font (size 1.27 1.27)) (justify {just}) (hide yes))))')
        return sym

    def flow(self, parts, x0=40, y0=30, xmax=None, col_gap=70, row_gap=14):
        xmax = xmax or self.pw - 30
        x, y, row_h = x0, y0, 0
        for part in parts:
            sym = make_symbol(part)
            w = sym.width + 2 * (col_gap if not isinstance(sym, TwoPin) else 22)
            if x + w > xmax and x > x0:
                x, y, row_h = x0, y + row_h + row_gap, 0
            self.place(part, x + w / 2, y + sym.h / 2 + 8)
            x += w
            row_h = max(row_h, sym.h + 16)
        return y + row_h

    def text(self, s, x, y, size=1.5):
        self.items.append(f"(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid {q(U(self.project, self.fname, 'txt', s, x, y))}))")

    def write(self, outdir, extra=(), root=False):
        o = [f"(kicad_sch (version {VERSION}) (generator \"gen_kicad\") (generator_version \"8.0\")", f"(uuid {q(self.uuid)})", f"(paper {q(self.paper)})", "(lib_symbols"]
        o += [s.sexp() for s in self.syms.values()]
        o.append(")")
        o += self.items
        o += extra
        if root:
            o.append('(sheet_instances (path "/" (page "1")))')
        o.append(")")
        with open(os.path.join(outdir, self.fname), "w") as fh:
            fh.write("\n".join(o) + "\n")


def write_project(outdir, project, root_uuid, children):
    root = Sheet(project, f"{project}.kicad_sch", root_uuid, None, "A4")
    items, y = [], 30
    for page, (title, child, cu) in enumerate(children, start=2):
        items.append(f"(sheet (at 25.4 {f(y)}) (size 70 25) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0)) (uuid {q(cu)}) "
                     f'(property "Sheetname" {q(title)} (at 25.4 {f(y-0.8)} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) '
                     f'(property "Sheetfile" {q(child)} (at 25.4 {f(y+25.6)} 0) (effects (font (size 1.27 1.27)) (justify left top))) '
                     f"(instances (project {q(project)} (path {q('/' + root_uuid)} (page {q(str(page))})))))")
        y += 40
    root.text(f"{project}: reverse-engineered CUAV V6X hardware (Pixhawk FMUv6X). Not vendor data.", 110, 40, 2.0)
    root.text("Connectivity by global labels; pin numbers are the real package pins (U1: BGA balls).", 110, 46)
    root.text("Sources: PX4 boards/px4/fmu-v6x, Pixhawk DS-010/DS-012, manufacturer datasheets.", 110, 52)
    root.write(outdir, items, root=True)
    pro = {"board": {"design_settings": {}, "layer_presets": [], "viewports": []},
           "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
           "meta": {"filename": f"{project}.kicad_pro", "version": 1},
           "net_settings": {"classes": [{"name": "Default", "clearance": 0.1, "track_width": 0.1, "via_diameter": 0.45, "via_drill": 0.2,
                                         "diff_pair_width": 0.1, "diff_pair_gap": 0.15, "diff_pair_via_gap": 0.25, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                                         "wire_width": 6, "bus_width": 12, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "line_style": 0}],
                            "meta": {"version": 3}, "net_colors": None, "netclass_assignments": None, "netclass_patterns": []},
           "pcbnew": {"page_layout_descr_file": ""},
           "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0, "label_size_ratio": 0.375, "pin_symbol_size": 25.0, "text_offset_ratio": 0.15},
                         "legacy_lib_dir": "", "legacy_lib_list": [], "meta": {"version": 1}},
           "sheets": [[root_uuid, "Root"]] + [[cu, t] for t, c, cu in children], "text_variables": {}}
    with open(os.path.join(outdir, f"{project}.kicad_pro"), "w") as fh:
        json.dump(pro, fh, indent=2)


def fmum_sheet_of(part):
    r = part["ref"]
    if r == "U1":
        return 0
    if r in ("X1", "X2", "J3", "J4", "J1") or (r.startswith("TP") and r != "TP1"):
        return 1
    if r in ("U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9") or r in [f"R{i}" for i in range(1, 25)] or \
       r in ("C1", "C2", "C3", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C15"):
        return 2
    return 3


def main():
    out = os.path.join(HERE, "kicad", "fmum")
    os.makedirs(out, exist_ok=True)
    project, root_uuid = "cuav_v6x_fmum", U("fmum-root")
    children = [("MCU", "01_mcu.kicad_sch", U("fmum", "mcu")), ("Bus connectors", "02_connectors.kicad_sch", U("fmum", "conn")),
                ("Power and on-module sensors", "03_power_sensors.kicad_sch", U("fmum", "power")), ("Core peripherals", "04_core.kicad_sch", U("fmum", "core"))]
    groups = {i: [] for i in range(4)}
    for p in PR.FMUM_PARTS:
        groups[fmum_sheet_of(p)].append(p)
    s = Sheet(project, children[0][1], root_uuid, children[0][2], "A2")
    s.place(groups[0][0], 297, 200)
    s.text("U1 STM32H743IIK6, UFBGA176+25. Only connected balls are drawn; pin numbers are the ball names from ST's pin data. Unused GPIO balls are left open on the PCB.", 20, 410)
    s.write(out)
    s = Sheet(project, children[1][1], root_uuid, children[1][2], "A2")
    s.flow(groups[1], col_gap=75)
    s.text("X1/X2: Pixhawk Autopilot Bus (DS-010). J3: IMU flex (DS-012 p.17). J4: microSD. J1: unpopulated ETM trace pads. TPn: test pads (nets unknown).", 20, 410)
    s.write(out)
    s = Sheet(project, children[2][1], root_uuid, children[2][2], "A2")
    s.flow(groups[2], col_gap=60)
    s.text("Regulators are replica substitutes (the original uses a switching regulator for the 3.3 V rail). Sensor LDOs: one per redundancy domain, EN from the MCU, 10k/10k sense dividers to ADC1.", 20, 410)
    s.write(out)
    s = Sheet(project, children[3][1], root_uuid, children[3][2], "A2")
    s.flow(groups[3], col_gap=60)
    s.text("FRAM (SPI5), SE050 (pads intentionally unassigned: pinout not verified), crystals, RTC cell with BAT54 + 1k charge path, LEDs (active low), module ID ladder 24.9k/442k, BOOT0 pad, reset cap.", 20, 410)
    s.write(out)
    write_project(out, project, root_uuid, children)

    out = os.path.join(HERE, "kicad", "imu")
    os.makedirs(out, exist_ok=True)
    project, root_uuid = "cuav_v6x_imu", U("imu-root")
    children = [("IMU board", "01_imu.kicad_sch", U("imu", "sheet"))]
    s = Sheet(project, children[0][1], root_uuid, children[0][2], "A2")
    s.flow(PR.IMU_PARTS, col_gap=60)
    s.text("IMU board 'V6X IMU RC10'. All rails arrive over J1 from the FMUM. RM3100 = U3 MagI2C + L1/L2 Sen-XY-f + L3 Sen-Z-f with 121 R bias resistors and 33k REXT (PNI reference design).", 20, 410)
    s.write(out)
    write_project(out, project, root_uuid, children)
    print("wrote kicad/fmum and kicad/imu schematics")


if __name__ == "__main__":
    main()
