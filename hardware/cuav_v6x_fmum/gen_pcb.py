#!/usr/bin/env python3
"""
Generate the two KiCad 8 PCBs from parts.py:

  kicad/fmum/cuav_v6x_fmum.kicad_pcb   FMU module, 36.0 x 31.4 mm, 6 layers
  kicad/imu/cuav_v6x_imu.kicad_pcb     IMU board, ~25 x 18 mm octagon, 4 layers

What is real: outline, mounting holes, connector positions (Pixhawk DS-010),
component footprints (KiCad 8 library files in kicad/lib/ + generated ones for
parts the library lacks), every pad's net.  What is approximate: component
positions measured from the photos (+-0.5 mm).  What is missing: copper
routing.  The original is a 6-layer BGA board whose inner layers cannot be
recovered from photographs; route it yourself (the ratsnest is complete).
"""
import math
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts as PR  # noqa: E402

LIB = os.path.join(HERE, "kicad", "lib")
NS = uuid.UUID("7a2b3c4d-5e6f-4a1b-8c9d-0e1f2a3b4c5d")


def U(*key):
    return str(uuid.uuid5(NS, "|".join(str(k) for k in key)))


# ---------------------------------------------------------------------------
# minimal s-expression reader / writer
# ---------------------------------------------------------------------------
class Str(str):
    """a quoted string token"""


