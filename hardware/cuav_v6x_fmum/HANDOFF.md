# HANDOFF — CUAV V6X FMUM + IMU board replica, state as of 2026-09-12

Purpose of this document: complete context for a new session whose goal is to take the
two KiCad boards in this folder to **fabrication-ready** (Gerbers + assembly), with no
open items left. Everything below is fact about the current state; the "TO DO" section is
the work remaining.

---

## 1. What the hardware is

* Photos showed two boards. Board 1: 36 × 31.4 mm, silkscreen `V6X_FMUM RC11`, date
  07-17/23, CUAV logo. Board 2: ~25 × 18 mm octagon, silkscreen `V6X IMU RC10`, date
  2022-09-20, connected to board 1 by a 34-pin 0.4 mm flex ("FLEX").
* Identification: **CUAV Pixhawk V6X**. Board 1 is the FMU core module ("FMUM") that
  plugs into a base board through the **Pixhawk Autopilot Bus** (PAB): Hirose DF40
  100-pin (X1) + 50-pin (X2), 3 mm stack. Board 2 is CUAV's vibration-isolated IMU board.
* Firmware: PX4 target `px4_fmu-v6x`, hardware type **`V6X001`** ("CUAV sensor set rev 1",
  module ID resistor ladder 24.9k/442k). The base board is ID 2 (CUAV base).
* Processor STM32H743IIK6 (UFBGA176+25; PX4 defconfig says H753, same pinout).
* FMUM carries: MCU, FM25V02A FRAM (SPI5), microSD (SDMMC2), ICM-20649 (IMU 3, SPI1),
  ICP-20100 barometer #2 (I2C2, 0x63, in a routed stress-relief slot), 16 MHz + 32.768 kHz
  crystals, RTC backup cell, 3 LEDs, 3.3 V regulator, four switched sensor LDOs, HW-ID
  ladder, I2C pull-ups, likely NXP SE050 secure element (I2C4 0x48), BOOT0 pad, unpopulated
  ETM trace pads, test pads TP1-TP4/TP7.
* IMU board carries: BMI088 (IMU 1, SPI3), ICM-42688-P (IMU 2, SPI2), RM3100 compass =
  PNI MagI2C ASIC (I2C4 0x20) + 2× Sen-XY-f + 1× Sen-Z-f coils, ICP-20100 barometer #1
  (I2C4 0x64), 24LC64 calibration EEPROM (I2C4 0x50), heater = 4× 470 Ω (marked 4700,
  ~0805) switched low-side by a SOT-23 N-MOSFET marked 3400 (AO3400 class), gate from
  `HEATER` (PB10). No regulators; rails SENSORS2/3/4 and VDD_5V_IN arrive over the flex.
* **Not official.** CUAV publishes no schematics; Pixhawk FMUv6X reference schematics are
  Dronecode-member-only. Everything here is reconstructed.

## 2. Where everything is

Repo: `eloyf26/PX4-Autopilot`, branch **`claude/unknown-component-schematics-mdgis0`**,
folder **`hardware/cuav_v6x_fmum/`** (also delivered as a zip). Contents:

