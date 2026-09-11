#!/usr/bin/env python3
"""Assemble the self-contained HTML report (schematic sheets inlined, photos
embedded) from README data + gen_schematic tables.  Output:
cuav_v6x_fmum_schematic.html next to this file."""
import base64
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_schematic as G  # noqa: E402

E = lambda s: html.escape(str(s), quote=True)


def inline_svg(name):
    s = open(os.path.join(HERE, "schematic", name)).read()
    # let the page size it: drop fixed width/height, keep viewBox
    s = re.sub(r'\swidth="\d+"\sheight="\d+"', "", s, count=1)
    return s


def b64img(path):
    with open(os.path.join(HERE, path), "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def mcu_pins(net):
    if net in G.POWER_NETS or net == "GND":
        return ""
    if net == "V_RTC_BAT":
        return "VBAT"
    return ", ".join(G.NET_TO_MCU.get(net, []))


def conn_table(tbl, nc=set()):
    rows = []
    n = len(tbl)
    for r in range((n + 1) // 2):
        cells = []
        for side in (0, 1):
            p = 2 * r + 1 + side
            net = tbl.get(p, "")
            cls = "gnd" if net == "GND" else "pwr" if net in G.POWER_NETS else "nc" if net in nc else "sig"
            m = mcu_pins(net)
            cells.append(f'<td class="pin">{p}</td><td class="{cls}">{E(net)}{" <span class=nc-tag>n.c.</span>" if net in nc else ""}</td><td class="mcu">{E(m)}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div class="tscroll"><table class="conn"><thead><tr><th>pin</th><th>net</th><th>U1</th><th>pin</th><th>net</th><th>U1</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def pin_table():
    rows = []
    for pin, fn, net, dest in G.PINS:
        cls = "pwr" if net in G.POWER_NETS else "nc" if dest.startswith("NC") else "sig"
        rows.append(f"<tr><td class=mcu>{E(pin)}</td><td>{E(fn)}</td><td class={cls}>{E(net)}</td><td class=dest>{E(dest)}</td></tr>")
    return ('<div class="tscroll"><table class="pins"><thead><tr><th>U1 pin</th><th>function</th><th>net</th><th>goes to</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


SENSORS = [
    ("IMU 1", "Bosch BMI088 accel + gyro", "SPI3", "PI4 (accel) / PI8 (gyro)", "PI7", "SENSORS3", "IMU board (J3)"),
    ("IMU 2", "TDK ICM-42688-P", "SPI2", "PH5", "PA10", "SENSORS2", "IMU board (J3)"),
    ("IMU 3", "TDK ICM-20649", "SPI1", "PI9", "PF2", "SENSORS1", "this module"),
    ("Compass", "PNI RM3100", "I2C4", "0x20", "—", "SENSORS4", "IMU board (J3)"),
    ("Baro 1", "TDK ICP-20100", "I2C4", "0x64", "—", "SENSORS4", "IMU board (J3)"),
    ("Baro 2", "TDK ICP-20100", "I2C2", "0x63", "PG5", "SENSORS2", "this module"),
    ("Cal. EEPROM", "24LC64", "I2C4", "0x50", "—", "SENSORS4", "IMU board (J3)"),
    ("Parameters", "FM25V02A FRAM 256 kbit", "SPI5", "PG7", "—", "FMU 3V3", "this module"),
    ("Secure element", "NXP SE050 (likely)", "I2C4", "0x48", "—", "FMU 3V3", "this module"),
]

PHOTO_BOTTOM = [  # (x%, y%, label) on fmum_bottom_mcu_side.jpg  (750x1000)
    (62, 47, "U1 STM32H7 BGA"),
    (22, 48, "X1 · 100-pin PAB"),
    (87, 48, "X2 · 50-pin PAB"),
    (55, 27, "ICM-20649 IMU3"),
    (74, 24, "ICP-20100 baro, in slot"),
    (40, 44, "Y1 16 MHz / Y2 32 kHz"),
    (47, 63, "3.3 V step-down"),
    (77, 65, "sensor LDOs + ID resistors"),
]
PHOTO_TOP = [  # on fmum_top_sd_side.jpg
    (14, 50, "J3 FLEX → IMU board"),
    (47, 57, "J4 microSD"),
    (66, 30, "FM25V02A FRAM"),
    (63, 43, "SE050 (likely)"),
    (76, 68, "B1 RTC cell"),
    (22, 76, "D1-D3 LEDs"),
    (16, 66, "J1 TRACE pads"),
    (45, 40, "BT0 = BOOT0"),
]


PHOTO_IMU_TOP = [  # imu_top_sensor_side.jpg
    (45, 42, "BMI088 (IMU 1)"),
    (41, 55, "ICM-42688-P (IMU 2)"),
    (59, 47, "PNI MagI2C (RM3100)"),
    (61, 39, "Sen-XY-f coil X"),
    (63, 62, "Sen-XY-f coil Y"),
    (53, 60, "Sen-Z-f coil"),
    (42, 63, "ICP-20100 baro #1"),
    (75, 53, "flight arrow"),
]
PHOTO_IMU_BOT = [  # imu_bottom_flex_side.jpg
    (41, 52, "FLEX (mates FMUM J3)"),
    (62, 43, "24LC64 cal EEPROM"),
    (77, 52, "MOSFET '3400'"),
    (24, 40, "470 Ω heater ×4"),
    (83, 38, ""),
    (24, 65, ""),
    (83, 63, ""),
]


def photo(fig, path, marks, caption):
    pins = "".join(
        f'<span class="mark" style="left:{x}%;top:{y}%"><i></i>{"<b>" + E(l) + "</b>" if l else ""}</span>' for x, y, l in marks)
    return f'''<figure class="photo">
  <div class="photo-wrap"><img src="{b64img(path)}" alt="{E(caption)}">{pins}</div>
  <figcaption><span class="fig">{fig}</span> {E(caption)}</figcaption>
</figure>'''


CSS = r"""
:root{
  --bg:#f1f3f2; --panel:#ffffff; --ink:#172026; --ink-2:#4b5560; --muted:#7a838c;
  --line:#d7dcda; --accent:#1f7a4d; --accent-ink:#0f5c37; --copper:#b0741f; --gnd:#6b7280;
  --nc:#9aa0a6; --note-bg:#fbf6e6; --note-line:#d9b85a; --mcu:#2f4fbf; --code:#eef1f0;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#11171a; --panel:#181f23; --ink:#e4e8e6; --ink-2:#b4bcc0; --muted:#8a949b;
  --line:#2b353b; --accent:#4fc38a; --accent-ink:#7fdcac; --copper:#e0a24a; --gnd:#98a1aa;
  --nc:#6f777e; --note-bg:#262214; --note-line:#8a7430; --mcu:#8ea4ff; --code:#1f282d;
}}
:root[data-theme="dark"]{
  --bg:#11171a; --panel:#181f23; --ink:#e4e8e6; --ink-2:#b4bcc0; --muted:#8a949b;
  --line:#2b353b; --accent:#4fc38a; --accent-ink:#7fdcac; --copper:#e0a24a; --gnd:#98a1aa;
  --nc:#6f777e; --note-bg:#262214; --note-line:#8a7430; --mcu:#8ea4ff; --code:#1f282d;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 'IBM Plex Sans',system-ui,'Helvetica Neue',Arial,sans-serif;padding-block:0 64px;padding-inline:clamp(16px,4vw,48px)}
.wrap{max-width:1180px;margin:0 auto}
h1,h2,h3{font-family:'IBM Plex Sans Condensed','IBM Plex Sans',system-ui,sans-serif;text-wrap:balance;letter-spacing:-.01em}
h1{font-size:clamp(30px,4.5vw,44px);line-height:1.05;margin:0 0 8px;font-weight:600}
h2{font-size:24px;margin:56px 0 14px;font-weight:600;border-top:2px solid var(--ink);padding-top:14px}
h3{font-size:17px;margin:26px 0 8px;font-weight:600}
p{max-width:72ch}
code,.mono,td.mcu,td.pin,td.sig,td.pwr,td.gnd,td.nc,.pins td:nth-child(3){font-family:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;font-size:.9em}
code{background:var(--code);padding:1px 5px;border-radius:3px}
header{padding-block:34px 10px;display:grid;gap:14px}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-ink)}
.lede{font-size:18px;color:var(--ink-2);max-width:68ch;margin:0}
.idcard{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin-top:8px}
.idcard div{background:var(--panel);padding:12px 14px}
.idcard .k{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.idcard .v{font-weight:600;margin-top:2px}
.photos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:22px;margin:18px 0}
.photo{margin:0}
.photo-wrap{position:relative;border:1px solid var(--line);background:#000;line-height:0}
.photo-wrap img{width:100%;height:auto;display:block}
.mark{position:absolute;transform:translate(-50%,-50%);line-height:1.2}
.mark i{display:block;width:12px;height:12px;border-radius:50%;border:2px solid #fff;background:var(--accent);box-shadow:0 0 0 2px rgba(0,0,0,.45);margin:0 auto}
.mark b{display:block;margin-top:4px;font:600 11px/1.2 'IBM Plex Mono',monospace;color:#fff;background:rgba(10,20,15,.78);padding:2px 6px;border-radius:2px;white-space:nowrap;transform:translateX(0)}
figcaption{font-size:13px;color:var(--ink-2);margin-top:8px}
.fig{font-family:'IBM Plex Mono',monospace;color:var(--accent-ink);font-weight:600;margin-right:4px}
table{border-collapse:collapse;width:100%;font-size:13.5px;font-variant-numeric:tabular-nums}
th{text-align:left;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--ink)}
td{padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:hover td{background:var(--code)}
.tscroll{overflow-x:auto;border:1px solid var(--line);background:var(--panel)}
.conn td.pin{color:var(--muted);text-align:right;width:3.2em}
td.mcu{color:var(--mcu);font-weight:600}
td.sig{color:var(--accent-ink);font-weight:600}
td.pwr{color:var(--copper);font-weight:600}
td.gnd{color:var(--gnd)}
td.nc{color:var(--nc)}
.nc-tag{font-size:10px;color:var(--nc);border:1px solid var(--nc);border-radius:2px;padding:0 3px;margin-left:4px;vertical-align:1px}
td.dest{color:var(--ink-2)}
.conf{display:inline-block;font:600 10px/1 'IBM Plex Mono',monospace;letter-spacing:.06em;padding:3px 6px;border-radius:2px;border:1px solid}
.hi{color:var(--accent-ink);border-color:var(--accent)} .md{color:var(--copper);border-color:var(--copper)} .lo{color:var(--nc);border-color:var(--nc)}
.sheet{background:var(--panel);border:1px solid var(--line);margin:18px 0 6px;overflow-x:auto}
.sheet svg{display:block;width:100%;height:auto;min-width:900px}
.sheet-h{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:8px;margin-top:30px}
.sheet-h a{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--accent-ink)}
.note{background:var(--note-bg);border:1px solid var(--note-line);padding:12px 16px;max-width:80ch;font-size:14px}
.note b{font-weight:600}
.blocks{display:grid;grid-template-columns:1fr auto 2fr auto 1fr;gap:10px;align-items:start;margin:16px 0}
.col h4{font:600 11px/1 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
.blk{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);padding:8px 10px;margin-bottom:8px;font-size:13px}
.blk.p{border-left-color:var(--copper)} .blk.m{border-left-color:var(--mcu)}
.blk small{display:block;color:var(--muted);font-family:'IBM Plex Mono',monospace;font-size:11px;margin-top:2px}
.arrow{align-self:center;color:var(--muted);font-family:'IBM Plex Mono',monospace;font-size:12px;text-align:center;padding-top:40px}
ol.steps{padding-left:1.2em;max-width:78ch} ol.steps li{margin:10px 0}
ul.tight{max-width:80ch} ul.tight li{margin:6px 0}
.src{font-size:13.5px;color:var(--ink-2);max-width:80ch}
@media (max-width:820px){.blocks{grid-template-columns:1fr}.arrow{padding:0;transform:rotate(90deg)}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""


def blocks():
    def col(title, items):
        return f'<div class="col"><h4>{title}</h4>' + "".join(
            f'<div class="blk {c}">{E(t)}<small>{E(s)}</small></div>' for c, t, s in items) + "</div>"
    base = col("base board (not this PCB)", [
        ("p", "Power path selector", "2 bricks + USB → VDD_5V_IN, 4 pins on X1"),
        ("", "JST-GH ports", "TELEM1-3, GPS1/2, UART4, CAN1/2, USB, PWM, ADIO, debug"),
        ("", "STM32F103 PX4IO", "8 more PWM + RC in, talks to U1 on USART6"),
        ("", "LAN8742A Ethernet PHY", "RMII over X2"),
        ("", "Base ID ladder + 24LC64 EEPROM", "HW_VER_SENSE, I2C3"),
    ])
    fmu = col("FMU module — this board", [
        ("m", "U1 STM32H743IIK6", "480 MHz M7 · 2 MB flash · 1 MB RAM"),
        ("p", "U_REG 5 V → 3.3 V step-down", "FMU_VDD_3V3, also exported on X1-84/86"),
        ("p", "U_LDO1…4 switched 3.3 V", "one per sensor domain · EN + ADC sense each"),
        ("", "FM25V02A FRAM · SPI5", "parameters"),
        ("", "microSD · SDMMC2", "logs · power-cycled by PC13"),
        ("", "ICM-20649 · SPI1", "IMU 3, domain 1"),
        ("", "ICP-20100 · I2C2", "baro 2, in stress-relief slot"),
        ("", "SE050 · I2C4", "secure element (likely)"),
        ("", "B1 RTC cell · Y1 16 MHz · Y2 32 kHz", "time-keeping"),
        ("", "HW-ID ladder 24.9k/442k", "module ID 1 = CUAV sensor set rev 1"),
    ])
    imu = col("IMU board (via J3 flex)", [
        ("", "BMI088 · SPI3", "IMU 1, domain 3"),
        ("", "ICM-42688-P · SPI2", "IMU 2, domain 2"),
        ("", "RM3100 · I2C4 0x20", "compass, domain 4"),
        ("", "ICP-20100 · I2C4 0x64", "baro 1, domain 4"),
        ("", "24LC64 · I2C4 0x50", "calibration EEPROM"),
        ("p", "Heater resistors + MOSFET", "HEATER from PB10, VDD_5V_IN"),
    ])
    return (f'<div class="blocks">{base}<div class="arrow">X1 100 p<br>X2 50 p<br>⇄</div>{fmu}'
            f'<div class="arrow">J3 34 p<br>⇄</div>{imu}</div>')


def sensor_table():
    rows = "".join(
        f"<tr><td>{E(a)}</td><td><b>{E(b)}</b></td><td class=sig>{E(c)}</td><td class=mono>{E(d)}</td><td class=mcu>{E(e)}</td><td class=pwr>{E(f)}</td><td>{E(g)}</td></tr>"
        for a, b, c, d, e, f, g in SENSORS)
    return ('<div class="tscroll"><table><thead><tr><th>role</th><th>part</th><th>bus</th><th>CS / addr</th><th>DRDY</th><th>power domain</th><th>location</th></tr></thead><tbody>'
            + rows + "</tbody></table></div>")


def features():
    items = [
        ("hi", "10 × 10 mm BGA, marked ARM / STM32H7…IIK6", "U1, STM32H743IIK6 (PX4 configures the H753 sibling). UFBGA176+25."),
        ("hi", "100-pin + 50-pin 0.4 mm connectors", "X1 / X2 Hirose DF40 — the Pixhawk Autopilot Bus. 3 mm stack to the base board."),
        ("hi", "3 × 3 mm QFN, top centre of MCU side", "ICM-20649 six-axis IMU #3 on SPI1 (the one hard-mounted IMU)."),
        ("hi", "2 mm metal-lid part with a port hole, in a U-shaped routed slot", "ICP-20100 barometer #2 on I2C2. The slot decouples it from board flex."),
        ("hi", "Two small metal cans left of the BGA", "Y1 16 MHz (HSE) and Y2 32.768 kHz (RTC) crystals — PX4 board.h confirms both frequencies."),
        ("md", "QFN + big inductor + capacitors, bottom centre", "U_REG, the 5 V → 3.3 V step-down for the MCU rail."),
        ("md", "SOT-23-5 ICs with 0402 capacitor clusters, right edge", "the four switched sensor LDOs and decoupling."),
        ("lo", "1.5 mm blue part marked IY2K", "small passive or IC (ESD array / tiny LDO). Not resolvable from the photo."),
        ("hi", "34-pin connector labelled FLEX", "J3 to the separate vibration-isolated IMU board; two of the three IMUs and the compass are there."),
        ("hi", "SOIC-8 at top", "FM25V02A 256 kbit FRAM — PX4 parameter storage; byte-writable, no wear."),
        ("md", "3 × 3 mm QFN marked S50 08 07", "most likely NXP SE050 secure element (I2C4 0x48, in the reference sensor set)."),
        ("hi", "Round metal can marked L03", "B1 RTC backup cell; exported to the base as V_RTC_BAT (X1-29)."),
        ("hi", "Three 0603 LEDs, 8+2 unpopulated pads, BT0 pad", "D1-D3 status LEDs · J1 ETM trace footprint · BOOT0 for the ST DFU bootloader."),
    ]
    return '<div class="tscroll"><table><thead><tr><th>seen on the photo</th><th>what it is</th><th>confidence</th></tr></thead><tbody>' + "".join(
        f"<tr><td>{E(a)}</td><td>{E(b)}</td><td><span class='conf {c}'>{ {'hi':'HIGH','md':'MEDIUM','lo':'LOW'}[c] }</span></td></tr>" for c, a, b in items) + "</tbody></table></div>"


def imu_table():
    rows = []
    for ref, part, pkg, pins in G.IMU_PARTS:
        nets = ", ".join(f"{pn}={net}" for pn, net in pins if net)
        rows.append(f"<tr><td class=mono>{E(ref)}</td><td>{E(part)}</td><td>{E(pkg)}</td><td class=dest>{E(nets)}</td></tr>")
    return '<div class="tscroll"><table><thead><tr><th>ref</th><th>part</th><th>package</th><th>pin = net</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"


def imu_features():
    items = [
        ("hi", "Rectangular LGA, top left (sensor side)", "Bosch BMI088 accel + gyro — IMU 1 on SPI3, power domain 3."),
        ("hi", "Small LGA below it", "TDK ICM-42688-P — IMU 2 on SPI2, domain 2."),
        ("hi", "4 × 4 mm QFN, centre right", "PNI MagI2C, the controller of the RM3100 compass — I2C4 address 0x20."),
        ("hi", "Two flat black bars marked PNI, one horizontal one vertical", "PNI Sen-XY-f sense coils for the X and Y axes, mounted at 90°."),
        ("hi", "Black cube below the QFN", "PNI Sen-Z-f coil for the vertical axis."),
        ("hi", "Metal lid with port hole, bottom left", "TDK ICP-20100 barometer #1 — I2C4 address 0x64 (AD0 high)."),
        ("hi", "34-pin 0.4 mm connector labelled FLEX (flex side)", "Mating half of the FMUM's J3; a short FPC jumper links the two boards."),
        ("hi", "SOIC-8 (flex side)", "24LC64 calibration EEPROM — I2C4 0x50; PX4 stores calibration, revision and ID here."),
        ("hi", "Four large resistors marked 4700", "470 Ω heater resistors in parallel: 117 Ω across 5 V, about 0.21 W under the IMUs."),
        ("hi", "SOT-23 marked 3400 beside a resistor silkscreen symbol", "N-channel MOSFET (AO3400 class): low-side switch for the heater, driven by the HEATER line (PB10)."),
    ]
    return '<div class="tscroll"><table><thead><tr><th>seen on the photo</th><th>what it is</th><th>confidence</th></tr></thead><tbody>' + "".join(
        f"<tr><td>{E(a)}</td><td>{E(b)}</td><td><span class='conf {c}'>{ {'hi':'HIGH','md':'MEDIUM','lo':'LOW'}[c] }</span></td></tr>" for c, a, b in items) + "</tbody></table></div>"


BOM = [
    ("U1", "STM32H743IIK6 / STM32H753IIK6", "UFBGA176+25", "✔ from marking + PX4 defconfig"),
    ("X1", "Hirose DF40C-100DP-0.4V(51)", "0.4 mm, 3 mm stack", "✔ DS-010; base side DF40HC(3.0)-100DS-0.4V(58)"),
    ("X2", "Hirose DF40C-50DP-0.4V(51)", "", "✔ DS-010; base side DF40HC(3.0)-50DS-0.4V(51)"),
    ("J3", "Hirose BM20B(0.8)-34DP-0.4V(53)", "0.4 mm FPC receptacle", "✔ DS-012"),
    ("J4", "Molex 5031821852 microSD push-push", "", "✔ marking"),
    ("U_FRAM", "Infineon FM25V02A-G", "SOIC-8", "✔ PX4 mtd.cpp"),
    ("U_SE", "NXP SE050C1HQ1/Z01SC", "HX2QFN-20", "likely; optional for PX4"),
    ("U_IMU3", "TDK ICM-20649", "QFN-24 3×3", "✔ PX4 rc.board_sensors V6X001"),
    ("U_BARO2", "TDK ICP-20100", "LGA-10 2×2.5", "✔ PX4 + photo (slot island)"),
    ("U_REG", "3.3 V buck 1 A (e.g. TPS62A01 / TPS563201)", "QFN/SOT + 2.2 µH", "substitute"),
    ("U_LDO1-4", "3.3 V LDO 300 mA with EN (e.g. TLV75533PDBV)", "SOT-23-5", "substitute; EN = PI11 / PF4 / PE7 / PG8"),
    ("Q_SD", "load switch (e.g. TPS22918)", "SOT-23-6", "substitute; EN = PC13"),
    ("Y1", "16.000 MHz, CL 8-10 pF + 2×10 pF", "3225", "✔ frequency"),
    ("Y2", "32.768 kHz, CL 6-7 pF + 2×6.8 pF", "3215 / 2012", "✔ frequency"),
    ("B1", "rechargeable Li cell 3 V (Seiko MS621FE) or 0.1 F supercap", "", "charge via BAT54 + 1 kΩ"),
    ("D1-D3", "red / green / blue LED + 470 Ω-1 kΩ", "0603", "✔"),
    ("R-ID", "24.9 kΩ + 442 kΩ, 1 %", "0402", "✔ module ID 1"),
    ("R-pull", "1.5 kΩ ×8 on I2C1-4", "0402", "✔ DS-010 requirement"),
    ("R-div", "10 kΩ ×10 (5 rails, 1:2)", "0402", "✔ PX4 scaling"),
    ("C", "100 nF ×~20, 2.2 µF ×2 (VCAP), 4.7-22 µF bulk", "0402/0603", "standard H7 decoupling"),
    ("IMU U1", "Bosch BMI088", "LGA-16 3×4.5", "✔ IMU board"),
    ("IMU U2", "TDK ICM-42688-P", "LGA-14 2.5×3", "✔ IMU board"),
    ("IMU U3 + L1-L3", "PNI RM3100 set: MagI2C + 2× Sen-XY-f + 1× Sen-Z-f", "QFN 4×4 + coils", "✔ IMU board (PNI marking on coils)"),
    ("IMU U4", "TDK ICP-20100", "LGA-10 2×2.5", "✔ IMU board, AD0 high → 0x64"),
    ("IMU U5", "Microchip 24LC64", "SOIC-8", "✔ PX4 mtd.cpp"),
    ("IMU Q1, R1-R4", "AO3400-class N-MOSFET + 4× 470 Ω (marked 4700)", "SOT-23, 1210", "✔ markings"),
    ("IMU J1", "Hirose BM20B(0.8)-34DS-0.4V(53) + FPC jumper", "0.4 mm", "mates FMUM J3"),
]


def bom():
    return '<div class="tscroll"><table><thead><tr><th>ref</th><th>part</th><th>package</th><th>basis</th></tr></thead><tbody>' + "".join(
        f"<tr><td class=mono>{E(a)}</td><td>{E(b)}</td><td>{E(c)}</td><td class=dest>{E(d)}</td></tr>" for a, b, c, d in BOM) + "</tbody></table></div>"


def sheet(fname, num, title, blurb):
    return f'''<div class="sheet-h"><h3 id="s{num}">Sheet {num} · {E(title)}</h3><a href="schematic/{fname}" target="_blank" rel="noopener">open full size ↗</a></div>
<p>{E(blurb)}</p>
<div class="sheet">{inline_svg(fname)}</div>'''


def build():
    parts = []
    parts.append(f"<title>CUAV V6X FMUM Schematic</title>\n<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Mono:wght@400;600&display=swap\">\n<style>{CSS}</style>")
    parts.append('<div class="wrap">')
    parts.append('''<header>
<div class="eyebrow">board identification · reverse-engineered schematic</div>
<h1>CUAV V6X FMUM — the plug-in brain of a Pixhawk V6X autopilot</h1>
<p class="note"><b>Not official.</b> CUAV publishes no schematic of the V6X modules and the full Pixhawk FMUv6X reference schematics are Dronecode-member-only. This is an independent reconstruction: connectivity from the PX4 firmware that runs on this hardware, connector pinouts from the public Pixhawk standards, part identification from the photos.</p>
<p class="lede">The board in your photos is the FMU core module of the CUAV Pixhawk V6X flight controller: an STM32H7 processor, memory, one IMU and one barometer on a 36 × 31 mm card that plugs into a base board through the Pixhawk Autopilot Bus. Below: what every visible part is, how the module works, and six schematic sheets rebuilt from the PX4 firmware that runs on it and the two public Pixhawk standards it implements.</p>
<div class="idcard">
 <div><div class="k">silkscreen</div><div class="v">V6X_FMUM RC11 · 07-17/23</div></div>
 <div><div class="k">maker</div><div class="v">CUAV (Guangzhou)</div></div>
 <div><div class="k">standard</div><div class="v">Pixhawk FMUv6X · PAB (DS-010 / DS-012)</div></div>
 <div><div class="k">processor</div><div class="v">STM32H743IIK6, 480 MHz M7</div></div>
 <div><div class="k">firmware target</div><div class="v">px4_fmu-v6x · HW type V6X001</div></div>
 <div><div class="k">size</div><div class="v">36.0 × 31.4 mm · 4 × M2 ground holes</div></div>
</div>
</header>''')

    parts.append("<h2 id=identify>1 · What you are looking at</h2>")
    parts.append('<div class="photos">' + photo("A", "photos/fmum_bottom_mcu_side.jpg", PHOTO_BOTTOM,
                 "Bottom of the module (faces the base board): processor, both bus connectors, IMU 3, barometer 2, crystals, regulators.")
                 + photo("B", "photos/fmum_top_sd_side.jpg", PHOTO_TOP,
                 "Top of the module (visible when installed): IMU flex connector, microSD, FRAM, secure element, RTC cell, LEDs, trace pads.") + "</div>")
    parts.append(features())
    parts.append('<p class="note" style="margin-top:16px"><b>Where the confidence comes from.</b> The module runs PX4\'s <code>px4_fmu-v6x</code> target and identifies itself as hardware type <code>V6X001</code> ("CUAV sensor set rev 1") through a resistor ladder. The PX4 board files for that target hard-code every MCU pin, SPI chip-select, data-ready line, I²C address and power-enable, so the connectivity below is read from the firmware rather than guessed from traces. Connector pinouts come from the Pixhawk DS-010 and DS-012 standards. Only regulator part numbers, passive values and two small ICs are inferred.</p>')

    parts.append("<h3 id=imu>The second board: V6X IMU RC10</h3>")
    parts.append('<p>The octagonal board on the other end of the FLEX cable is CUAV\'s IMU board (silkscreen <code>V6X IMU RC10</code>, 2022-09-20). It sits in an elastomer isolation mount — the two half-round notches and the four ground pads M1-M4 are the mount interface — so the inertial sensors ride on a damped mass while the processor board is bolted rigidly to the base. It has no regulators: every rail arrives over the flex.</p>')
    parts.append('<div class="photos">' + photo("C", "photos/imu_top_sensor_side.jpg", PHOTO_IMU_TOP,
                 "IMU board, sensor side: BMI088, ICM-42688-P, the RM3100 compass as controller plus three coils, barometer #1.")
                 + photo("D", "photos/imu_bottom_flex_side.jpg", PHOTO_IMU_BOT,
                 "IMU board, flex side: mating 34-pin connector, calibration EEPROM, four 470 Ω heater resistors and their MOSFET.") + "</div>")
    parts.append(imu_features())
    parts.append("<h2 id=arch>2 · How the module works</h2>")
    parts.append('<p>Three boards, one system. Only 5 V and 3.3 V logic cross the connectors; everything that touches the outside world (transceivers, power switching, ESD) stays on the base board, which is what makes the module small and reusable across vendors.</p>')
    parts.append(blocks())
    parts.append('''<ul class="tight">
<li><b>One supply in, everything generated locally.</b> <code>VDD_5V_IN</code> enters on four X1 pins. A step-down makes <code>FMU_VDD_3V3</code> for the MCU and memories; that rail is also exported back to the base (X1-84/86).</li>
<li><b>Four independent sensor power domains.</b> Each IMU or compass group has its own LDO with an MCU-controlled enable and a 1:2 divider read by the ADC, so PX4 can power-cycle one misbehaving domain and watch every rail.</li>
<li><b>One IMU per SPI bus</b> (SPI1/2/3), each with a hardware data-ready interrupt; a hung device cannot stall the others. I2C4 is the internal sensor bus, I2C1-3 go to the base for GPS pucks and power monitors.</li>
<li><b>Storage:</b> FRAM for parameters (byte-writable, no wear), microSD for logs, battery-backed RTC and SRAM.</li>
<li><b>Self-identification.</b> At boot PG0 powers two resistor ladders; ADC3 reads them on PH4 (module ID) and PH3 (base ID, via X1-27). PX4 then starts exactly the right drivers and axis rotations for this sensor set.</li>
</ul>''')
    parts.append("<h3>Sensor set of this revision</h3>")
    parts.append(sensor_table())

    parts.append("<h2 id=sheets>3 · Schematic sheets</h2>")
    parts.append('<p class="note"><b>KiCad project.</b> The same data is generated as a KiCad 8 project with five hierarchical sheets, embedded symbols and global-label connectivity: <code>hardware/cuav_v6x_fmum/kicad/cuav_v6x_fmum.kicad_pro</code> on the branch <code>claude/unknown-component-schematics-mdgis0</code> of your PX4-Autopilot fork. Open the .kicad_pro; click any net label and press ` to highlight it across sheets.</p>')
    parts.append('<p>Net names follow the Pixhawk standards, so they line up with the published base-board reference schematics. Blue = MCU pin, green = signal net, copper = power rail, grey = ground.</p>')
    parts.append(sheet("01_mcu_u1.svg", 1, "U1 microcontroller", "Every used pin of the STM32H7: peripheral function inside the symbol, net name outside, and where the net goes in the margin. Pins not shown are unconnected on the module."))
    parts.append(sheet("02_core_peripherals.svg", 2, "Core peripherals", "FRAM, secure element, microSD with its power switch, both crystals, RTC cell, status LEDs, USB lines, the hardware-ID ladder and the reset / boot / trace provisions."))
    parts.append(sheet("03_power_and_sensors.svg", 3, "Power domains and on-module sensors", "The 3.3 V step-down, the four switched sensor LDOs with their ADC dividers, the on-board ICM-20649 and ICP-20100, the heater control line and the I²C pull-ups."))
    parts.append(sheet("04_x1_pab_100pin.svg", 4, "X1 — Pixhawk Autopilot Bus, 100 pins", "Pin-by-pin with the MCU pin that drives each signal. Odd pins on one row, even on the other."))
    parts.append(sheet("05_x2_pab_50pin.svg", 5, "X2 — Pixhawk Autopilot Bus, 50 pins", "RMII Ethernet to the PHY on the base, the external SPI6 payload bus, and the pins the standard reserves but an FMUv6X module leaves unconnected."))
    parts.append(sheet("06_j3_imu_flex_34pin.svg", 6, "J3 — IMU flex connector, 34 pins", "Two SPI buses, I2C4, three switched 3.3 V rails, raw 5 V for the heater and the heater control line, with a ground between every signal group."))
    parts.append(sheet("07_imu_board.svg", 7, "IMU board (V6X IMU RC10)", "Everything on the vibration-isolated board: the mating flex connector, BMI088, ICM-42688-P, the RM3100 controller with its three coils, barometer #1, the calibration EEPROM and the heater with its MOSFET."))

    parts.append("<h2 id=tables>4 · Pin tables</h2>")
    parts.append("<h3>U1 pin map (as configured by PX4 for this module)</h3>")
    parts.append(pin_table())
    parts.append("<h3>X1 — 100-pin bus</h3>")
    parts.append(conn_table(G.X1))
    parts.append("<h3>X2 — 50-pin bus</h3>")
    parts.append(conn_table(G.X2, G.X2_NC))
    parts.append("<h3>J3 — 34-pin IMU flex</h3>")
    parts.append(conn_table(G.J3))

    parts.append("<h3>IMU board parts and nets</h3>")
    parts.append(imu_table())
    parts.append("<h2 id=bom>5 · Parts list for a replica</h2>")
    parts.append(bom())

    parts.append("<h2 id=learn>6 · Replicating it as a learning project</h2>")
    parts.append('''<p>The original is a 6-layer, 0.4 mm-pitch BGA board — a poor <em>first</em> PCB. The electronics, however, split cleanly into stages that each produce a working board and reuse the pin tables above.</p>
<ol class="steps">
<li><b>Same brain, big pins.</b> STM32H743VIT6 (LQFP-100) or ZIT6 (LQFP-144) on a 2-layer board with FRAM, microSD, both crystals, LEDs, USB and an SWD header. Keep the pin functions from the table wherever the LQFP exposes them. Make your own PX4 board folder by copying <code>boards/px4/fmu-v6x</code> and editing <code>board.h</code>, <code>board_config.h</code>, <code>spi.cpp</code>, <code>timer_config.cpp</code> to your pins — the reverse of how these tables were produced.</li>
<li><b>One sensor domain.</b> Add one LDO with enable, one IMU on SPI1 with its DRDY line (ICM-42688-P is easier to buy than ICM-20649), one barometer on I²C. Learn decoupling, the rail-sense divider, and how <code>rc.board_sensors</code> starts drivers.</li>
<li><b>The bus.</b> Add the two DF40 connectors and a minimal base board (USB-C, 5 V in, one UART, buzzer, safety switch). Your module now fits any commercial Pixhawk Autopilot Bus base board — that is the real payoff of copying the standard.</li>
<li><b>Go BGA.</b> Move to the IIK6 package and 6 layers once you can get X-ray-inspected assembly. Compare against the open-hardware Holybro Pixhawk 6X and ARK V6X modules, which publish full schematics.</li>
</ol>
<h3>Things that bite</h3>
<ul class="tight">
<li><b>BOOT0</b> needs a 10 k pull-down and a reachable pad — you will use DFU at least once.</li>
<li><b>VCAP1/VCAP2</b> need low-ESR 2.2 µF right at the balls or the H7 will not start.</li>
<li><b>SD power switching</b> is not optional: PX4 power-cycles the card on error.</li>
<li><b>I²C pull-ups belong on the module</b> (DS-010) so a bare module never has floating buses.</li>
<li><b>DRDY lines must be EXTI-capable pins</b> as listed, or PX4 falls back to polling and IMU timing suffers.</li>
<li><b>Ground generously</b> through the DF40 GND pins and the four mounting holes; they return the 25 MHz SD and 50 MHz RMII currents.</li>
</ul>''')

    parts.append("<h2 id=src>7 · Sources</h2>")
    parts.append('''<div class="src">
<p>PX4-Autopilot, <code>boards/px4/fmu-v6x/</code>: <code>nuttx-config/include/board.h</code> (alternate-function pin map), <code>src/board_config.h</code> (GPIO, ADC, HW-ID, power control), <code>src/spi.cpp</code> (chip selects, DRDY, rail enables per hardware version), <code>src/i2c.cpp</code>, <code>src/timer_config.cpp</code> (PWM), <code>src/mtd.cpp</code> (FRAM/EEPROM), <code>init/rc.board_sensors</code> (drivers per hardware version, branch <code>V6X001</code>); <code>platforms/common/pab_manifest.c</code>; <code>platforms/nuttx/src/px4/stm/stm32_common/board_hw_info/board_hw_rev_ver.c</code> (ID ladder table).</p>
<p>Pixhawk SIG, <em>DS-010 Pixhawk Autopilot Bus Standard</em> (connector parts, X1/X2 pinouts, mechanics) and <em>DS-012 Pixhawk Autopilot FMUv6X Standard</em> (sensor sets, IMU flex pinout). PX4 user guide, <em>CUAV Pixhawk V6X</em>; CUAV, <em>Pixhawk V6X Controller Product Manual</em> (2023-11).</p>
<p>This is an independent reconstruction for study, not CUAV documentation. Where the DS-012 draft pinout sheet and the PX4 board files disagree, the PX4 files were taken as truth because this exact module boots them.</p>
</div>''')
    parts.append("</div>")
    out = os.path.join(HERE, "cuav_v6x_fmum_schematic.html")
    with open(out, "w") as f:
        f.write("\n".join(parts))
    print("wrote", out, os.path.getsize(out) // 1024, "KiB")


if __name__ == "__main__":
    build()
