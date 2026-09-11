# CUAV V6X FMUM — what the board is, and a reverse-engineered schematic

Two photos of a small green 36 × 31 mm board, silkscreened **`V6X_FMUM RC11`**, a
CUAV logo and the date code **07-17/23**. This folder identifies it, explains every
visible part, and reconstructs its schematic well enough to build a compatible
replica.

| File | What it is |
| --- | --- |
| `README.md` | this document |
| `kicad/cuav_v6x_fmum.kicad_pro` | **KiCad 8 project** — open this; five hierarchical sheets, nets carried by global labels |
| `schematic/01…07_*.svg` | seven schematic sheets (MCU, core peripherals, power + sensors, X1, X2, IMU flex, IMU board) |
| `netlist.csv` | every MCU pin / connector pin / IMU-board pin → net → destination, machine readable |
| `gen_schematic.py` | the single data table the sheets, netlist and KiCad project are generated from |
| `gen_kicad.py`, `build_html.py` | generators for the KiCad project and the HTML report |
| `cuav_v6x_fmum_schematic.html` | self-contained report (same content as the published artifact) |
| `photos/` | the four source photos (FMU module and IMU board), downscaled |

> **Are these the official schematics? No.** CUAV does not publish the schematic of
> the V6X modules, and the full Pixhawk FMUv6X reference schematics are available only
> to Dronecode Foundation members. Everything here is an independent reconstruction.
> Connectivity is derived from the firmware that runs on this exact hardware, so it is
> reliable; part choices for regulators and passives are engineering substitutes.

> **Provenance / confidence.** No vendor schematic of this module is public. The
> schematic below was rebuilt from three sources that describe this exact hardware:
> (1) the PX4 board support package the module runs
> (`boards/px4/fmu-v6x`, hardware type `V6X001` = "CUAV sensor set rev 1"), which
> hard-codes every MCU pin, bus, chip-select, address and power-enable;
> (2) the two public Pixhawk standards the module implements, DS-010 *Pixhawk
> Autopilot Bus* (the 100- and 50-pin connector pinouts) and DS-012 *Pixhawk
> Autopilot FMUv6X* (sensor sets, the 34-pin IMU flex pinout, mechanical drawing);
> (3) the photos, for placement, packages and markings.
> Pin-to-net connectivity is therefore high confidence. Passive values, regulator
> part numbers and a few small ICs are educated engineering choices and are
> marked as such.

---

## 1. Identification

**It is the FMU core module ("FMUM") of the CUAV Pixhawk V6X flight controller.**

The Pixhawk V6X is a modular autopilot: a *base board* (all the JST-GH connectors,
power selection, CAN/USB/Ethernet transceivers, the STM32F103 IO co-processor) and a
plug-in *FMU module* carrying the main processor, storage and part of the sensor set.
The two boards meet through the **Pixhawk Autopilot Bus (PAB)**: one 100-pin and one
50-pin Hirose DF40 connector with a 3 mm stack height. Your board is the plug-in
module. CUAV sells the V6X either complete or as this "core" alone (43 g, 36 × 31.4 mm
per the standard's mechanical drawing, which the photos match to the millimetre:
four 2.0 mm grounded mounting holes, R2.3 corners, LEDs and SD slot in the
standardised positions).

Everything on it maps to the standard's reference module drawing (DS-012 p.10,
"FMUv6X FMUM"): same FLEX connector position, same TRACE pad footprint, same
LED/SD/battery placement. CUAV re-laid the board but kept the reference architecture.

### What the photos show

**Photo 1 — MCU side (this is the *bottom* of the module; it faces the base board)**