def parse(text):
    tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')
    pos, stack, root = 0, [[]], None
    while pos < len(text):
        m = tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"bad token at {pos}: {text[pos:pos+30]!r}")
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            lst = stack.pop()
            stack[-1].append(lst)
        elif m.group(3) is not None:
            stack[-1].append(Str(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        elif m.group(4) is not None:
            stack[-1].append(m.group(4))
    return stack[0][0]


def dump(node, depth=0):
    if isinstance(node, list):
        inner = " ".join(dump(n, depth + 1) for n in node)
        return "(" + inner + ")"
    if isinstance(node, Str):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(node)


def pretty(node, depth=0):
    """multi-line dump (one child list per line) – keeps files diff-able"""
    if not isinstance(node, list):
        return dump(node)
    if not any(isinstance(n, list) for n in node) or len(dump(node)) < 100:
        return dump(node)
    out = ["(" + " ".join(dump(n) for n in node if not isinstance(n, list))]
    for n in node:
        if isinstance(n, list):
            out.append("  " * (depth + 1) + pretty(n, depth + 1))
    return "\n".join(out) + ")"


def num(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def key(node):
    return node[0] if isinstance(node, list) and node else None


def find(node, k):
    return [n for n in node if key(n) == k]


# ---------------------------------------------------------------------------
# generated footprints (library lacks them) – returned as s-expression text
# ---------------------------------------------------------------------------
def fp_header(name, desc, attr="smd"):
    return [f'(footprint "{name}" (version 20240108) (generator "gen_pcb") (layer "F.Cu") (descr "{desc}") (attr {attr})',
            '(property "Reference" "REF**" (at 0 -1 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'(property "Value" "{name}" (at 0 1 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            '(property "Footprint" "" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1.27 1.27))))',
            '(property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1.27 1.27))))',
            '(property "Description" "" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1.27 1.27))))']


def smd(n, x, y, w, h, shape="roundrect", rr=0.25, layers='"F.Cu" "F.Paste" "F.Mask"'):
    extra = f" (roundrect_rratio {rr})" if shape == "roundrect" else ""
    return f'(pad "{n}" smd {shape} (at {num(x)} {num(y)}) (size {num(w)} {num(h)}) (layers {layers}){extra})'


def rect_lines(w, h, layer, width=0.1):
    x, y = w / 2, h / 2
    pts = [(-x, -y), (x, -y), (x, y), (-x, y), (-x, -y)]
    return [f'(fp_line (start {num(a[0])} {num(a[1])}) (end {num(b[0])} {num(b[1])}) (stroke (width {width}) (type default)) (layer "{layer}"))' for a, b in zip(pts, pts[1:])]


def gen_bga176():
    rows = "ABCDEFGHJKLMNPR"
    o = fp_header("ST_UFBGA-176+25_10x10mm_Layout15x15_P0.65mm", "UFBGA176+25, 0.65 mm pitch, 0.30 mm NSMD pads (ST recommends 0.30 mm)")
    for ri, r in enumerate(rows):
        for c in range(1, 16):
            inner = 4 <= ri <= 10 and 5 <= c <= 11
            centre = 5 <= ri <= 9 and 6 <= c <= 10
            if inner and not centre:
                continue
            x, y = (c - 8) * 0.65, (ri - 7) * 0.65
            o.append(f'(pad "{r}{c}" smd circle (at {num(x)} {num(y)}) (size 0.3 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))')
    o += rect_lines(10.0, 10.0, "F.Fab") + rect_lines(10.5, 10.5, "F.CrtYd", 0.05)
    o.append('(fp_circle (center -5.6 -5.6) (end -5.4 -5.6) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o += rect_lines(10.0, 10.0, "F.SilkS", 0.12)
    o.append(")")
    return "\n".join(o)


def gen_df40(n):
    """Hirose DF40C-nDP plug, 0.4 mm pitch, two rows. Pin 1/2 at -x end. Approximate land pattern."""
    o = fp_header(f"Hirose_DF40C-{n}DP-0.4V", f"Hirose DF40C-{n}DP-0.4V plug, approximated pattern - verify against Hirose drawing")
    per = n // 2
    x0 = -(per - 1) * 0.4 / 2
    for i in range(per):
        x = x0 + i * 0.4
        o.append(smd(2 * i + 1, x, -1.3, 0.2, 0.9, rr=0.2))   # odd row: appears LEFT in the DS-010 bottom view once mounted on B.Cu at 270 deg
        o.append(smd(2 * i + 2, x, 1.3, 0.2, 0.9, rr=0.2))
    L = per * 0.4 + 3.2
    o.append(smd("M1", -L / 2 + 0.5, 0, 0.6, 1.4, rr=0.2))
    o.append(smd("M2", L / 2 - 0.5, 0, 0.6, 1.4, rr=0.2))
    o += rect_lines(L, 3.0, "F.Fab") + rect_lines(L + 0.4, 3.6, "F.CrtYd", 0.05)
    o.append(f'(fp_circle (center {num(x0 - 0.6)} -2.1) (end {num(x0 - 0.45)} -2.1) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_bm20(n=34):
    o = fp_header("Hirose_BM20B-34-0.4V", "Hirose BM20B(0.8)-34 0.4 mm pitch board-to-board, approximated pattern - verify against Hirose drawing")
    per = n // 2
    x0 = -(per - 1) * 0.4 / 2
    for i in range(per):
        x = x0 + i * 0.4
        o.append(smd(2 * i + 1, x, 1.35, 0.22, 0.9, rr=0.2))
        o.append(smd(2 * i + 2, x, -1.35, 0.22, 0.9, rr=0.2))
    L = per * 0.4 + 3.0
    for k, (mx, my) in enumerate(((-L / 2 + 0.5, 1.0), (-L / 2 + 0.5, -1.0), (L / 2 - 0.5, 1.0), (L / 2 - 0.5, -1.0)), start=1):
        o.append(smd(f"M{k}", mx, my, 0.6, 0.8, rr=0.2))
    o += rect_lines(L, 3.2, "F.Fab") + rect_lines(L + 0.4, 3.8, "F.CrtYd", 0.05)
    o.append(f'(fp_circle (center {num(x0 - 0.6)} 2.2) (end {num(x0 - 0.45)} 2.2) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_lga10_icp():
    """TDK ICP-20100, 2x2 mm LGA-10, pitch 0.5. Pin positions from DS-000416 fig. 9 (bottom view mirrored to top view)."""
    o = fp_header("TDK_LGA-10_2x2mm_P0.5mm", "ICP-20100 2x2x0.8 mm LGA-10, port hole on top - keep the sensor in a routed stress-relief slot")
    pos = {10: (-0.5, -0.75), 9: (0, -0.75), 8: (0.5, -0.75), 1: (-0.75, -0.25), 2: (-0.75, 0.25),
           7: (0.75, -0.25), 6: (0.75, 0.25), 3: (-0.5, 0.75), 4: (0, 0.75), 5: (0.5, 0.75)}
    for n, (x, y) in pos.items():
        w, h = (0.3, 0.45) if y in (-0.75, 0.75) else (0.45, 0.3)
        o.append(smd(n, x, y, w, h, rr=0.2))
    o += rect_lines(2.0, 2.0, "F.Fab") + rect_lines(2.6, 2.6, "F.CrtYd", 0.05)
    o.append('(fp_circle (center -1.3 -0.25) (end -1.2 -0.25) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_lga16_bmi088():
    """Bosch BMI088 4.5x3 mm LGA-16: pins 1-7 along the top (left to right), 8 right, 9-15 bottom (right to left), 16 left. Datasheet fig. 6/11."""
    o = fp_header("Bosch_LGA-16_4.5x3mm_P0.5mm", "BMI088 LGA-16 4.5x3.0 mm, 0.5 mm pitch; land pattern per BST-BMI088-DS000 8.2")
    for i in range(7):
        x = -1.5 + i * 0.5
        o.append(smd(1 + i, x, -1.3, 0.25, 0.75, rr=0.2))
        o.append(smd(15 - i, x, 1.3, 0.25, 0.75, rr=0.2))
    o.append(smd(8, 1.9, 0, 0.7, 0.25, rr=0.2))
    o.append(smd(16, -1.9, 0, 0.7, 0.25, rr=0.2))
    o += rect_lines(4.5, 3.0, "F.Fab") + rect_lines(5.1, 3.6, "F.CrtYd", 0.05)
    o.append('(fp_circle (center -2.6 -1.5) (end -2.5 -1.5) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_qfn28_magi2c():
    """PNI MagI2C MLF-28 4x4 mm, 0.4 mm pitch, 7 pins per side, no exposed pad soldered (PNI recommendation)."""
    o = fp_header("PNI_MLF-28_4x4mm_P0.4mm", "PNI MagI2C 13156, MLF 4x4 mm 0.4 mm pitch; die pad intentionally not soldered")
    for i in range(7):
        t = -1.2 + i * 0.4
        o.append(smd(1 + i, -1.9, t, 0.75, 0.2, rr=0.2))        # left, top->bottom
        o.append(smd(8 + i, t, 1.9, 0.2, 0.75, rr=0.2))          # bottom, left->right
        o.append(smd(15 + i, 1.9, -t, 0.75, 0.2, rr=0.2))       # right, bottom->top
        o.append(smd(22 + i, -t, -1.9, 0.2, 0.75, rr=0.2))      # top, right->left
    o += rect_lines(4.0, 4.0, "F.Fab") + rect_lines(4.8, 4.8, "F.CrtYd", 0.05)
    o.append('(fp_circle (center -2.6 -1.4) (end -2.5 -1.4) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_senxy():
    o = fp_header("PNI_Sen-XY-f", "PNI Sen-XY-f coil 6.5x2.5 mm; pads 1.40x1.70 at 5.30 c-c (RM3100 manual fig. 3-3)")
    o.append(smd(1, -2.65, 0, 1.4, 1.7, "rect"))
    o.append(smd(2, 2.65, 0, 1.4, 1.7, "rect"))
    o += rect_lines(6.5, 2.5, "F.Fab") + rect_lines(7.2, 3.0, "F.CrtYd", 0.05)
    o.append(")")
    return "\n".join(o)


def gen_senz():
    o = fp_header("PNI_Sen-Z-f", "PNI Sen-Z-f coil 3.6x3.6x3.2 mm; pads 2.40x1.95, 0.40 gap (RM3100 manual fig. 3-6); polarity mark toward pad 1")
    o.append(smd(1, -1.4, 0, 2.4, 1.95, "rect"))
    o.append(smd(2, 1.4, 0, 2.4, 1.95, "rect"))
    o += rect_lines(3.6, 3.6, "F.Fab") + rect_lines(4.4, 4.2, "F.CrtYd", 0.05)
    o.append('(fp_line (start -1.8 -2.1) (end -1.0 -2.1) (stroke (width 0.15) (type default)) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_ms621():
    o = fp_header("Seiko_MS621FE", "Seiko MS621FE 6.8 mm rechargeable cell with horizontal tabs (approximate)")
    o.append(smd(1, -4.5, 0, 2.0, 2.5, "rect"))
    o.append(smd(2, 4.5, 0, 2.0, 2.5, "rect"))
    o.append('(fp_circle (center 0 0) (end 3.4 0) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))')
    o.append('(fp_circle (center 0 0) (end 3.6 0) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    o += rect_lines(11.5, 7.6, "F.CrtYd", 0.05)
    o.append(")")
    return "\n".join(o)


def gen_sod323():
    o = fp_header("D_SOD-323", "SOD-323; pad 1 = cathode band end")
    o.append(smd(1, -1.1, 0, 0.6, 0.45))
    o.append(smd(2, 1.1, 0, 0.6, 0.45))
    o += rect_lines(1.7, 1.25, "F.Fab") + rect_lines(3.0, 1.7, "F.CrtYd", 0.05)
    o.append('(fp_line (start -0.6 -0.9) (end -0.6 0.9) (stroke (width 0.15) (type default)) (layer "F.SilkS"))')
    o.append(")")
    return "\n".join(o)


def gen_tp():
    o = fp_header("TestPad_1.0mm", "1.0 mm round test pad")
    o.append('(pad "1" smd circle (at 0 0) (size 1.0 1.0) (layers "F.Cu" "F.Mask"))')
    o.append(")")
    return "\n".join(o)


def gen_trace():
    o = fp_header("TRACE_8+2", "unpopulated 8-pad 0.8 mm pitch ETM trace footprint with two 2 mm mounting pads (as seen on the FMUM)")
    for i in range(8):
        o.append(smd(i + 1, -2.45 + i * 0.7, 0, 0.45, 1.5, rr=0.2))
    o.append(smd("M1", -3.7, 1.4, 1.5, 1.5, "rect"))
    o.append(smd("M2", 3.7, 1.4, 1.5, 1.5, "rect"))
    o += rect_lines(9.2, 4.0, "F.CrtYd", 0.05)
    o.append(")")
    return "\n".join(o)


def gen_hole(drill, pad, name, plated=True):
    o = fp_header(name, "grounded mounting hole", "through_hole" if plated else "through_hole")
    if plated:
        o.append(f'(pad "1" thru_hole circle (at 0 0) (size {num(pad)} {num(pad)}) (drill {num(drill)}) (layers "*.Cu" "*.Mask"))')
    else:
        o.append(f'(pad "" np_thru_hole circle (at 0 0) (size {num(drill)} {num(drill)}) (drill {num(drill)}) (layers "*.Cu" "*.Mask"))')
    o.append(f'(fp_circle (center 0 0) (end {num(pad/2+0.3)} 0) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))')
    o.append(")")
    return "\n".join(o)


def gen_mpad():
    o = fp_header("GroundPad_1.6mm", "plated contact pad for the isolation mount (M1-M4 on the IMU board)")
    o.append('(pad "1" smd circle (at 0 0) (size 1.6 1.6) (layers "F.Cu" "F.Mask"))')
    o.append(")")
    return "\n".join(o)


GEN = {"gen:UFBGA176": gen_bga176, "gen:DF40-100": lambda: gen_df40(100), "gen:DF40-50": lambda: gen_df40(50), "gen:BM20-34": gen_bm20,
       "gen:LGA10-ICP": gen_lga10_icp, "gen:LGA16-BMI088": gen_lga16_bmi088, "gen:QFN28-MAGI2C": gen_qfn28_magi2c,
       "gen:SENXY": gen_senxy, "gen:SENZ": gen_senz, "gen:MS621": gen_ms621, "gen:SOD323": gen_sod323, "gen:TP": gen_tp, "gen:TRACE": gen_trace,
       "gen:HOLE": lambda: gen_hole(2.0, 3.6, "MountingHole_2.0mm_3.6mm_GND"), "gen:NPTH": lambda: gen_hole(2.2, 2.2, "NPTH_2.2mm", False), "gen:MPAD": gen_mpad}


def load_footprint(fpkey):
    if fpkey.startswith("gen:"):
        return parse(GEN[fpkey]())
    name = fpkey.split(":", 1)[1]
    with open(os.path.join(LIB, name + ".kicad_mod")) as fh:
        return parse(fh.read())


# ---------------------------------------------------------------------------
# footprint placement: rename, rotate, flip, net-assign
# ---------------------------------------------------------------------------
FLIP_LAYER = {"F.Cu": "B.Cu", "B.Cu": "F.Cu", "F.Paste": "B.Paste", "B.Paste": "F.Paste", "F.Mask": "B.Mask", "B.Mask": "F.Mask",
              "F.SilkS": "B.SilkS", "B.SilkS": "F.SilkS", "F.Fab": "B.Fab", "B.Fab": "F.Fab", "F.CrtYd": "B.CrtYd", "B.CrtYd": "F.CrtYd",
              "F.Adhes": "B.Adhes", "B.Adhes": "F.Adhes"}


def flip_layers(node):
    """swap F./B. layer names in a (layer ..) or (layers ..) node"""
    for i, v in enumerate(node):
        if isinstance(v, Str) and v in FLIP_LAYER:
            node[i] = Str(FLIP_LAYER[v])


def mirror_x(node):
    """mirror geometry of a footprint child about the footprint's y axis (KiCad flip L/R)"""
    if not isinstance(node, list):
        return
    k = key(node)
    if k in ("at", "start", "end", "mid", "center", "xy") and len(node) >= 3:
        node[1] = num(-float(node[1]))
        if k == "at" and len(node) >= 4:
            node[3] = num(-float(node[3]))
    if k in ("layer", "layers"):
        flip_layers(node)
    if k == "effects":
        just = find(node, "justify")
        if just:
            if "mirror" not in just[0]:
                just[0].append("mirror")
        else:
            node.append(["justify", "mirror"])
    for n in node:
        mirror_x(n)


def place_footprint(part, netnum, lib_id_of):
    fp = load_footprint(part["fp"])
    ref, side = part["ref"], part["side"]
    # strip library-only headers
    fp[:] = [n for n in fp if key(n) not in ("version", "generator", "generator_version")]
    fp[1] = Str(lib_id_of(part["fp"]))
    # layer / uuid / position
    lay = find(fp, "layer")[0]
    idx = fp.index(lay)
    fp.insert(idx + 1, ["uuid", Str(U("fp", part["ref"], part["fp"]))])
    fp.insert(idx + 2, ["at", num(part["x"]), num(part["y"]), num(part["rot"])])
    # properties
    for prop in find(fp, "property"):
        if prop[1] == "Reference":
            prop[2] = Str(ref)
        elif prop[1] == "Value":
            prop[2] = Str(part["value"])
    # give every child a fresh uuid
    def reuuid(node, path):
        if isinstance(node, list):
            for i, n in enumerate(node):
                if isinstance(n, list) and key(n) == "uuid":
                    node[i] = ["uuid", Str(U("item", ref, path, i))]
                elif isinstance(n, list):
                    reuuid(n, f"{path}/{i}")
    reuuid(fp, "")
    for item in fp:
        if isinstance(item, list) and key(item) in ("pad", "fp_line", "fp_circle", "fp_arc", "fp_poly", "fp_rect", "fp_text", "property") and not find(item, "uuid"):
            item.append(["uuid", Str(U("item2", ref, dump(item)[:200]))])
    # nets
    nets = {pad: net for pad, name, net, et in part["pins"]}
    for pad in find(fp, "pad"):
        net = nets.get(str(pad[1]))
        if net:
            pad.append(["net", str(netnum[net]), Str(net)])
    fp.append(["path", Str("/" + U("sym", part["ref"]))])
    if side == "B":
        lay[1] = Str("B.Cu")
        for n in fp:
            if isinstance(n, list) and key(n) not in ("layer", "at", "uuid", "path", "descr", "tags", "attr", "model"):
                mirror_x(n)
    return fp


# ---------------------------------------------------------------------------
# board
# ---------------------------------------------------------------------------
LAYER_DEFS = {
    6: ['(0 "F.Cu" signal)', '(1 "In1.Cu" signal)', '(2 "In2.Cu" signal)', '(3 "In3.Cu" signal)', '(4 "In4.Cu" signal)', '(31 "B.Cu" signal)'],
    4: ['(0 "F.Cu" signal)', '(1 "In1.Cu" signal)', '(2 "In2.Cu" signal)', '(31 "B.Cu" signal)'],
}
USER_LAYERS = ['(32 "B.Adhes" user "B.Adhesive")', '(33 "F.Adhes" user "F.Adhesive")', '(34 "B.Paste" user)', '(35 "F.Paste" user)',
               '(36 "B.SilkS" user "B.Silkscreen")', '(37 "F.SilkS" user "F.Silkscreen")', '(38 "B.Mask" user)', '(39 "F.Mask" user)',
               '(40 "Dwgs.User" user "User.Drawings")', '(41 "Cmts.User" user "User.Comments")', '(42 "Eco1.User" user "User.Eco1")',
               '(43 "Eco2.User" user "User.Eco2")', '(44 "Edge.Cuts" user)', '(45 "Margin" user)', '(46 "B.CrtYd" user "B.Courtyard")',
               '(47 "F.CrtYd" user "F.Courtyard")', '(48 "B.Fab" user)', '(49 "F.Fab" user)', '(50 "User.1" user)', '(51 "User.2" user)']


def gr_line(a, b, layer="Edge.Cuts", w=0.1):
    return f'(gr_line (start {num(a[0])} {num(a[1])}) (end {num(b[0])} {num(b[1])}) (stroke (width {w}) (type default)) (layer "{layer}") (uuid "{U("gr", a, b, layer)}"))'


def gr_arc(s, m, e, layer="Edge.Cuts", w=0.1):
    return f'(gr_arc (start {num(s[0])} {num(s[1])}) (mid {num(m[0])} {num(m[1])}) (end {num(e[0])} {num(e[1])}) (stroke (width {w}) (type default)) (layer "{layer}") (uuid "{U("arc", s, e, layer)}"))'


def gr_text(t, x, y, layer="F.SilkS", size=1.0, mirror=False):
    mir = " (justify mirror)" if mirror else ""
    return f'(gr_text "{t}" (at {num(x)} {num(y)} 0) (layer "{layer}") (uuid "{U("txt", t, x, y, layer)}") (effects (font (size {size} {size}) (thickness 0.15)){mir}))'


def rounded_rect_outline(w, h, r):
    o = []
    o.append(gr_line((r, 0), (w - r, 0)))
    o.append(gr_arc((w - r, 0), (w - r + r * math.sin(math.pi / 4), r - r * math.cos(math.pi / 4)), (w, r)))
    o.append(gr_line((w, r), (w, h - r)))
    o.append(gr_arc((w, h - r), (w - r + r * math.cos(math.pi / 4), h - r + r * math.sin(math.pi / 4)), (w - r, h)))
    o.append(gr_line((w - r, h), (r, h)))
    o.append(gr_arc((r, h), (r - r * math.sin(math.pi / 4), h - r + r * math.cos(math.pi / 4)), (0, h - r)))
    o.append(gr_line((0, h - r), (0, r)))
    o.append(gr_arc((0, r), (r - r * math.cos(math.pi / 4), r - r * math.sin(math.pi / 4)), (r, 0)))
    return o


def slot_outline(pts, width):
    """closed outline of a U-shaped slot around a centre-line polyline (rectangle segments, no rounded ends)"""
    o, hw = [], width / 2
    # offset each segment both sides; simple approach: draw each segment as its own rectangle + connect ends
    segs = list(zip(pts, pts[1:]))
    outer, inner = [], []
    for (x1, y1), (x2, y2) in segs:
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * hw, dx / L * hw
        outer.append(((x1 + nx, y1 + ny), (x2 + nx, y2 + ny)))
        inner.append(((x1 - nx, y1 - ny), (x2 - nx, y2 - ny)))
    # exact mitre corners for axis-aligned polylines
    def mitre(side):
        res = [side[0][0]]
        for (a1, a2), (b1, b2) in zip(side, side[1:]):
            # both segments axis aligned: corner is (x of the vertical one, y of the horizontal one)
            if abs(a1[0] - a2[0]) < 1e-9:   # a vertical
                res.append((a2[0], b1[1]))
            else:
                res.append((b1[0], a2[1]))
        res.append(side[-1][1])
        return res
    O, I = mitre(outer), mitre(inner)
    poly = O + [I[-1]] + I[::-1][1:] + [O[0]]
    for a, b in zip(poly, poly[1:]):
        o.append(gr_line(a, b))
    return o


def octagon_outline(w, h, cx, cy, notch_r):
    """octagon with chamfered corners and semicircular notches at top and bottom centre"""
    pts = [(cx, 0), (w - cx, 0), (w, cy), (w, h - cy), (w - cx, h), (cx, h), (0, h - cy), (0, cy), (cx, 0)]
    o = []
    for a, b in zip(pts, pts[1:]):
        if a[1] == 0 and b[1] == 0:       # top edge with notch
            o.append(gr_line(a, (w / 2 - notch_r, 0)))
            o.append(gr_arc((w / 2 - notch_r, 0), (w / 2, notch_r), (w / 2 + notch_r, 0)))
            o.append(gr_line((w / 2 + notch_r, 0), b))
        elif a[1] == h and b[1] == h:     # bottom edge with notch
            o.append(gr_line(a, (w / 2 + notch_r, h)))
            o.append(gr_arc((w / 2 + notch_r, h), (w / 2, h - notch_r), (w / 2 - notch_r, h)))
            o.append(gr_line((w / 2 - notch_r, h), b))
        else:
            o.append(gr_line(a, b))
    return o


def build_board(board, parts, extra_parts, outfile, title, lib_id_of):
    nets = sorted(PR.netlist(parts + extra_parts))
    netnum = {n: i + 1 for i, n in enumerate(nets)}
    o = ['(kicad_pcb (version 20240108) (generator "gen_pcb") (generator_version "8.0")',
         f'(general (thickness 1.6) (legacy_teardrops no))', '(paper "A4")',
         "(layers " + " ".join(LAYER_DEFS[board["layers"]] + USER_LAYERS) + ")",
         '(setup (pad_to_mask_clearance 0.05) (allow_soldermask_bridges_in_footprints no) (pcbplotparams (layerselection 0x00010fc_ffffffff) (plot_on_all_layers_selection 0x0000000_00000000) (disableapertmacros no) (usegerberextensions no) (usegerberattributes yes) (usegerberadvancedattributes yes) (creategerberjobfile yes) (dashed_line_dash_ratio 12.000000) (dashed_line_gap_ratio 3.000000) (svgprecision 4) (plotframeref no) (viasonmask no) (mode 1) (useauxorigin no) (hpglpennumber 1) (hpglpenspeed 20) (hpglpendiameter 15.000000) (pdf_front_fp_property_popups yes) (pdf_back_fp_property_popups yes) (dxfpolygonmode yes) (dxfimperialunits yes) (dxfusepcbnewfont yes) (psnegative no) (psa4output no) (plotreference yes) (plotvalue yes) (plotfptext yes) (plotinvisibletext no) (sketchpadsonfab no) (subtractmaskfromsilk no) (outputformat 1) (mirror no) (drillshape 1) (scaleselection 1) (outputdirectory "")))',
         '(net 0 "")']
    o += [f'(net {i} "{n}")' for n, i in netnum.items()]
    for p in parts + extra_parts:
        o.append(pretty(place_footprint(p, netnum, lib_id_of)))
    return o, netnum


def fmum_extra():
    return [PR.P(f"H{i+1}", "M2 GND", "gen:HOLE", "F", x, y, 0, [("1", "1", "GND", "passive")], "mounting hole, 2.0 drill / 3.6 pad") for i, (x, y) in enumerate(PR.FMUM_BOARD["holes"])]


def imu_extra():
    ex = [PR.P(f"H{i+1}", "2.2 mm", "gen:NPTH", "F", x, y, 0, [], "isolation mount hole") for i, (x, y) in enumerate(PR.IMU_BOARD["npth"])]
    ex += [PR.P(name, "GND pad", "gen:MPAD", side, x, y, 0, [("1", "1", "GND", "passive")], "isolation mount contact pad") for name, side, x, y in PR.IMU_BOARD["pads"]]
    return ex


def main():
    from gen_kicad import fp_id
    # ---------------- FMUM
    b = PR.FMUM_BOARD
    o, netnum = build_board(b, PR.FMUM_PARTS, fmum_extra(), None, "FMUM", fp_id)
    o += rounded_rect_outline(b["w"], b["h"], b["corner_r"])
    o += slot_outline(b["slot"], 0.6)
    o.append(gr_text("CUAV V6X FMUM replica", 17.0, 12.5, "F.SilkS", 1.0))
    o.append(gr_text("top = SD side", 17.0, 14.0, "F.SilkS", 0.8))
    o.append(gr_text("X1 100-pin  |  X2 50-pin  |  U1 STM32H743", 18.0, 30.0, "B.SilkS", 0.8, True))
    o.append(gr_text("Reverse-engineered from PX4 board files + Pixhawk DS-010/DS-012. Positions from photos (+-0.5 mm). UNROUTED.", 18.0, -2.5, "Cmts.User", 0.8))
    o.append(")")
    with open(os.path.join(HERE, "kicad", "fmum", "cuav_v6x_fmum.kicad_pcb"), "w") as fh:
        fh.write("\n".join(o) + "\n")
    print("wrote kicad/fmum/cuav_v6x_fmum.kicad_pcb", len(netnum), "nets")
    # ---------------- IMU
    b = PR.IMU_BOARD
    o, netnum = build_board(b, PR.IMU_PARTS, imu_extra(), None, "IMU", fp_id)
    o += octagon_outline(b["w"], b["h"], b["chamfer"][0], b["chamfer"][1], b["notch_r"])
    o.append(gr_text("V6X IMU replica", 12.5, 16.8, "F.SilkS", 0.8))
    o.append(gr_text("^ flight direction", 20.5, 9.0, "F.SilkS", 0.6))
    o.append(gr_text("Outline estimated from photos (~25 x 18 mm). UNROUTED.", 12.5, -2.0, "Cmts.User", 0.8))
    o.append(")")
    with open(os.path.join(HERE, "kicad", "imu", "cuav_v6x_imu.kicad_pcb"), "w") as fh:
        fh.write("\n".join(o) + "\n")
    print("wrote kicad/imu/cuav_v6x_imu.kicad_pcb", len(netnum), "nets")


if __name__ == "__main__":
    main()