| Path | Role |
| --- | --- |
| `gen_schematic.py` | Source-of-truth tables: `PINS` (every used STM32 pin → function → net → destination, from PX4 board files), `X1`, `X2`, `J3` connector tables (from DS-010 / DS-012), `IMU_PARTS`, `X2_NC`. Also draws the 7 SVG sheets and writes `netlist.csv`. |
| `parts.py` | **Parts database used for KiCad**: every component with real package pin numbers, nets, board side (`F`/`B`), position (mm, top-view, origin top-left, y down), rotation. `FMUM_BOARD` / `IMU_BOARD` hold outline data. Loads ST ball map from `kicad/lib/STM32H743IIKx.xml`. |
| `gen_kicad.py` | Generates the two schematic projects from `parts.py` (embedded symbols, real pin numbers, global-label connectivity). |
| `gen_pcb.py` | Generates the two `.kicad_pcb` (outline, holes, slot, footprints from `kicad/lib/*.kicad_mod` or generated in-code, pads net-assigned, bottom-side footprints mirrored, UNROUTED). Contains a small s-expression parser/writer. |
| `kicad/fmum/cuav_v6x_fmum.kicad_pro` | FMU module project: root + `01_mcu`, `02_connectors`, `03_power_sensors`, `04_core` sheets + `cuav_v6x_fmum.kicad_pcb` (6 layers). |
| `kicad/imu/cuav_v6x_imu.kicad_pro` | IMU board project: root + `01_imu.kicad_sch` + `cuav_v6x_imu.kicad_pcb` (4 layers). |
| `kicad/lib/` | Official KiCad footprints (from kicad-footprints tag **8.0.8**, file version 20240108): SOIC-8, TSSOP-8, QFN-24 3×3 P0.4 EP1.75×1.6, QFN-24 4×4 P0.5 EP2.6, QFN-20 3×3 P0.4, LGA-14 3×2.5 P0.5, SOT-23/-5/-6, SOT-223, R/C 0402/0603/0805, LED 0603, Crystal 3225-4pin, 3215-2pin, 2016-4pin, microSD Molex 104031-0811, L 1210. Plus `STM32H743IIKx.xml` (ST open-pin-data ball map) and `stm32h743iikx_ballmap.json`. |
| `schematic/01…07_*.svg` | Human-readable schematic sheets (net-label style). |
| `netlist.csv` | 400 rows: refdes/pin/function/net/destination. |
| `README.md` | Full analysis, pin tables, trust table, BOM, replication advice. |
| `build_html.py`, `cuav_v6x_fmum_schematic.html` | Report (published artifact https://claude.ai/code/artifact/883c72e7-9c20-4462-bce4-4e600c60ca24). |
| `photos/` | 4 downscaled source photos. |

Regenerate everything: `python3 gen_schematic.py && python3 gen_kicad.py && python3 gen_pcb.py && python3 build_html.py`.
Validation used so far: `pip install kiutils` then parse every `.kicad_sch`/`.kicad_pcb`
(`kiutils.schematic.Schematic.from_file`, `kiutils.board.Board.from_file`). **KiCad itself was
never run** (not available in the environment). kicad-cli is not installed.

## 3. Sources and how the data was derived

* PX4 `boards/px4/fmu-v6x/`: `nuttx-config/include/board.h` (AF pin map), `src/board_config.h`
  (GPIO, ADC channels, HW-ID, power enables), `src/spi.cpp` (per-hardware-version CS/DRDY/rail
  enable), `src/i2c.cpp`, `src/timer_config.cpp` (PWM), `src/mtd.cpp` (FRAM, 24LC64),
  `init/rc.board_sensors` (V6X001 branch), `platforms/common/pab_manifest.c`,
  `platforms/nuttx/src/px4/stm/stm32_common/board_hw_info/board_hw_rev_ver.c` (ID ladder table:
  1: 24.9k/442k … 10: 442k/24.9k). **PX4 as-built pins were used wherever the DS-012 draft pinout
  sheet disagreed** (nARMED PE6, HW_VER_SENSE PH3 / HW_REV_SENSE PH4, NFC PC0, safety switch PF5,
  FMU_CH1-8 on TIM5/TIM4/TIM12, SDMMC2 D0/D1/D3 on PB14/PB15/PB4, SPI1_MISO PG9).
* Pixhawk DS-010 (PAB): X1/X2 pinout, connector parts DF40C-100DP-0.4V(51) / DF40C-50DP-0.4V(51)
  on the module (DF40HC(3.0)-…DS on the base), mechanical: 36.00 × 31.40 mm, R2.3 corners, 4×
  ∅2.0 holes with 3.6 pads at 2.30 mm from edges (GND), X1–X2 centre spacing 28.90 mm, X2 centre
  3.00 mm from the edge (bottom view), connector centres 14.50 mm from the bottom edge, LEDs at
  6.70/8.30/9.85 mm from left (blue/green/red), 2.30 mm from bottom; SD pin 1 at 20.25 mm.
  Pin 1/2 at the bottom end of X1 and X2, odd column on the left, in the bottom view.
* Pixhawk DS-012 (FMUv6X): sensor sets, IMU flex pinout (BM20B(0.8)-34DP-0.4V(53), p.17), FMUM
  reference layout picture (p.10) which CUAV's board matches (FLEX, TRACE, LEDs, SD, cell).
* Datasheets actually read for pin tables: Bosch BMI088 DS000 (table 14, landing pattern 8.2),
  TDK ICM-20649 DS-000192 (table 9, QFN-24 3×3, NC pins 1-6/14-17), TDK ICM-42688-P DS-000347
  (table 10, LGA-14), TDK ICP-20100 DS-000416 (table 18 + fig. 9, LGA-10 2×2, e=0.5, pad
  0.25×0.375), PNI RM3100/RM2100 user manual r06 (MagI2C table 4-1, 28-pin MLF 4×4 mm 0.4 mm
  pitch, do not solder die pad; Sen-XY-f pads 1.40×1.70 @ 5.30 c-c; Sen-Z-f pads 2.40×1.95, 0.40
  gap; Rbias 121 Ω ×6, REXT 33 kΩ; I2C ref schematic fig. 4-2). Datasheet mirrors that worked:
  Adafruit CDN (ICM-20649), mikroe (ICP-20100), github finani/ICM42688 (ICM-42688-P), tri-m.com
  (RM3100 manual), bosch-sensortec.com (BMI088). TDK and ST sites block direct download.
* ST ball map: `STMicroelectronics/STM32_open_pin_data` `mcu/STM32H743IIKx.xml` (201 balls).
  Notes: only `PC2_C`/`PC3_C` balls exist (M4/M5) — used for ADC1_6V6/ADC1_3V3; VCAP = F13, M10;
  VDD33_USB = H13; VREF+ P1, VREF- N1, VDDA R1, VSSA M1, VBAT C1, PDR_ON C6, BOOT0 D6, NRST J1.
* Photo scales: FMUM photos ≈36 px/mm (36 mm board); IMU top photo ≈42 px/mm, bottom ≈48 px/mm
  (calibrated on BMI088 4.5×3 mm and the PNI 6.5 mm coil). Positions in `parts.py` ±0.5 mm.

## 4. Decisions already taken (and why)

* FMUM PCB top (F.Cu) = SD-card side; MCU, X1, X2, ICM-20649, ICP-20100, crystals, main
  regulator, bottom-left LDO cluster on B.Cu. X1 at (31.9, 16.9) rot 270, X2 at (3.0, 16.9) rot
  270, J3 flex on top at (3.3, 15.9) rot 270 (directly opposite X2, as on the reference FMUM).
* U1 at (13.0, 14.4) B.Cu. Baro slot: U-shape 0.6 mm wide, centre-line (6.3,0.9)→(6.3,4.3)→
  (10.8,4.3)→(10.8,0.9); ICP-20100 #2 at (8.4,1.9) B.Cu inside it.
* Substitutes chosen for the replica: U2 3.3 V main rail = SOT-223 LDO (AP7361C-33 / AMS1117
  pinout GND/VOUT/VIN) **instead of the original switching regulator**; U3–U6 sensor LDOs =
  TLV75533PDBV (SOT-23-5: IN, GND, EN, NC, OUT); U7 microSD load switch = SOT-23-5 with the same
  IN/GND/ON/NC/OUT pinout (TPS22919/SiP32431 class — pinout NOT verified); BT1 = Seiko MS621FE
  footprint (2 pads ±4.5 mm, approximate); D4 BAT54 SOD-323 + R30 1k charge path; LEDs 0603
  (pad 1 = cathode) with 470 Ω; J4 microSD = Molex 104031-0811 library footprint standing in for
  the original Molex 5031821852 (same contact order).
* U11 SE050: QFN-20 3×3 P0.4 footprint placed at (23.3, 11.4) F.Cu with **all pads unassigned**
  (pinout not obtained). PX4 boots without it.
* X2 pin 50 ("PH11" in DS-010) is wired to FMU_CH3 (same MCU pin). PI6 (BMI088 accel INT1) left
  open: not on the flex in this sensor set. PD15 spare open. X2 spares/CAN3/FMU_CH9-12/ETH_RX_ER/
  ETH_PHY_nINT open (standard reserves, not connected on FMUv6X).
* IMU board: J1 = mating BM20 half at (16.7, 9.4) B.Cu rot 90 (pin 1 orientation NOT verified);
  U1 BMI088 (9.4,4.0) F rot 90; U2 ICM-42688-P (8.2,8.8) F; U3 MagI2C (14.5,6.4) F; L1 X coil
  (15.5,2.6) F horizontal; L2 Y coil (15.8,13.6) F rot 90; L3 Z coil (12.5,12.3) F; U4 ICP-20100
  #1 (8.6,13.5) F; U5 24LC64 (10.1,5.7) B; Q1 (5.6,9.2) B; R1-R4 heater 0805 at the four corners
  on B; outline octagon 25×18 with chamfers 4.8 (x) × 4.0 (y), notches r1.5 top/bottom centre,
  ∅2.2 NPTH at (2.2,9.0) and (22.8,9.0), 1.6 mm GND pads M1-M4.
* Generated (non-library) footprints in `gen_pcb.py`: BGA176+25 (0.30 mm pads, exact grid),
  DF40C-100/50DP (pads 0.20×0.90 at ±1.30 mm rows, 0.4 pitch, 2 mount pads — geometry
  APPROXIMATE), BM20B-34 (0.22×0.90 at ±1.35 — APPROXIMATE), ICP-20100 LGA-10 (positions from
  datasheet figure, pads 0.30×0.45), BMI088 LGA-16 (0.25×0.75 top/bottom rows at ±1.30,
  side pads 0.70×0.25 at ±1.90 — from datasheet landing pattern numbers, check), MagI2C MLF-28
  4×4 0.4 mm (pads 0.2×0.75, no EP), Sen-XY-f, Sen-Z-f, MS621, SOD-323, test pad ∅1.0,
  TRACE 8×(0.45×1.5 @0.7 mm) + 2 mount pads, mounting hole ∅2.0/3.6 GND, NPTH ∅2.2, GND pad ∅1.6.
* Bottom-side footprints are written with x-mirrored pad/graphic coordinates, negated angles,
  F./B. layers swapped (KiCad "flip left/right" convention); pad angles are footprint-relative
  (KiCad 7+ file semantics). Footprint rotation stored in `(at x y rot)`.

## 5. Validation status

* All 6 schematic files and both PCB files parse with kiutils. FMUM: 96 footprints, 670 pads,
  588 net-assigned, 150 nets; IMU: 37 footprints, 171 pads, 154 assigned, 33 nets. No
  single-ended nets in either schematic; every schematic net exists on its board.
* A home-made plot of the PCBs (pads + outline) was checked visually: no gross collisions after
  fixes; X1/X2 pin 1 at bottom end, odd pins left in bottom view.
* **Never opened in KiCad. ERC/DRC never run. Nothing routed.**

## 6. TO DO to reach fabrication-ready (ordered)

1. **Open both projects in KiCad 8/9** and fix any load errors. Run *Update PCB from schematic*
   both ways to confirm symbol/footprint pad numbers agree (U1 ball names, connectors, all ICs).
   Run ERC and DRC; resolve everything except the intentional opens listed in §4.
2. **Verify every generated footprint against the manufacturer drawing** and fix pad geometry in
   `gen_pcb.py`: Hirose DF40C-100DP-0.4V(51) and DF40C-50DP-0.4V(51) (plug side!), Hirose
   BM20B(0.8)-34DP/DS-0.4V (decide which half sits on which board; a flex jumper with the
   complementary halves is needed), BMI088 LGA-16, ICP-20100 LGA-10, PNI MagI2C MLF-28 and both
   coils (manual figs 3-3/3-6/3-7), MS621FE cell, SOD-323, trace/test pads. Confirm pin-1
   orientation of J3 (FMUM) and J1 (IMU) from the Hirose drawings + DS-012 p.10 figure.
3. **Resolve the substitutes**: pick and verify U2 (either a real buck like the original, or an
   LDO with thermal check at ~400 mA/1.7 V drop), U7 load-switch pinout, U3-U6 LDO part, BT1 cell
   part and footprint. Decide SE050: obtain the HX2QFN20 pinout and assign nets
   (SDA=I2C4_SDA_FMU, SCL=I2C4_SCL_FMU, VDD/VIN/ENA=FMU_VDD_3V3, GND) or delete U11.
4. **Complete the circuit details** a fab-ready design needs: one 100 nF per U1 VDD ball
   (only 12 placed) + 4.7 µF bulk ×2, 2.2 µF on each VCAP ball adjacent to F13/M10, ferrite +
   1 µF on VDDA/VREF+, 100 nF on VDD33_USB, pull-downs on the four LDO EN lines and on
   VDD_3V3_SD_CARD_EN, 10 k pull-up on the HEATER gate line optional, ESD/series parts belong on
   the base board (none needed on the module), decoupling on every IMU-board IC per datasheet
   (BMI088 VDD/VDDIO 100 nF; ICM-42688-P VDD 100 nF + VDDIO 100 nF; MagI2C AVDD 10 µF + 100 nF,
   DVDD 100 nF; ICP-20100 100 nF each on VDD/VDDIO; 24LC64 100 nF). Check heater power
   (4×470 Ω ∥ = 117 Ω → 0.21 W at 5 V) versus what CUAV likely uses; confirm resistor size.
5. **Mechanical**: measure or confirm PCB thicknesses (DF40 3 mm stack assumes the standard
   DF40C/DF40HC(3.0) pair; PCB thickness does not affect stack), IMU board outline and hole
   positions against the physical part (all estimated), mounting-hole diameters, slot width,
   keep-out under the BGA for the heatsink case (DS-010 wants heat-sinking of U1), component
   heights under the module (max 3 mm minus PCB), flight-direction arrow and sensor rotations
   (PX4 uses -R 14 for ICM-20649, -R 6 ICM-42688-P, -R 4 BMI088 relative to the arrow — the
   replica must keep the chips oriented the same way or the parameters must change).
6. **Stackup and rules** (FMUM): 6 layers, e.g. Sig / GND / Sig / Sig / PWR / Sig; 0.65 mm BGA
   escape needs 0.1 mm track/0.1 mm clearance, 0.2 mm drill / 0.4-0.45 mm via (or µvias),
   ENIG finish, 0.30 mm NSMD pads. IMU: 4 layers, GND planes both inner. Set net classes for
   USB (D+/D−, 90 Ω diff, kept short to X1), RMII (50 Ω, length-matched, all 6 signals), SDMMC
   (25 MHz, matched), SPI1/2/3 with DRDY, I2C. Keep no vias/traces under BMI088 (Bosch) and keep
   the baro island copper-free except its pads.
7. **Route** both boards. Priorities: BGA fan-out, crystals right at PH0/PH1 and PC14/PC15 with
   ground guard, USB and RMII straight to X1/X2, sensor domains kept apart, GND stitching around
   the DF40 connectors, heater traces sized for 45 mA, coil traces short and symmetric.
8. **Outputs**: Gerbers + drill (RS-274X, 2-layer drill files), pick-and-place (both sides), BOM
   with manufacturer part numbers (export from schematic; fill the `Value` fields with real MPNs
   first), assembly drawings, fab notes (impedance, ENIG, solder-mask defined pads for BGA if
   chosen, no clean for MEMS, panelization with mouse-bites away from the baro slot).
9. **Bring-up plan**: flash `px4_fmu-v6x_bootloader` over SWD (X1-75/77, NRST X1-87) or DFU via
   BOOT0 pad; the module needs a real PAB base board (CUAV V6X base, Holybro 6X base, or ARK
   PAB carrier) to get 5 V, USB and IDs; check that PX4 detects `V6X001` from the 24.9k/442k
   ladder and starts icm20649/icm42688p/bmi088/rm3100/icp201xx.
10. **Legal**: "Pixhawk" is a registered trademark usable only with an adopter agreement; sell or
    publish the replica without the name.

## 7. Known uncertainties to keep in mind

* Blue 1.5 mm part marked `IY2K` on the FMUM (near the IMU) unidentified (probably TVS/ESD or
  tiny LDO). Test pads TP2/TP3/TP4/TP7 nets unknown. TP1 = BOOT0 (`BT0`).
* The photo suggested X1 about 6.9 mm from the edge while DS-010 gives 4.1 mm; the standard was
  trusted (perspective in the photo). Verify against a physical module if available.
* ICM-20649 rotation -R 14 (ROLL_180_YAW_270), consistent with it being on the bottom side.
* The IMU board's two through-holes plus M1-M4 pads are the elastomer isolation-mount interface;
  their exact geometry drives the enclosure fit.
* Routing of the original is 6 layers with inner-layer planes; none of it is recoverable from
  the photos.

## 8. Suggested opening prompt for the new session

"Continue the CUAV V6X FMUM + IMU board replica in `hardware/cuav_v6x_fmum/` on branch
`claude/unknown-component-schematics-mdgis0` of eloyf26/PX4-Autopilot. Read HANDOFF.md first.
Goal: both KiCad boards fabrication-ready (ERC/DRC clean, verified footprints, complete
decoupling, routed, Gerbers, BOM with MPNs, pick-and-place), no open items. Work through §6 of
HANDOFF.md in order and keep `parts.py`/`gen_pcb.py` as the source of truth until routing
starts; after routing, the `.kicad_pcb` files become the source of truth."