| What you see | What it is | Confidence |
| --- | --- | --- |
| 10 × 10 mm BGA marked ARM / `STM32H7…IIK6` | **U1, STM32H743IIK6** (or H753, the crypto variant PX4 is configured for). Cortex-M7 at 480 MHz, 2 MB flash, 1 MB RAM, UFBGA176+25 package. | high |
| 100-pin fine-pitch connector, left | **X1** Hirose DF40C-100DP-0.4V — the main Pixhawk Autopilot Bus | high |
| 50-pin fine-pitch connector, right | **X2** Hirose DF40C-50DP-0.4V — Ethernet RMII + external SPI bus | high |
| 3 × 3 mm QFN, top centre | **ICM-20649** 6-axis IMU (#3), on SPI1 — the one "hard mounted" IMU of the set | high (from firmware; size matches QFN-24 3×3) |
| tiny metal-lidded part with a port hole, sitting in a U-shaped routed slot, top right | **ICP-20100** barometer (#2), on I2C2 at 0x63. The slot is stress relief: board flex would otherwise read as pressure. | high (2 × 2.5 mm metal-lid LGA is unique to a baro) |
| two small metal cans left of the MCU (`TW2…` rectangular, `A-T` square) | **Y1 16 MHz** HSE crystal (3225) and **Y2 32.768 kHz** RTC crystal | high (PX4 board.h: 16 MHz HSE, 32.768 kHz LSE) |
| small blue 1.5 mm part marked `IY2K`, right of the IMU | small passive/IC, probably an ESD/TVS array or a tiny LDO for the sensor domain | low |
| QFN + large inductor + capacitors, bottom centre | **U_REG**, the module's 5 V → 3.3 V step-down for `FMU_VDD_3V3` | medium |
| SOT-23-5 ICs and clusters of 0402 capacitors along the right edge | the four **switched sensor LDOs** (`VDD_3V3_SENSORS1…4`) with their decoupling | medium |
| `TP1` | test pad | — |
| ladders of 0402 resistors bottom right | hardware-ID resistor ladders + I²C pull-ups (1.5 kΩ, required on the module by DS-010) | medium |

**Photo 2 — SD-card side (the *top* of the module; visible when installed)**

| What you see | What it is | Confidence |
| --- | --- | --- |
| `CUAV`, `V6X_FMUM RC11`, `07-17/23`, arrow | vendor, board name (V6X **F**light **M**anagement **U**nit **M**odule), layout revision RC11, build date; the arrow is the flight direction reference for the IMUs | high |
| 34-pin connector labelled `FLEX`, left | **J3** Hirose BM20B(0.8)-34DP-0.4V, FPC to CUAV's separate, vibration-isolated **IMU board** (BMI088, ICM-42688-P, RM3100, ICP-20100 #1, calibration EEPROM). That is why the "triple-redundant IMU" is not visible here: two of the three IMUs and the compass live on the other board. | high |
| microSD push-push slot marked `molex 2011EC` | **J4** microSD, SDMMC2 4-bit, PX4 logs go here | high |
| SOIC-8, top centre | **FM25V02A** 256 kbit FRAM (SPI5) — PX4 parameter storage. FRAM is used instead of flash because it survives millions of writes and needs no erase. | high |
| 3 × 3 mm QFN marked `S50 08 07 AD307`, right of the SD slot | most likely **NXP SE050** secure element (I2C4, 0x48) — it is in the FMUv6X reference sensor set and PX4 defines its address for this board | medium |
| round metal can marked `L03`, bottom right | **B1**, RTC backup cell (rechargeable lithium coin/cylinder). Keeps the clock and backup SRAM alive without main power; exported to the base on X1-29. | high (role) / medium (exact part) |
| three 0603 LEDs bottom left | **D1 red, D2 green, D3 blue** status LEDs (PE3/PE4/PE5, active-low) | high |
| row of 8 pads + 2 large pads, bottom left | unpopulated **J1 TRACE** footprint (Cortex-M ETM trace: TRACECLK + TRACED0-3) | high |
| `BT0` pad | **BOOT0** — bridge to 3.3 V at power-up to enter the STM32 ROM (DFU) bootloader | high |
| `TP2 TP3 TP4 TP7` | test pads (nets unknown) | — |
| SOT-23 / 0603 parts around the right edge | the remaining sensor LDO and its decoupling, RTC charging diode + resistor | medium |

### Sensor set of this exact revision (from `boards/px4/fmu-v6x/init/rc.board_sensors`, branch `V6X001`)

| Sensor | Part | Bus | CS / address | DRDY | Power domain | Where |
| --- | --- | --- | --- | --- | --- | --- |
| IMU 1 | Bosch **BMI088** (accel + gyro) | SPI3 | PI4 (accel), PI8 (gyro) | PI7 (gyro INT3) | `VDD_3V3_SENSORS3` | IMU board via J3 |
| IMU 2 | TDK **ICM-42688-P** | SPI2 | PH5 | PA10 | `VDD_3V3_SENSORS2` | IMU board via J3 |
| IMU 3 | TDK **ICM-20649** | SPI1 | PI9 | PF2 | `VDD_3V3_SENSORS1` | **this module** |
| Compass | PNI **RM3100** | I2C4 | 0x20 | — | `VDD_3V3_SENSORS4` | IMU board via J3 |
| Baro 1 | TDK **ICP-20100** | I2C4 | 0x64 | — | `VDD_3V3_SENSORS4` | IMU board via J3 |
| Baro 2 | TDK **ICP-20100** | I2C2 | 0x63 | PG5 (optional) | `VDD_3V3_SENSORS2` | **this module** |
| Cal EEPROM | 24LC64 | I2C4 | 0x50 | — | `VDD_3V3_SENSORS4` | IMU board via J3 |
| Parameters | **FM25V02A** FRAM | SPI5 | PG7 | — | `FMU_VDD_3V3` | **this module** |
| Secure element | NXP **SE050** | I2C4 | 0x48 | — | `FMU_VDD_3V3` | **this module** (likely) |

### The second board: `V6X IMU RC10` (2022-09-20)

The octagonal board on the other end of the FLEX cable is CUAV's **IMU board**. It sits
in an elastomer isolation mount (the two half-round notches and the four M1-M4 ground
pads are the mount interface), which is why it is a separate PCB at all: the inertial
sensors ride on a damped mass, while the processor board is bolted rigidly to the base.
It contains no regulators; all its power arrives over the flex.

| What you see | What it is | Confidence |
| --- | --- | --- |
| rectangular LGA, top left, sensor side | **Bosch BMI088** accel + gyro (IMU 1, SPI3) | high (package 3 × 4.5 mm, firmware) |
| small 3-row-marked LGA below it | **TDK ICM-42688-P** (IMU 2, SPI2) | high |
| 4 × 4 mm QFN, centre right | **PNI MagI2C**, the RM3100 compass controller (I2C4, 0x20) | high |
| two flat black bars marked `PNI`, one horizontal one vertical | **PNI Sen-XY-f** sense coils for the X and Y magnetic axes (mounted at 90°) | high |
| black cube below the QFN | **PNI Sen-Z-f** coil, Z axis | high |
| metal lid with port hole, bottom left | **TDK ICP-20100** barometer #1 (I2C4, 0x64) | high |
| white arrow | flight-direction reference for the IMU axes | high |
| flex side: 34-pin 0.4 mm connector `FLEX` | mating half of the FMUM's J3 (BM20 series); an FPC jumper links the two | high |
| flex side: SOIC-8 | **24LC64** calibration EEPROM (I2C4, 0x50; PX4 `imu_eeprom`: cal data, MFT revision, ID) | high |
| flex side: four large resistors marked `4700` | **470 Ω heater resistors**, paralleled (117 Ω across 5 V ≈ 0.21 W) | high |
| flex side: SOT-23 marked `3400` next to a resistor silkscreen symbol | **N-MOSFET (AO3400 class)**, low-side switch for the heater, gate on the `HEATER` line | high |
| remaining 0402/0603 parts | decoupling, gate pull-down | — |

Sheet `07_imu_board.svg` (and KiCad sheet 5) draws it. Because the flex pinout is fixed by
the standard, the IMU board and the FMU module are individually replaceable; the
sensor rotations PX4 applies (`-R 4` BMI088, `-R 6` ICM-42688-P, `-R 14` ICM-20649) encode how
each chip is oriented relative to the arrow.

---

## 2. How the module works (architecture)

```
             base board                        ┃  FMU module (this board)                         ┃  IMU board (flex)
                                               ┃                                                   ┃
  power path selector ── VDD_5V_IN ────────────╋──► U_REG 3.3 V ──► FMU_VDD_3V3 ──► U1 STM32H7     ┃
  (2 bricks + USB)      X1-49/51/53/55         ┃      │                     ├──► FM25V02A FRAM (SPI5) ┃
                                               ┃      │                     ├──► SE050 (I2C4)        ┃
                                               ┃      │                     ├──► microSD (SDMMC2, switched by PC13)
                                               ┃      ├──► LDO1 (PI11) ──► ICM-20649  (SPI1)        ┃
                                               ┃      ├──► LDO2 (PF4)  ──► ICP-20100 #2 (I2C2) ─────╋──► ICM-42688-P (SPI2)
                                               ┃      ├──► LDO3 (PE7)  ────────────────────────────╋──► BMI088 (SPI3)
                                               ┃      └──► LDO4 (PG8)  ────────────────────────────╋──► RM3100, ICP-20100 #1, EEPROM (I2C4)
  UARTs, CAN, USB, PWM, I2C1-3, ADC, IDs ◄─────╋── X1 (100 pins) ── U1 GPIO/peripherals             ┃      HEATER (PB10) ◄── J3-30
  LAN8742A PHY (RMII), payload SPI6 ◄──────────╋── X2 (50 pins)                                    ┃
```

Key ideas worth understanding before you copy it:

* **One supply in, everything else generated locally.** Only `VDD_5V_IN` enters (four
  pins for current). A step-down makes `FMU_VDD_3V3` for the MCU and memories, and that
  rail is *exported* on X1-84/86 so the base can run its own small logic from it.
* **Four independent sensor power domains.** Each IMU/compass group has its own 3.3 V
  LDO with an MCU-controlled enable and a 1:2 resistor divider read by the ADC. PX4 can
  power-cycle a misbehaving sensor domain without touching the others and can detect a
  sagging rail. This is the "three redundancy domains" design of FMUv6X.
* **Separate buses per IMU.** SPI1, SPI2, SPI3 each carry exactly one IMU (plus a data-ready
  interrupt line), so a hung device cannot block the others. I2C4 is the internal
  sensor I²C (compass, baro 1, EEPROM, secure element). I2C1/2/3 go out to the base for
  GPS/compass pucks and power monitors; baro 2 rides on I2C2 locally.
* **Storage:** FRAM for parameters (byte-writable, non-volatile), microSD for logs, backup
  SRAM + RTC kept alive by B1.
* **Hardware identification without firmware changes.** At boot PG0 drives 3.3 V into two
  resistor ladders; ADC3 reads the divider voltages. PH4 reads the *module* ladder
  (24.9 k / 442 k → ID 1 → "CUAV sensor set rev 1"), PH3 reads the *base board* ladder via
  X1-27. PX4 then starts exactly the right drivers with the right axis rotations.
* **Everything analog-ish that touches the outside world stays on the base**: USB/CAN
  transceivers, RS-232-level shifters, PHY magnetics, power switching, ESD. Only 3.3 V
  logic crosses X1/X2. That is what makes the module small and reusable.

---

## 3. Schematic sheets

### KiCad

Open `kicad/cuav_v6x_fmum.kicad_pro` in KiCad 8 (7 also reads it). The root sheet holds
five hierarchical sheets: MCU, bus connectors, power and sensors, core peripherals,
IMU board. Every connection is a **global label**, so the netlist, highlighting
(click a label, press backtick) and ERC work immediately; there are no drawn wires,
which is the fastest way to *read* a dense design and the normal way FMU-class
schematics are drawn anyway. Symbols are embedded in each sheet (no external library
needed). Notes for working with it:

* U1's pin numbers are the port names (`PA0`…) because the ball map is not included.
  When you go to layout, use *Change Symbol* to the library part
  `MCU_ST_STM32H7:STM32H743IIKx`, which has identical pin names and the real ball numbers.
* Footprints are pre-filled where a standard KiCad footprint exists (DF40, SOIC-8, QFN,
  SOT-23-5, microSD, UFBGA-176). Substitute parts (regulators, LDOs, load switch) have
  none until you pick a part.
* ERC will report the intentionally open pins (X2 spares, ICM-20649 FSYNC, BMI088 unused
  INT pins) and a few "power pin not driven" notes on rails that come from the base board.
* Regenerate after editing the tables: `python3 gen_kicad.py`.

### SVG sheets

Open the SVGs in `schematic/` (any browser or Inkscape). Net labels
follow the Pixhawk standard names so they line up with the published base-board
examples.

| Sheet | Content |
| --- | --- |
| `01_mcu_u1.svg` | U1 with every used pin: peripheral function inside, net outside, destination in the margin |
| `02_core_peripherals.svg` | FRAM, SE050, microSD + load switch, crystals, RTC cell, LEDs, USB, HW-ID ladder, BOOT0/NRST/TRACE |
| `03_power_and_sensors.svg` | 3.3 V step-down, four sensor LDOs with dividers, ICM-20649, ICP-20100 #2, heater line, I²C pull-ups |
| `04_x1_pab_100pin.svg` | X1 pin-by-pin with the MCU pin on each signal |
| `05_x2_pab_50pin.svg` | X2 pin-by-pin (RMII, SPI6, spares) |
| `06_j3_imu_flex_34pin.svg` | J3 IMU flex pin-by-pin |
| `07_imu_board.svg` | the IMU board: BMI088, ICM-42688-P, RM3100 (MagI2C + 3 coils), ICP-20100 #1, 24LC64, heater |

### Full MCU pin map (as used by PX4 on this module)

Column "goes to" uses the same vocabulary as the sheets: `X1-nn`, `X2-nn`, `J3-nn`, or an on-module part.

| Pin | Function | Net | Goes to |
| --- | --- | --- | --- |
| PA0 | ADC1_INP16 | SCALED_VDD_3V3_SENSORS1 | divider on sensor rail 1 |
| PA1 | ETH_REF_CLK | ETH_REF_CLK | X2-3 |
| PA2 | ETH_MDIO | ETH_MDIO | X2-2 |
| PA3 | USART2_RX | USART2_RX_TELEM3 | X1-42 |
| PA4 | ADC12_INP18 | SCALED_VDD_3V3_SENSORS2 | divider on sensor rail 2 |
| PA5 | SPI1_SCK | SPI1_SCK_SENSOR1 | ICM-20649 SCLK |
| PA6 | SPI6_MISO | SPI6_MISO_EXTERNAL1 | X2-31 |
| PA7 | ETH_CRS_DV | ETH_CRS_DV | X2-7 |
| PA8 | I2C3_SCL | I2C3_SCL_BASE | X1-10 |
| PA9 | OTG_FS_VBUS | VBUS_SENSE | X1-80 |
| PA10 | GPIO/EXTI | SPI2_DRDY2_IMU2_INT2 | J3-31 |
| PA11 | OTG_FS_DM | USB_D_N | X1-78 |
| PA12 | OTG_FS_DP | USB_D_P | X1-76 |
| PA13 | SWDIO | FMU_SWDIO | X1-75 |
| PA14 | SWCLK | FMU_SWCLK | X1-77 |
| PA15 | GPIO | SPI6_nCS2_EXTERNAL1 | X2-43 |
| PB0 | ADC12_INP9 | SCALED_VDD_3V3_SENSORS3 | divider on sensor rail 3 |
| PB1 | ADC12_INP5 | SCALED_V5 | divider on VDD_5V_IN |
| PB2 | SPI3_MOSI | SPI3_MOSI_SENSOR3 | J3-14 |
| PB3 | SPI6_SCK / SWO | SPI6_SCK_EXTERNAL1 | X2-35 |
| PB4 | SDMMC2_D3 | SD_D3 | microSD |
| PB5 | SPI1_MOSI | SPI1_MOSI_SENSOR1 | ICM-20649 SDI |
| PB6 | USART1_TX | USART1_TX_GPS1 | X1-36 |
| PB7 | USART1_RX | USART1_RX_GPS1 | X1-34 |
| PB8 | I2C1_SCL | I2C1_SCL_BASE | X1-18 |
| PB9 | I2C1_SDA | I2C1_SDA_BASE | X1-16 |
| PB10 | GPIO (TIM2_CH3) | HEATER | J3-30 |
| PB11 | ETH_TX_EN | ETH_TX_EN | X2-27 |
| PB12 | FDCAN2_RX | CAN2_RX | X1-59 |
| PB13 | FDCAN2_TX | CAN2_TX | X1-57 |
| PB14 | SDMMC2_D0 | SD_D0 | microSD |
| PB15 | SDMMC2_D1 | SD_D1 | microSD |
| PC0 | GPIO/EXTI | NFC_GPIO | X2-48 |
| PC1 | ETH_MDC | ETH_MDC | X2-4 |
| PC2 | ADC3_INP12 | ADC1_6V6 | X1-90 |
| PC3 | ADC3_INP13 | ADC1_3V3 | X1-92 |
| PC4 | ETH_RXD0 | ETH_RXD0 | X2-11 |
| PC5 | ETH_RXD1 | ETH_RXD1 | X2-15 |
| PC6 | USART6_TX | USART6_TX_TO_IO | X1-72 |
| PC7 | USART6_RX | USART6_RX_FROM_IO_RC | X1-70 |
| PC8 | UART5_RTS | UART5_RTS_TELEM2 | X1-58 |
| PC9 | UART5_CTS | UART5_CTS_TELEM2 | X1-60 |
| PC10 | SPI3_SCK | SPI3_SCK_SENSOR3 | J3-10 |
| PC11 | SPI3_MISO | SPI3_MISO_SENSOR3 | J3-12 |
| PC12 | UART5_TX | UART5_TX_TELEM2 | X1-52 |
| PC13 | GPIO | VDD_3V3_SD_CARD_EN | SD load switch |
| PC14/PC15 | OSC32 | 32 kHz crystal | Y2 |
| PD0 | FDCAN1_RX | CAN1_RX | X1-65 |
| PD1 | FDCAN1_TX | CAN1_TX | X1-63 |
| PD2 | UART5_RX | UART5_RX_TELEM2 | X1-54 |
| PD3 | USART2_CTS | USART2_CTS_TELEM3 | X1-48 |
| PD4 | USART2_RTS | USART2_RTS_TELEM3 | X1-46 |
| PD5 | USART2_TX | USART2_TX_TELEM3 | X1-40 |
| PD6 | SDMMC2_CK | SD_CLK | microSD |
| PD7 | SDMMC2_CMD | SD_CMD | microSD |
| PD8 | USART3_TX | USART3_TX_DEBUG | X1-69 |
| PD9 | USART3_RX | USART3_RX_DEBUG | X1-71 |
| PD10 | GPIO | FMU_nSAFETY_SWITCH_LED_OUT | X1-23 |
| PD11 | GPIO | SPI6_DRDY1_EXTERNAL1 | X2-47 |
| PD12 | GPIO | SPI6_DRDY2_EXTERNAL1 | X2-45 |
| PD13 | TIM4_CH2 | FMU_CH5 | X1-7 |
| PD14 | TIM4_CH3 | FMU_CH6 | X1-5 |
| PD15 | GPIO | spare | n.c. |
| PE0 | UART8_RX | UART8_RX_GPS2 | X1-30 |
| PE1 | UART8_TX | UART8_TX_GPS2 | X1-28 |
| PE2 | TRACECLK | TRACECLK | J1 pad 1 |
| PE3 | GPIO, open drain | nLED_RED | D1 (+ J1 pad 3) |
| PE4 | GPIO, open drain | nLED_GREEN | D2 (+ J1 pad 5) |
| PE5 | GPIO, open drain | nLED_BLUE | D3 (+ J1 pad 7) |
| PE6 | GPIO | nARMED | X1-85 (+ J1 pad 8) |
| PE7 | GPIO | VDD_3V3_SENSORS3_EN | LDO3 EN |
| PE8 | UART7_TX | UART7_TX_TELEM1 | X1-64 |
| PE9 | GPIO | SPIX_SYNC | X2-49 |
| PE10 | UART7_CTS | UART7_CTS_TELEM1 | X1-24 |
| PE11 | TIM1_CH2 capture | FMU_CAP1 | X1-97 |
| PE15 | GPIO | VDD_5V_PERIPH_nOC | X1-37 |
| PF0 | I2C2_SDA | I2C2_SDA_BASE | X1-12 + ICP-20100 #2 |
| PF1 | I2C2_SCL | I2C2_SCL_BASE | X1-14 + ICP-20100 #2 |
| PF2 | GPIO/EXTI | SPI1_DRDY1_IMU3_INT1 | ICM-20649 INT1 |
| PF4 | GPIO | VDD_3V3_SENSORS2_EN | LDO2 EN |
| PF5 | GPIO, pull-up | FMU_SAFETY_SWITCH_IN | X1-21 |
| PF6 | UART7_RX | UART7_RX_TELEM1 | X1-66 |
| PF7 | SPI5_SCK | SPI5_SCK_FRAM | FRAM SCK |
| PF8 | UART7_RTS | UART7_RTS_TELEM1 | X1-22 |
| PF9 | TIM14_CH1 | BUZZER_1 | X1-4 |
| PF10 | GPIO | SPI6_nRESET_EXTERNAL1 | X2-39 |
| PF11 | SPI5_MOSI | SPI5_MOSI_FRAM | FRAM SI |
| PF12 | ADC1_INP6 | SCALED_VDD_3V3_SENSORS4 | divider on sensor rail 4 |
| PF13 | GPIO | VDD_5V_HIPOWER_nOC | X1-83 |
| PF14 | I2C4_SCL | I2C4_SCL_FMU | J3-7 + SE050 |
| PF15 | I2C4_SDA | I2C4_SDA_FMU | J3-5 + SE050 |
| PG0 | GPIO | HW_VER_REV_DRIVE | X1-25 + module ID ladder |
| PG1 | GPIO, pull-up | nPOWER_IN_A | X1-89 |
| PG2 | GPIO, pull-up | nPOWER_IN_B | X1-91 |
| PG3 | GPIO, pull-up | nPOWER_IN_C | X1-93 |
| PG4 | GPIO | VDD_5V_PERIPH_nEN | X1-35 |
| PG5 | GPIO/EXTI | I2C2_DRDY1_BARO2 | ICP-20100 #2 INT (optional) |
| PG6 | GPIO, pull-up | PG6 | X2-44 |
| PG7 | GPIO | SPI5_nCS1_FRAM | FRAM nCS |
| PG8 | GPIO | VDD_3V3_SENSORS4_EN | LDO4 EN |
| PG9 | SPI1_MISO | SPI1_MISO_SENSOR1 | ICM-20649 SDO |
| PG10 | GPIO | VDD_5V_HIPOWER_nEN | X1-81 |
| PG11 | SDMMC2_D2 | SD_D2 | microSD |
| PG12 | ETH_TXD1 | ETH_TXD1 | X2-23 |
| PG13 | ETH_TXD0 | ETH_TXD0 | X2-19 |
| PG14 | SPI6_MOSI | SPI6_MOSI_EXTERNAL1 | X2-33 |
| PG15 | GPIO | ETH_POWER_EN | X2-6 |
| PH0/PH1 | OSC | 16 MHz crystal | Y1 |
| PH2 | GPIO | VDD_3V3_SPEKTRUM_POWER_EN | X1-33 |
| PH3 | ADC3_INP14 | HW_VER_SENSE | X1-27 (base ID ladder) |
| PH4 | ADC3_INP15 | HW_REV_SENSE | module ID ladder |
| PH5 | GPIO | SPI2_nCS1_IMU2 | J3-33 |
| PH6 | TIM12_CH1 | FMU_CH7 | X1-3 |
| PH7 | SPI5_MISO | SPI5_MISO_FRAM | FRAM SO |
| PH8 | I2C3_SDA | I2C3_SDA_BASE | X1-8 |
| PH9 | TIM12_CH2 | FMU_CH8 | X1-1 |
| PH10 | TIM5_CH1 | FMU_CH4 | X1-11 |
| PH11 | TIM5_CH2 | FMU_CH3 | X1-13 (+ X2-50) |
| PH12 | TIM5_CH3 | FMU_CH2 | X1-15 |
| PH13 | UART4_TX | UART4_TX | X1-98 |
| PH14 | UART4_RX | UART4_RX | X1-96 |
| PI0 | TIM5_CH4 | FMU_CH1 | X1-17 |
| PI1 | SPI2_SCK | SPI2_SCK_SENSOR2 | J3-20 |
| PI2 | SPI2_MISO | SPI2_MISO_SENSOR2 | J3-22 |
| PI3 | SPI2_MOSI | SPI2_MOSI_SENSOR2 | J3-24 |
| PI4 | GPIO | SPI3_nCS1_BMI088_ACCEL | J3-2 |
| PI5 | TIM8_CH1 capture | FMU_PPM_INPUT | X1-39 |
| PI6 | GPIO | SPI3_DRDY1_BMI088_INT1 | n.c. (not on flex) |
| PI7 | GPIO/EXTI | SPI3_DRDY2_BMI088_INT3_GYRO | J3-3 |
| PI8 | GPIO | SPI3_nCS2_BMI088_GYRO | J3-4 |
| PI9 | GPIO | SPI1_nCS1_IMU3 | ICM-20649 nCS |
| PI10 | GPIO | SPI6_nCS1_EXTERNAL1 | X2-41 |
| PI11 | GPIO | VDD_3V3_SENSORS1_EN | LDO1 EN |
| NRST | reset | FMU_nRST | X1-87 |
| BOOT0 | boot | BOOT0 | BT0 pad, 10 k to GND |
| VBAT | backup | V_RTC_BAT | B1 + X1-29 |

Serial ports as PX4 names them: USART1 = GPS1, USART2 = TELEM3, USART3 = debug
console, UART4 = "UART4/I2C3" port, UART5 = TELEM2, USART6 = PX4IO link and RC input
(1.5 Mbit/s), UART7 = TELEM1, UART8 = GPS2.

### X1 — 100-pin Pixhawk Autopilot Bus (module part: Hirose DF40C-100DP-0.4V(51))

Odd pins on one row, even on the other. `GND` pins: 2 6 9 19 20 26 31 32 38 41 43 44 45 47 50 56 61 62 67 68 73 74 79 82 88 94 95 99 100.

| Pin | Net | Pin | Net |
| --- | --- | --- | --- |
| 1 | FMU_CH8 (PH9) | 4 | BUZZER_1 (PF9) |
| 3 | FMU_CH7 (PH6) | 8 | I2C3_SDA (PH8) |
| 5 | FMU_CH6 (PD14) | 10 | I2C3_SCL (PA8) |
| 7 | FMU_CH5 (PD13) | 12 | I2C2_SDA (PF0) |
| 11 | FMU_CH4 (PH10) | 14 | I2C2_SCL (PF1) |
| 13 | FMU_CH3 (PH11) | 16 | I2C1_SDA (PB9) |
| 15 | FMU_CH2 (PH12) | 18 | I2C1_SCL (PB8) |
| 17 | FMU_CH1 (PI0) | 22 | UART7_RTS_TELEM1 (PF8) |
| 21 | FMU_SAFETY_SWITCH_IN (PF5) | 24 | UART7_CTS_TELEM1 (PE10) |
| 23 | FMU_nSAFETY_SWITCH_LED_OUT (PD10) | 28 | UART8_TX_GPS2 (PE1) |
| 25 | HW_VER_REV_DRIVE (PG0) | 30 | UART8_RX_GPS2 (PE0) |
| 27 | HW_VER_SENSE (PH3) | 34 | USART1_RX_GPS1 (PB7) |
| 29 | V_RTC_BAT (VBAT, B1) | 36 | USART1_TX_GPS1 (PB6) |
| 33 | VDD_3V3_SPEKTRUM_POWER_EN (PH2) | 40 | USART2_TX_TELEM3 (PD5) |
| 35 | VDD_5V_PERIPH_nEN (PG4) | 42 | USART2_RX_TELEM3 (PA3) |
| 37 | VDD_5V_PERIPH_nOC (PE15) | 46 | USART2_RTS_TELEM3 (PD4) |
| 39 | FMU_PPM_INPUT (PI5) | 48 | USART2_CTS_TELEM3 (PD3) |
| 49 51 53 55 | **VDD_5V_IN** (supply in) | 52 | UART5_TX_TELEM2 (PC12) |
| 57 | CAN2_TX (PB13) | 54 | UART5_RX_TELEM2 (PD2) |
| 59 | CAN2_RX (PB12) | 58 | UART5_RTS_TELEM2 (PC8) |
| 63 | CAN1_TX (PD1) | 60 | UART5_CTS_TELEM2 (PC9) |
| 65 | CAN1_RX (PD0) | 64 | UART7_TX_TELEM1 (PE8) |
| 69 | USART3_TX_DEBUG (PD8) | 66 | UART7_RX_TELEM1 (PF6) |
| 71 | USART3_RX_DEBUG (PD9) | 70 | USART6_RX_FROM_IO / RC (PC7) |
| 75 | FMU_SWDIO (PA13) | 72 | USART6_TX_TO_IO (PC6) |
| 77 | FMU_SWCLK (PA14) | 76 | USB_D_P (PA12) |
| 81 | VDD_5V_HIPOWER_nEN (PG10) | 78 | USB_D_N (PA11) |
| 83 | VDD_5V_HIPOWER_nOC (PF13) | 80 | VBUS_SENSE (PA9) |
| 85 | nARMED (PE6) | 84, 86 | **FMU_VDD_3V3** (3.3 V out) |
| 87 | FMU_nRST (NRST) | 90 | ADC1_6V6 (PC2) |
| 89 | nPOWER_IN_A (PG1) | 92 | ADC1_3V3 (PC3) |
| 91 | nPOWER_IN_B (PG2) | 96 | UART4_RX (PH14) |
| 93 | nPOWER_IN_C (PG3) | 98 | UART4_TX (PH13) |
| 97 | FMU_CAP1 (PE11) | | |

### X2 — 50-pin Pixhawk Autopilot Bus (module part: Hirose DF40C-50DP-0.4V(51))

`GND`: 1 5 8 9 13 14 17 21 24 25 29 34 37 46. Connected signals: 2 ETH_MDIO (PA2) · 3 ETH_REF_CLK (PA1) · 4 ETH_MDC (PC1) · 6 ETH_POWER_EN (PG15) · 7 ETH_CRS_DV (PA7) · 11 ETH_RXD0 (PC4) · 15 ETH_RXD1 (PC5) · 19 ETH_TXD0 (PG13) · 23 ETH_TXD1 (PG12) · 27 ETH_TX_EN (PB11) · 31 SPI6_MISO (PA6) · 33 SPI6_MOSI (PG14) · 35 SPI6_SCK/SWO (PB3) · 39 SPI6_nRESET (PF10) · 41 SPI6_nCS1 (PI10) · 43 SPI6_nCS2 (PA15) · 44 PG6 · 45 SPI6_DRDY2 (PD12) · 47 SPI6_DRDY1 (PD11) · 48 NFC_GPIO (PC0) · 49 SPIX_SYNC (PE9) · 50 PH11.
Defined by the standard but **not connected** on an FMUv6X module: 10 ETH_RX_ER, 12 ETH_PHY_nINT, 16/18/20/22 FMU_CH9-12, 26/28/30/32/36/38 SPARE, 40/42 CAN3.

### J3 — 34-pin IMU flex (module part: Hirose BM20B(0.8)-34DP-0.4V(53))

| Pin | Net | Pin | Net |
| --- | --- | --- | --- |
| 1 | GND | 2 | SPI3_nCS1_BMI088_ACCEL (PI4) |
| 3 | SPI3_DRDY2_BMI088_INT3_GYRO (PI7) | 4 | SPI3_nCS2_BMI088_GYRO (PI8) |
| 5 | I2C4_SDA (PF15) | 6 | VDD_3V3_SENSORS3 |
| 7 | I2C4_SCL (PF14) | 8 | GND |
| 9 | GND | 10 | SPI3_SCK (PC10) |
| 11 | GND | 12 | SPI3_MISO (PC11) |
| 13 | GND | 14 | SPI3_MOSI (PB2) |
| 15 | GND | 16 | VDD_3V3_SENSORS4 |
| 17 | GND | 18 | GND |
| 19 | GND | 20 | SPI2_SCK (PI1) |
| 21 | GND | 22 | SPI2_MISO (PI2) |
| 23 | GND | 24 | SPI2_MOSI (PI3) |
| 25 | GND | 26 | GND |
| 27 | GND | 28 | VDD_5V_IN |
| 29 | GND | 30 | HEATER (PB10) |
| 31 | SPI2_DRDY2_IMU2_INT2 (PA10) | 32 | VDD_3V3_SENSORS2 |
| 33 | SPI2_nCS1_IMU2 (PH5) | 34 | GND |

---

## 4. Bill of materials for a replica

Exact-match parts are marked ✔ (identified from photo + firmware). Others are
functional substitutes any designer would pick; the original is likely different but
electrically equivalent.

| Ref | Part | Package | Notes |
| --- | --- | --- | --- |
| U1 ✔ | STM32H743IIK6 (or STM32H753IIK6) | UFBGA176+25, 0.65 mm | needs 4-6 layer PCB with 0.3 mm vias to route |
| X1 ✔ | Hirose DF40C-100DP-0.4V(51) | 0.4 mm, 3 mm stack | base side: DF40HC(3.0)-100DS-0.4V(58) |
| X2 ✔ | Hirose DF40C-50DP-0.4V(51) | | base side: DF40HC(3.0)-50DS-0.4V(51) |
| J3 ✔ | Hirose BM20B(0.8)-34DP-0.4V(53) | 0.4 mm | to IMU board FPC |
| J4 ✔ | Molex 5031821852 microSD push-push | | any hinged/push microSD works |
| U_FRAM ✔ | Cypress/Infineon FM25V02A-G | SOIC-8 | 256 kbit, SPI up to 40 MHz |
| U_SE | NXP SE050C1HQ1/Z01SC | HX2QFN-20 | optional; PX4 boots without it |
| U_IMU3 ✔ | TDK InvenSense ICM-20649 | QFN-24 3×3 | SPI mode 3 |
| U_BARO2 ✔ | TDK InvenSense ICP-20100 | LGA-10 2×2.5 | put it in a routed slot island |
| U_REG | 3.3 V buck, 1 A (e.g. TI TPS62A01, TPS563201 for a first prototype) | QFN/SOT | + 2.2 µH inductor, 2×10 µF in, 22 µF out |
| U_LDO1-4 | 3.3 V LDO 300 mA with EN (e.g. TLV75533PDBV) | SOT-23-5 | 1 µF in/out each; EN from PI11/PF4/PE7/PG8 |
| Q_SD | load switch (e.g. TPS22918) or P-MOSFET + pull-up | SOT-23-6 | EN from PC13 |
| Y1 ✔ | 16.000 MHz crystal, CL 8-10 pF | 3225 | 2×10 pF |
| Y2 ✔ | 32.768 kHz crystal, CL 6-7 pF | 3215/2012 | 2×6.8 pF |
| B1 | rechargeable Li cell 3 V (Seiko MS621FE) or 0.1 F supercap | | charge via BAT54 + 1 kΩ from 3.3 V |
| D1-3 ✔ | red / green / blue LEDs | 0603 | 470 Ω-1 kΩ series |
| R-ID | 24.9 kΩ + 442 kΩ (module ID 1) | 0402 | 1 % |
| R-pullups | 1.5 kΩ ×8 (I2C1-4 SCL/SDA) | 0402 | to FMU_VDD_3V3 |
| R-div | 10 kΩ ×10 (5 rails, 1:2) | 0402 | |
| C | 100 nF per supply pin (≈ 20), 2×2.2 µF VCAP, 4.7 µF bulk ×3 | 0402/0603 | |
| ferrite | on VDDA/VREF+ | 0603 | |

---

## 5. Learning-project advice (how to actually replicate this)

The module is a serious 6-layer, 0.4 mm-pitch, BGA design. Copying it 1:1 is a
poor *first* board. A path that keeps the same electronics but grows with your skill:

1. **Stage 1 — same brain, big pins.** Put an STM32H743**VIT6** (LQFP-100) or ZIT6 (LQFP-144)
   on a 2-layer board with the FRAM, microSD, crystals, LEDs, USB and an SWD header.
   Keep the exact pin functions from the table above wherever the LQFP exposes them
   (most of ports A-E are there). Flash the PX4 `px4_fmu-v6x` firmware unchanged only if
   you keep the BGA pinout; otherwise create your own board directory in
   `boards/<you>/…` copied from `boards/px4/fmu-v6x` and edit `board.h` /
   `board_config.h` / `spi.cpp` / `timer_config.cpp` to your pins. That is exactly the
   procedure the tables in this document were derived from, in reverse.
2. **Stage 2 — one sensor domain.** Add one LDO with enable, one ICM-20649 (or the more
   available ICM-42688-P) on SPI1 with its DRDY line, one ICP-20100 or BMP390 on I²C.
   Learn decoupling, the 1:2 rail sense divider, and how PX4's `rc.board_sensors`
   starts drivers.
3. **Stage 3 — the bus.** Add the DF40 pair and a minimal base board (USB-C, 5 V in,
   one UART, buzzer, safety switch). Now your module is mechanically and electrically
   a Pixhawk Autopilot Bus module and works on any commercial PAB base board
   (Holybro, CUAV, ARK) — that is the real value of copying the standard.
4. **Stage 4 — go BGA.** Move to the IIK6 and 6 layers when you can afford assembly
   with X-ray. Reference designs to compare against: Holybro Pixhawk 6X and ARK V6X
   (both open-hardware FMUv6X modules with published schematics).

Things that are easy to get wrong:

* **BOOT0** must be pulled down (10 k) and reachable — you will need DFU at least once.
* **VCAP1/VCAP2** need low-ESR 2.2 µF right at the balls; the H7 will not start without them.
* **SD card power switching** is not optional for PX4: it power-cycles the card on error.
* **I²C pull-ups belong on the module** (DS-010), not on the base — otherwise a bare
  module without base has floating buses and PX4 probes hang.
* **Sensor DRDY lines must be true EXTI-capable pins** (the ones listed) or PX4 falls
  back to polling and IMU timing suffers.
* **Grounding:** the four mounting holes are ground; the DF40 GND pins carry the return
  currents for the 25 MHz SD and 50 MHz RMII lines. Do not thin out the GND pins.

---

## 6. Sources

* PX4-Autopilot `boards/px4/fmu-v6x/` — `nuttx-config/include/board.h` (alternate-function
  pin map), `src/board_config.h` (GPIO, ADC, HW-ID, power control), `src/spi.cpp`
  (chip selects / DRDY / rail enables per hardware version), `src/i2c.cpp`,
  `src/timer_config.cpp` (PWM outputs), `src/mtd.cpp` (FRAM / EEPROM), `init/rc.board_sensors`
  (sensor start per hardware version — `V6X001` branch), `platforms/common/pab_manifest.c`
  (base-board IDs), `platforms/nuttx/src/px4/stm/stm32_common/board_hw_info/board_hw_rev_ver.c`
  (ID ladder table).
* Pixhawk Special Interest Group, *DS-010 Pixhawk Autopilot Bus Standard* — connector part
  numbers, X1 / X2 pinouts, mechanical drawing, layout guidelines.
* Pixhawk Special Interest Group, *DS-012 Pixhawk Autopilot FMUv6X Standard* — sensor
  sets, IMU flex connector pinout, sensor locations.
* PX4 user guide, *CUAV Pixhawk V6X* (`docs/en/flight_controller/cuav_pixhawk_v6x.md`) and CUAV
  *Pixhawk V6X Controller Product Manual* (2023-11) — sensor list, serial port mapping, ratings.
