#!/usr/bin/env python3
"""
Generate the reverse-engineered schematic sheets (SVG) and netlist (CSV) of the
CUAV V6X FMUM (Pixhawk FMUv6X flight-management-unit module, silkscreen
"V6X_FMUM RC11").

Single source of truth: the PINS / X1 / X2 / J3 tables below.  Everything else
(SVG sheets, netlist.csv) is derived from them, so fix the tables, not the output.

Sources for the tables:
  * PX4 board definition of this module (boards/px4/fmu-v6x/...: board.h,
    board_config.h, spi.cpp, i2c.cpp, timer_config.cpp, mtd.cpp,
    init/rc.board_sensors  -> hardware type V6X001 = "CUAV Sensor Set Rev 1")
  * Pixhawk Autopilot Bus standard DS-010 (X1 / X2 pinout, connector parts)
  * Pixhawk Autopilot FMUv6X standard DS-012 (sensor sets, IMU flex pinout)
  * The two photos of the board (component placement, packages, silkscreen)

Run:  python3 gen_schematic.py
"""
import csv
import html
import os
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schematic")

# --------------------------------------------------------------------------
# MCU pin table.  (pin, peripheral function, net name, where the net goes)
# Destination vocabulary:  "X1-nn" / "X2-nn" (PAB connectors), "J3-nn" (IMU
# flex), "U..." (on-module part), "NC" (no connection on this module).
# --------------------------------------------------------------------------
PINS = [
    # ---- Port A
    ("PA0",  "ADC1_INP16",        "SCALED_VDD_3V3_SENSORS1", "R-divider on VDD_3V3_SENSORS1"),
    ("PA1",  "ETH_REF_CLK",       "ETH_REF_CLK",             "X2-3"),
    ("PA2",  "ETH_MDIO",          "ETH_MDIO",                "X2-2"),
    ("PA3",  "USART2_RX",         "USART2_RX_TELEM3",        "X1-42"),
    ("PA4",  "ADC12_INP18",       "SCALED_VDD_3V3_SENSORS2", "R-divider on VDD_3V3_SENSORS2"),
    ("PA5",  "SPI1_SCK",          "SPI1_SCK_SENSOR1",        "U_IMU3 ICM-20649 SCLK"),
    ("PA6",  "SPI6_MISO",         "SPI6_MISO_EXTERNAL1",     "X2-31"),
    ("PA7",  "ETH_CRS_DV",        "ETH_CRS_DV",              "X2-7"),
    ("PA8",  "I2C3_SCL",          "I2C3_SCL_BASE",           "X1-10"),
    ("PA9",  "OTG_FS_VBUS",       "VBUS_SENSE",              "X1-80"),
    ("PA10", "GPIO in (EXTI)",    "SPI2_DRDY2_IMU2_INT2",    "J3-31"),
    ("PA11", "OTG_FS_DM",         "USB_D_N",                 "X1-78"),
    ("PA12", "OTG_FS_DP",         "USB_D_P",                 "X1-76"),
    ("PA13", "SWDIO",             "FMU_SWDIO",               "X1-75"),
    ("PA14", "SWCLK",             "FMU_SWCLK",               "X1-77"),
    ("PA15", "GPIO out",          "SPI6_nCS2_EXTERNAL1",     "X2-43"),
    # ---- Port B
    ("PB0",  "ADC12_INP9",        "SCALED_VDD_3V3_SENSORS3", "R-divider on VDD_3V3_SENSORS3"),
    ("PB1",  "ADC12_INP5",        "SCALED_V5",               "R-divider on VDD_5V_IN"),
    ("PB2",  "SPI3_MOSI",         "SPI3_MOSI_SENSOR3",       "J3-14"),
    ("PB3",  "SPI6_SCK / SWO",    "SPI6_SCK_EXTERNAL1",      "X2-35"),
    ("PB4",  "SDMMC2_D3",         "SD_D3",                   "J4 microSD DAT3"),
    ("PB5",  "SPI1_MOSI",         "SPI1_MOSI_SENSOR1",       "U_IMU3 ICM-20649 SDI"),
    ("PB6",  "USART1_TX",         "USART1_TX_GPS1",          "X1-36"),
    ("PB7",  "USART1_RX",         "USART1_RX_GPS1",          "X1-34"),
    ("PB8",  "I2C1_SCL",          "I2C1_SCL_BASE",           "X1-18"),
    ("PB9",  "I2C1_SDA",          "I2C1_SDA_BASE",           "X1-16"),
    ("PB10", "GPIO out (TIM2_CH3)", "HEATER",                "J3-30"),
    ("PB11", "ETH_TX_EN",         "ETH_TX_EN",               "X2-27"),
    ("PB12", "FDCAN2_RX",         "CAN2_RX",                 "X1-59"),
    ("PB13", "FDCAN2_TX",         "CAN2_TX",                 "X1-57"),
    ("PB14", "SDMMC2_D0",         "SD_D0",                   "J4 microSD DAT0"),
    ("PB15", "SDMMC2_D1",         "SD_D1",                   "J4 microSD DAT1"),
    # ---- Port C
    ("PC0",  "GPIO in (EXTI)",    "NFC_GPIO",                "X2-48"),
    ("PC1",  "ETH_MDC",           "ETH_MDC",                 "X2-4"),
    ("PC2",  "ADC3_INP12 (PC2_C)", "ADC1_6V6",               "X1-90"),
    ("PC3",  "ADC3_INP13 (PC3_C)", "ADC1_3V3",               "X1-92"),
    ("PC4",  "ETH_RXD0",          "ETH_RXD0",                "X2-11"),
    ("PC5",  "ETH_RXD1",          "ETH_RXD1",                "X2-15"),
    ("PC6",  "USART6_TX",         "USART6_TX_TO_IO",         "X1-72"),
    ("PC7",  "USART6_RX",         "USART6_RX_FROM_IO_RC",    "X1-70"),
    ("PC8",  "UART5_RTS",         "UART5_RTS_TELEM2",        "X1-58"),
    ("PC9",  "UART5_CTS",         "UART5_CTS_TELEM2",        "X1-60"),
    ("PC10", "SPI3_SCK",          "SPI3_SCK_SENSOR3",        "J3-10"),
    ("PC11", "SPI3_MISO",         "SPI3_MISO_SENSOR3",       "J3-12"),
    ("PC12", "UART5_TX",          "UART5_TX_TELEM2",         "X1-52"),
    ("PC13", "GPIO out",          "VDD_3V3_SD_CARD_EN",      "Q_SD load switch EN"),
    ("PC14", "OSC32_IN",          "32KHZ_IN",                "Y2 32.768 kHz"),
    ("PC15", "OSC32_OUT",         "32KHZ_OUT",               "Y2 32.768 kHz"),
    # ---- Port D
    ("PD0",  "FDCAN1_RX",         "CAN1_RX",                 "X1-65"),
    ("PD1",  "FDCAN1_TX",         "CAN1_TX",                 "X1-63"),
    ("PD2",  "UART5_RX",          "UART5_RX_TELEM2",         "X1-54"),
    ("PD3",  "USART2_CTS",        "USART2_CTS_TELEM3",       "X1-48"),
    ("PD4",  "USART2_RTS",        "USART2_RTS_TELEM3",       "X1-46"),
    ("PD5",  "USART2_TX",         "USART2_TX_TELEM3",        "X1-40"),
    ("PD6",  "SDMMC2_CK",         "SD_CLK",                  "J4 microSD CLK"),
    ("PD7",  "SDMMC2_CMD",        "SD_CMD",                  "J4 microSD CMD"),
    ("PD8",  "USART3_TX",         "USART3_TX_DEBUG",         "X1-69"),
    ("PD9",  "USART3_RX",         "USART3_RX_DEBUG",         "X1-71"),
    ("PD10", "GPIO out",          "FMU_nSAFETY_SWITCH_LED_OUT", "X1-23"),
    ("PD11", "GPIO in",           "SPI6_DRDY1_EXTERNAL1",    "X2-47"),
    ("PD12", "GPIO in",           "SPI6_DRDY2_EXTERNAL1",    "X2-45"),
    ("PD13", "TIM4_CH2",          "FMU_CH5",                 "X1-7"),
    ("PD14", "TIM4_CH3",          "FMU_CH6",                 "X1-5"),
    ("PD15", "GPIO in (spare)",   "PD15_SPARE",              "NC"),
    # ---- Port E
    ("PE0",  "UART8_RX",          "UART8_RX_GPS2",           "X1-30"),
    ("PE1",  "UART8_TX",          "UART8_TX_GPS2",           "X1-28"),
    ("PE2",  "TRACECLK",          "TRACECLK",                "J1 TRACE-1"),
    ("PE3",  "GPIO od (TRACED0)", "nLED_RED",                "D1 red LED cathode (+ J1 TRACE-3)"),
    ("PE4",  "GPIO od (TRACED1)", "nLED_GREEN",              "D2 green LED cathode (+ J1 TRACE-5)"),
    ("PE5",  "GPIO od (TRACED2)", "nLED_BLUE",               "D3 blue LED cathode (+ J1 TRACE-7)"),
    ("PE6",  "GPIO (TRACED3)",    "nARMED",                  "X1-85 (+ J1 TRACE-8)"),
    ("PE7",  "GPIO out",          "VDD_3V3_SENSORS3_EN",     "U_LDO3 EN"),
    ("PE8",  "UART7_TX",          "UART7_TX_TELEM1",         "X1-64"),
    ("PE9",  "GPIO out",          "SPIX_SYNC",               "X2-49"),
    ("PE10", "UART7_CTS",         "UART7_CTS_TELEM1",        "X1-24"),
    ("PE11", "TIM1_CH2 (capture)", "FMU_CAP1",               "X1-97"),
    ("PE15", "GPIO in",           "VDD_5V_PERIPH_nOC",       "X1-37"),
    # ---- Port F
    ("PF0",  "I2C2_SDA",          "I2C2_SDA_BASE",           "X1-12 (+ U_BARO2 ICP-20100 SDA)"),
    ("PF1",  "I2C2_SCL",          "I2C2_SCL_BASE",           "X1-14 (+ U_BARO2 ICP-20100 SCL)"),
    ("PF2",  "GPIO in (EXTI)",    "SPI1_DRDY1_IMU3_INT1",    "U_IMU3 ICM-20649 INT1"),
    ("PF4",  "GPIO out",          "VDD_3V3_SENSORS2_EN",     "U_LDO2 EN"),
    ("PF5",  "GPIO in (pull-up)", "FMU_SAFETY_SWITCH_IN",    "X1-21"),
    ("PF6",  "UART7_RX",          "UART7_RX_TELEM1",         "X1-66"),
    ("PF7",  "SPI5_SCK",          "SPI5_SCK_FRAM",           "U_FRAM FM25V02A SCK"),
    ("PF8",  "UART7_RTS",         "UART7_RTS_TELEM1",        "X1-22"),
    ("PF9",  "TIM14_CH1",         "BUZZER_1",                "X1-4"),
    ("PF10", "GPIO out",          "SPI6_nRESET_EXTERNAL1",   "X2-39"),
    ("PF11", "SPI5_MOSI",         "SPI5_MOSI_FRAM",          "U_FRAM FM25V02A SI"),
    ("PF12", "ADC1_INP6",         "SCALED_VDD_3V3_SENSORS4", "R-divider on VDD_3V3_SENSORS4"),
    ("PF13", "GPIO in",           "VDD_5V_HIPOWER_nOC",      "X1-83"),
    ("PF14", "I2C4_SCL",          "I2C4_SCL_FMU",            "J3-7 (+ U_SE SE050 SCL)"),
    ("PF15", "I2C4_SDA",          "I2C4_SDA_FMU",            "J3-5 (+ U_SE SE050 SDA)"),
    # ---- Port G
    ("PG0",  "GPIO out",          "HW_VER_REV_DRIVE",        "X1-25 (+ top of FMUM ID ladder)"),
    ("PG1",  "GPIO in (pull-up)", "nPOWER_IN_A",             "X1-89"),
    ("PG2",  "GPIO in (pull-up)", "nPOWER_IN_B",             "X1-91"),
    ("PG3",  "GPIO in (pull-up)", "nPOWER_IN_C",             "X1-93"),
    ("PG4",  "GPIO out",          "VDD_5V_PERIPH_nEN",       "X1-35"),
    ("PG5",  "GPIO in (EXTI)",    "I2C2_DRDY1_BARO2",        "U_BARO2 ICP-20100 INT (optional)"),
    ("PG6",  "GPIO in (pull-up)", "PG6",                     "X2-44"),
    ("PG7",  "GPIO out",          "SPI5_nCS1_FRAM",          "U_FRAM FM25V02A nCS"),
    ("PG8",  "GPIO out",          "VDD_3V3_SENSORS4_EN",     "U_LDO4 EN"),
    ("PG9",  "SPI1_MISO",         "SPI1_MISO_SENSOR1",       "U_IMU3 ICM-20649 SDO"),
    ("PG10", "GPIO out",          "VDD_5V_HIPOWER_nEN",      "X1-81"),
    ("PG11", "SDMMC2_D2",         "SD_D2",                   "J4 microSD DAT2"),
    ("PG12", "ETH_TXD1",          "ETH_TXD1",                "X2-23"),
    ("PG13", "ETH_TXD0",          "ETH_TXD0",                "X2-19"),
    ("PG14", "SPI6_MOSI",         "SPI6_MOSI_EXTERNAL1",     "X2-33"),
    ("PG15", "GPIO out",          "ETH_POWER_EN",            "X2-6"),
    # ---- Port H
    ("PH0",  "OSC_IN",            "16MHZ_IN",                "Y1 16 MHz"),
    ("PH1",  "OSC_OUT",           "16MHZ_OUT",               "Y1 16 MHz"),
    ("PH2",  "GPIO out",          "VDD_3V3_SPEKTRUM_POWER_EN", "X1-33"),
    ("PH3",  "ADC3_INP14",        "HW_VER_SENSE",            "X1-27 (base-board ID ladder)"),
    ("PH4",  "ADC3_INP15",        "HW_REV_SENSE",            "FMUM ID ladder (R_up 24.9k / R_dn 442k = ID 1)"),
    ("PH5",  "GPIO out",          "SPI2_nCS1_IMU2",          "J3-33"),
    ("PH6",  "TIM12_CH1",         "FMU_CH7",                 "X1-3"),
    ("PH7",  "SPI5_MISO",         "SPI5_MISO_FRAM",          "U_FRAM FM25V02A SO"),
    ("PH8",  "I2C3_SDA",          "I2C3_SDA_BASE",           "X1-8"),
    ("PH9",  "TIM12_CH2",         "FMU_CH8",                 "X1-1"),
    ("PH10", "TIM5_CH1",          "FMU_CH4",                 "X1-11"),
    ("PH11", "TIM5_CH2",          "FMU_CH3",                 "X1-13 (+ X2-50 'PH11')"),
    ("PH12", "TIM5_CH3",          "FMU_CH2",                 "X1-15"),
    ("PH13", "UART4_TX",          "UART4_TX",                "X1-98"),
    ("PH14", "UART4_RX",          "UART4_RX",                "X1-96"),
    # ---- Port I
    ("PI0",  "TIM5_CH4",          "FMU_CH1",                 "X1-17"),
    ("PI1",  "SPI2_SCK",          "SPI2_SCK_SENSOR2",        "J3-20"),
    ("PI2",  "SPI2_MISO",         "SPI2_MISO_SENSOR2",       "J3-22"),
    ("PI3",  "SPI2_MOSI",         "SPI2_MOSI_SENSOR2",       "J3-24"),
    ("PI4",  "GPIO out",          "SPI3_nCS1_BMI088_ACCEL",  "J3-2"),
    ("PI5",  "TIM8_CH1 (capture)", "FMU_PPM_INPUT",          "X1-39"),
    ("PI6",  "GPIO in",           "SPI3_DRDY1_BMI088_INT1",  "NC (not wired on flex for sensor set 1)"),
    ("PI7",  "GPIO in (EXTI)",    "SPI3_DRDY2_BMI088_INT3_GYRO", "J3-3"),
    ("PI8",  "GPIO out",          "SPI3_nCS2_BMI088_GYRO",   "J3-4"),
    ("PI9",  "GPIO out",          "SPI1_nCS1_IMU3",          "U_IMU3 ICM-20649 nCS"),
    ("PI10", "GPIO out",          "SPI6_nCS1_EXTERNAL1",     "X2-41"),
    ("PI11", "GPIO out",          "VDD_3V3_SENSORS1_EN",     "U_LDO1 EN"),
    # ---- non-port pins
    ("NRST",  "reset",            "FMU_nRST",                "X1-87 (+ 100 nF to GND)"),
    ("BOOT0", "boot select",      "BOOT0",                   "test pad 'BT0', 10k pull-down"),
    ("VBAT",  "backup supply",    "V_RTC_BAT",               "B1 backup cell + X1-29"),
    ("PDR_ON", "power-down reset", "FMU_VDD_3V3",            "tie to VDD"),
    ("VDD/VDDA/VDDUSB/VDDLDO", "supply", "FMU_VDD_3V3",      "100 nF per pin + 4.7 uF bulk"),
    ("VCAP1/VCAP2", "core LDO caps", "VCAP",                 "2.2 uF each to GND"),
    ("VREF+",  "ADC reference",    "FMU_VDD_3V3",            "via ferrite/1 uF"),
]

PINS_BY_NAME = {p[0]: p for p in PINS}


def mcu_for(dest_key):
    """Return list of MCU pins whose destination mentions dest_key (e.g. 'X1-36')."""
    out = []
    for pin, fn, net, dest in PINS:
        toks = dest.replace("(", " ").replace(")", " ").replace("+", " ").split()
        if dest_key in toks:
            out.append(pin)
    return out


# --------------------------------------------------------------------------
# X1: 100-pin PAB connector, Hirose DF40C-100DP-0.4V(51) on the module.
# (pin -> net) from DS-010.  Nets present on this module get an MCU pin from
# the table above; power/GND get explicit rails.
# --------------------------------------------------------------------------
X1 = {
    1: "FMU_CH8", 2: "GND", 3: "FMU_CH7", 4: "BUZZER_1", 5: "FMU_CH6", 6: "GND",
    7: "FMU_CH5", 8: "I2C3_SDA_BASE", 9: "GND", 10: "I2C3_SCL_BASE",
    11: "FMU_CH4", 12: "I2C2_SDA_BASE", 13: "FMU_CH3", 14: "I2C2_SCL_BASE",
    15: "FMU_CH2", 16: "I2C1_SDA_BASE", 17: "FMU_CH1", 18: "I2C1_SCL_BASE",
    19: "GND", 20: "GND", 21: "FMU_SAFETY_SWITCH_IN", 22: "UART7_RTS_TELEM1",
    23: "FMU_nSAFETY_SWITCH_LED_OUT", 24: "UART7_CTS_TELEM1",
    25: "HW_VER_REV_DRIVE", 26: "GND", 27: "HW_VER_SENSE", 28: "UART8_TX_GPS2",
    29: "V_RTC_BAT", 30: "UART8_RX_GPS2", 31: "GND", 32: "GND",
    33: "VDD_3V3_SPEKTRUM_POWER_EN", 34: "USART1_RX_GPS1",
    35: "VDD_5V_PERIPH_nEN", 36: "USART1_TX_GPS1", 37: "VDD_5V_PERIPH_nOC",
    38: "GND", 39: "FMU_PPM_INPUT", 40: "USART2_TX_TELEM3", 41: "GND",
    42: "USART2_RX_TELEM3", 43: "GND", 44: "GND", 45: "GND",
    46: "USART2_RTS_TELEM3", 47: "GND", 48: "USART2_CTS_TELEM3",
    49: "VDD_5V_IN", 50: "GND", 51: "VDD_5V_IN", 52: "UART5_TX_TELEM2",
    53: "VDD_5V_IN", 54: "UART5_RX_TELEM2", 55: "VDD_5V_IN", 56: "GND",
    57: "CAN2_TX", 58: "UART5_RTS_TELEM2", 59: "CAN2_RX", 60: "UART5_CTS_TELEM2",
    61: "GND", 62: "GND", 63: "CAN1_TX", 64: "UART7_TX_TELEM1", 65: "CAN1_RX",
    66: "UART7_RX_TELEM1", 67: "GND", 68: "GND", 69: "USART3_TX_DEBUG",
    70: "USART6_RX_FROM_IO_RC", 71: "USART3_RX_DEBUG", 72: "USART6_TX_TO_IO",
    73: "GND", 74: "GND", 75: "FMU_SWDIO", 76: "USB_D_P", 77: "FMU_SWCLK",
    78: "USB_D_N", 79: "GND", 80: "VBUS_SENSE", 81: "VDD_5V_HIPOWER_nEN",
    82: "GND", 83: "VDD_5V_HIPOWER_nOC", 84: "FMU_VDD_3V3", 85: "nARMED",
    86: "FMU_VDD_3V3", 87: "FMU_nRST", 88: "GND", 89: "nPOWER_IN_A",
    90: "ADC1_6V6", 91: "nPOWER_IN_B", 92: "ADC1_3V3", 93: "nPOWER_IN_C",
    94: "GND", 95: "GND", 96: "UART4_RX", 97: "FMU_CAP1", 98: "UART4_TX",
    99: "GND", 100: "GND",
}

# X2: 50-pin PAB connector, Hirose DF40C-50DP-0.4V(51) on the module.
X2 = {
    1: "GND", 2: "ETH_MDIO", 3: "ETH_REF_CLK", 4: "ETH_MDC", 5: "GND",
    6: "ETH_POWER_EN", 7: "ETH_CRS_DV", 8: "GND", 9: "GND", 10: "ETH_RX_ER",
    11: "ETH_RXD0", 12: "ETH_PHY_nINT", 13: "GND", 14: "GND", 15: "ETH_RXD1",
    16: "FMU_CH9", 17: "GND", 18: "FMU_CH10", 19: "ETH_TXD0", 20: "FMU_CH11",
    21: "GND", 22: "FMU_CH12", 23: "ETH_TXD1", 24: "GND", 25: "GND",
    26: "SPARE09", 27: "ETH_TX_EN", 28: "SPARE10", 29: "GND", 30: "SPARE11",
    31: "SPI6_MISO_EXTERNAL1", 32: "SPARE12", 33: "SPI6_MOSI_EXTERNAL1",
    34: "GND", 35: "SPI6_SCK_EXTERNAL1", 36: "SPARE14", 37: "GND",
    38: "SPARE15", 39: "SPI6_nRESET_EXTERNAL1", 40: "CAN3_TX",
    41: "SPI6_nCS1_EXTERNAL1", 42: "CAN3_RX", 43: "SPI6_nCS2_EXTERNAL1",
    44: "PG6", 45: "SPI6_DRDY2_EXTERNAL1", 46: "GND", 47: "SPI6_DRDY1_EXTERNAL1",
    48: "NFC_GPIO", 49: "SPIX_SYNC", 50: "PH11",
}
# Nets the standard reserves but the STM32H7 module leaves unconnected.
X2_NC = {"ETH_RX_ER", "ETH_PHY_nINT", "FMU_CH9", "FMU_CH10", "FMU_CH11",
         "FMU_CH12", "SPARE09", "SPARE10", "SPARE11", "SPARE12", "SPARE14",
         "SPARE15", "CAN3_TX", "CAN3_RX"}

# J3: IMU flex connector, Hirose BM20B(0.8)-34DP-0.4V(53) (DS-012, page 17).
J3 = {
    1: "GND", 2: "SPI3_nCS1_BMI088_ACCEL", 3: "SPI3_DRDY2_BMI088_INT3_GYRO",
    4: "SPI3_nCS2_BMI088_GYRO", 5: "I2C4_SDA_FMU", 6: "VDD_3V3_SENSORS3",
    7: "I2C4_SCL_FMU", 8: "GND", 9: "GND", 10: "SPI3_SCK_SENSOR3", 11: "GND",
    12: "SPI3_MISO_SENSOR3", 13: "GND", 14: "SPI3_MOSI_SENSOR3", 15: "GND",
    16: "VDD_3V3_SENSORS4", 17: "GND", 18: "GND", 19: "GND",
    20: "SPI2_SCK_SENSOR2", 21: "GND", 22: "SPI2_MISO_SENSOR2", 23: "GND",
    24: "SPI2_MOSI_SENSOR2", 25: "GND", 26: "GND", 27: "GND", 28: "VDD_5V_IN",
    29: "GND", 30: "HEATER", 31: "SPI2_DRDY2_IMU2_INT2", 32: "VDD_3V3_SENSORS2",
    33: "SPI2_nCS1_IMU2", 34: "GND",
}

POWER_NETS = {"VDD_5V_IN", "FMU_VDD_3V3", "V_RTC_BAT", "VDD_3V3_SENSORS1",
              "VDD_3V3_SENSORS2", "VDD_3V3_SENSORS3", "VDD_3V3_SENSORS4",
              "VDD_3V3_SD", "VBUS_SENSE"}

NET_TO_MCU = {}
for pin, fn, net, dest in PINS:
    NET_TO_MCU.setdefault(net, []).append(pin)
NET_TO_MCU["PH11"] = ["PH11"]  # X2-50 carries the raw pin name in DS-010

# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------
FONT = "'IBM Plex Mono', 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace"
FONT_UI = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif"

C = dict(
    ink="#1d232b", sym="#2b3a4a", stub="#1d232b", box="#f7f5ef",
    wire="#0b6e4f", power="#b8442c", gnd="#6b7280", mcu="#3b5bdb",
    muted="#7a828c", grid="#e7e2d6", title="#1d232b", warn="#a16207",
    sheet="#fbfaf6", nc="#9aa0a6",
)


def esc(s):
    return html.escape(str(s), quote=True)


class SVG:
    def __init__(self, w, h, title, subtitle):
        self.w, self.h = w, h
        self.parts = []
        self.parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}" font-size="11">')
        self.parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="{C["sheet"]}" stroke="{C["sym"]}" stroke-width="2"/>')
        # title block (bottom right)
        tb_w, tb_h = 720, 62
        x0, y0 = w - tb_w - 14, h - tb_h - 14
        self.parts.append(f'<rect x="{x0}" y="{y0}" width="{tb_w}" height="{tb_h}" fill="{C["box"]}" stroke="{C["sym"]}" stroke-width="1.2"/>')
        self.parts.append(f'<text x="{x0+10}" y="{y0+22}" font-family="{FONT_UI}" font-size="15" font-weight="700" fill="{C["title"]}">{esc(title)}</text>')
        self.parts.append(f'<text x="{x0+10}" y="{y0+40}" font-size="10.5" fill="{C["ink"]}">{esc(subtitle)}</text>')
        self.parts.append(f'<text x="{x0+10}" y="{y0+54}" font-size="9.5" fill="{C["muted"]}">CUAV V6X FMUM (RC11, 07-2023) · reverse-engineered from PX4 fmu-v6x board files + Pixhawk DS-010/DS-012 · not vendor data</text>')

    def text(self, x, y, s, size=11, fill=None, anchor="start", weight="400", family=None, italic=False):
        fill = fill or C["ink"]
        fam = f' font-family="{family}"' if family else ""
        st = ' font-style="italic"' if italic else ""
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{fam}{st}>{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke=None, width=1.3, dash=None):
        stroke = stroke or C["wire"]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"{d}/>')

    def rect(self, x, y, w, h, fill=None, stroke=None, width=1.4, rx=0):
        fill = fill or C["box"]
        stroke = stroke or C["sym"]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" rx="{rx}"/>')

    def dot(self, x, y, r=2.2, fill=None):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill or C["wire"]}"/>')

    def gnd(self, x, y):
        """ground symbol hanging down from (x,y)"""
        self.line(x, y, x, y + 6, C["gnd"])
        self.line(x - 7, y + 6, x + 7, y + 6, C["gnd"])
        self.line(x - 4.5, y + 9.5, x + 4.5, y + 9.5, C["gnd"])
        self.line(x - 2, y + 13, x + 2, y + 13, C["gnd"])

    def pwr(self, x, y, name):
        """power bar symbol rising from (x,y)"""
        self.line(x, y, x, y - 8, C["power"])
        self.line(x - 6, y - 8, x + 6, y - 8, C["power"], 1.8)
        self.text(x, y - 12, name, 9.5, C["power"], "middle", "600")

    def note(self, x, y, lines, w=None, size=10):
        h = 14 * len(lines) + 12
        w = w or max(len(l) for l in lines) * size * 0.62 + 16
        self.rect(x, y, w, h, "#fffbea", C["warn"], 1)
        for i, l in enumerate(lines):
            self.text(x + 8, y + 16 + 14 * i, l, size, "#5a4300")
        return h

    def save(self, name):
        self.parts.append("</svg>")
        path = os.path.join(OUT, name)
        with open(path, "w") as f:
            f.write("\n".join(self.parts))
        return path


def net_color(net):
    if net == "GND":
        return C["gnd"]
    if net in POWER_NETS or net.startswith("VDD_") and "_EN" not in net and "_nEN" not in net and "_nOC" not in net:
        return C["power"]
    return C["wire"]


# --------------------------------------------------------------------------
# Generic component-symbol drawer: box with pins on left/right.
# pins: list of (side, pin_label_inside, net_label_outside, mcu_pin_or_None)
# --------------------------------------------------------------------------
def draw_part(svg, x, y, w, refdes, part, desc, left, right, pitch=16, pad=26):
    n = max(len(left), len(right))
    h = pad + n * pitch + 10
    svg.rect(x, y, w, h)
    svg.text(x + w / 2, y + 17, refdes, 11.5, C["sym"], "middle", "700")
    stub = 22
    for i, (pname, net, mcu) in enumerate(left):
        py = y + pad + 10 + i * pitch
        col = net_color(net)
        svg.text(x + 5, py + 3.5, pname, 9.5, C["ink"])
        if not net:
            continue
        svg.line(x - stub, py, x, py, col)
        if net == "GND":
            svg.gnd(x - stub, py)
        else:
            lbl = net + (f"  [{mcu}]" if mcu else "")
            svg.text(x - stub - 4, py + 3.5, lbl, 9.5, col, "end", "600")
    for i, (pname, net, mcu) in enumerate(right):
        py = y + pad + 10 + i * pitch
        col = net_color(net)
        svg.text(x + w - 5, py + 3.5, pname, 9.5, C["ink"], "end")
        if not net:
            continue
        svg.line(x + w, py, x + w + stub, py, col)
        if net == "GND":
            svg.gnd(x + w + stub, py)
        else:
            lbl = net + (f"  [{mcu}]" if mcu else "")
            svg.text(x + w + stub + 4, py + 3.5, lbl, 9.5, col, "start", "600")
    svg.text(x + w / 2, y + h + 13, part, 9, C["ink"], "middle")
    if desc:
        svg.text(x + w / 2, y + h + 26, desc, 9, C["muted"], "middle", italic=True)
    return h


def m(net):
    """first MCU pin for a net, or None"""
    p = NET_TO_MCU.get(net)
    return p[0] if p else None


# --------------------------------------------------------------------------
# Sheet 1 : MCU
# --------------------------------------------------------------------------
def sheet_mcu():
    ports_left = ["PA", "PB", "PC", "PD"]
    ports_right = ["PE", "PF", "PG", "PH", "PI"]
    pitch, gap = 15.5, 14

    def rows(ports):
        r = []
        for prt in ports:
            pins = [p for p in PINS if p[0].startswith(prt) and p[0][2:].isdigit()]
            r.append(pins)
        return r

    L, R = rows(ports_left), rows(ports_right)
    nl = sum(len(g) for g in L) * pitch + gap * (len(L) - 1)
    nr = sum(len(g) for g in R) * pitch + gap * (len(R) - 1)
    box_h = max(nl, nr) + 60
    W, H = 1500, int(box_h + 260)
    svg = SVG(W, H, "Sheet 1 · U1 microcontroller", "STM32H743IIK6 (marking) / STM32H753II per PX4 defconfig · UFBGA176+25 · 480 MHz Cortex-M7")
    bx, by, bw = 520, 40, 460
    svg.rect(bx, by, bw, box_h)
    svg.text(bx + bw / 2, by + 20, "U1  STM32H7x3IIK6", 14, C["sym"], "middle", "700", FONT_UI)
    svg.text(bx + bw / 2, by + 36, "pin function shown inside · net name and destination outside", 9.5, C["muted"], "middle")
    stub = 26

    def side(groups, xside, left=True):
        yy = by + 56
        for g in groups:
            for pin, fn, net, dest in g:
                col = net_color(net)
                if dest == "NC" or dest.startswith("NC"):
                    col = C["nc"]
                if left:
                    svg.line(bx - stub, yy, bx, yy, col)
                    svg.text(bx + 6, yy + 3.5, f"{pin}  {fn}", 9.5, C["ink"])
                    svg.text(bx - stub - 5, yy + 3.5, net, 9.5, col, "end", "600")
                    svg.text(bx - stub - 5, yy + 3.5, "", 9)
                    svg.text(20, yy + 3.5, dest, 8.5, C["muted"])
                else:
                    svg.line(bx + bw, yy, bx + bw + stub, yy, col)
                    svg.text(bx + bw - 6, yy + 3.5, f"{fn}  {pin}", 9.5, C["ink"], "end")
                    svg.text(bx + bw + stub + 5, yy + 3.5, net, 9.5, col, "start", "600")
                    svg.text(W - 20, yy + 3.5, dest, 8.5, C["muted"], "end")
                yy += pitch
            yy += gap

    side(L, bx, True)
    side(R, bx + bw, False)

    # Non-port pins block under the MCU
    y2 = by + box_h + 24
    svg.text(bx, y2, "Supply, reset and boot pins", 11, C["sym"], "start", "700", FONT_UI)
    extra = [p for p in PINS if not (p[0].startswith("P") and p[0][2:].isdigit())]
    for i, (pin, fn, net, dest) in enumerate(extra):
        yy = y2 + 18 + i * 15
        svg.text(bx, yy, pin, 9.5, C["ink"], "start", "600")
        svg.text(bx + 190, yy, net, 9.5, net_color(net), "start", "600")
        svg.text(bx + 380, yy, dest, 9, C["muted"])

    svg.note(20, y2 - 6, [
        "Pin assignment is the as-built PX4 fmu-v6x map (boards/px4/fmu-v6x).",
        "Where the DS-012 draft pinout sheet disagrees (nARMED, HW_*_SENSE,",
        "NFC_GPIO, safety switch, FMU_CHx timers, SDMMC2 data pins) the PX4",
        "board files were taken as truth because this exact module runs them.",
        "Pins not listed (PE12-14, PF3, PH15, ...) are unconnected on the module.",
    ], 470)
    return svg.save("01_mcu_u1.svg")


# --------------------------------------------------------------------------
# Sheet 2 : core peripherals (memory, storage, clocks, debug, LEDs, RTC, IDs)
# --------------------------------------------------------------------------
def sheet_core():
    W, H = 1500, 1120
    svg = SVG(W, H, "Sheet 2 · Core peripherals on the module", "FRAM, secure element, microSD, crystals, LEDs, RTC backup cell, USB, HW-ID ladder, trace pads")
    # FRAM
    draw_part(svg, 250, 40, 150, "U_FRAM", "FM25V02A-DG  SOIC-8 (256 kbit FRAM)", "PX4 parameters. SPI5 @ up to 40 MHz",
              [("nCS", "SPI5_nCS1_FRAM", "PG7"), ("SO", "SPI5_MISO_FRAM", "PH7"), ("nWP", "FMU_VDD_3V3", None), ("VSS", "GND", None)],
              [("VDD", "FMU_VDD_3V3", None), ("nHOLD", "FMU_VDD_3V3", None), ("SCK", "SPI5_SCK_FRAM", "PF7"), ("SI", "SPI5_MOSI_FRAM", "PF11")])
    # SE050
    draw_part(svg, 250, 225, 150, "U_SE", "NXP SE050C1  HX2QFN-20 3x3 (likely, marked 'S50')", "secure element, I2C4 addr 0x48 (PX4_I2C_OBDEV_SE050)",
              [("SDA", "I2C4_SDA_FMU", "PF15"), ("SCL", "I2C4_SCL_FMU", "PF14"), ("ENA", "FMU_VDD_3V3", None), ("GND", "GND", None)],
              [("VDD", "FMU_VDD_3V3", None), ("VIN", "FMU_VDD_3V3", None), ("IO1", "", None), ("IO2", "", None)])
    # microSD
    draw_part(svg, 250, 410, 150, "J4", "Molex 5031821852 push-push microSD (marked 'molex 2011EC')", "SDMMC2 4-bit, 25 MHz; power gated by PC13",
              [("DAT2", "SD_D2", "PG11"), ("CD/DAT3", "SD_D3", "PB4"), ("CMD", "SD_CMD", "PD7"), ("VDD", "VDD_3V3_SD", None), ("CLK", "SD_CLK", "PD6"), ("VSS", "GND", None), ("DAT0", "SD_D0", "PB14"), ("DAT1", "SD_D1", "PB15")],
              [("SHIELD", "GND", None)])
    # SD load switch
    draw_part(svg, 700, 425, 130, "Q_SD", "3.3 V load switch (e.g. TPS22918 / SiP32431)", "10k pull-ups on CMD/DAT0-3 to VDD_3V3_SD",
              [("VIN", "FMU_VDD_3V3", None), ("EN", "VDD_3V3_SD_CARD_EN", "PC13"), ("GND", "GND", None)],
              [("VOUT", "VDD_3V3_SD", None)])
    # Crystals
    draw_part(svg, 700, 40, 130, "Y1", "16.000 MHz, 3225 SMD, CL 8-10 pF", "HSE -> PLL1: 480 MHz SYSCLK. 2x 10 pF load caps",
              [("1", "16MHZ_IN", "PH0"), ("2", "GND", None)], [("3", "16MHZ_OUT", "PH1"), ("4", "GND", None)])
    draw_part(svg, 700, 160, 130, "Y2", "32.768 kHz, 2012/3215 SMD, CL 6-7 pF", "LSE for RTC. 2x 6.8 pF load caps",
              [("1", "32KHZ_IN", "PC14")], [("2", "32KHZ_OUT", "PC15")])
    # RTC battery
    draw_part(svg, 700, 255, 130, "B1", "rechargeable Li coin/cyl. cell (marked 'L03'), e.g. Seiko MS621 / Panasonic ML", "keeps RTC + backup SRAM; charged from FMU_VDD_3V3 through D + R",
              [("+", "V_RTC_BAT", None)], [("-", "GND", None)])
    svg.text(700, 372, "V_RTC_BAT -> U1 VBAT and X1-29; charge path: FMU_VDD_3V3 -> BAT54 -> 1k -> V_RTC_BAT", 9, C["muted"])
    # LEDs
    y = 40
    for i, (d, colr, net, pin) in enumerate([("D1", "red", "nLED_RED", "PE3"), ("D2", "green", "nLED_GREEN", "PE4"), ("D3", "blue", "nLED_BLUE", "PE5")]):
        yy = y + i * 52
        svg.rect(1120, yy, 26, 26, "#fff", C["sym"])
        svg.text(1133, yy + 17, "▶|", 11, C["sym"], "middle")
        svg.pwr(1080, yy + 13, "FMU_VDD_3V3")
        svg.line(1080, yy + 13, 1120, yy + 13, C["power"])
        svg.line(1146, yy + 13, 1200, yy + 13)
        svg.rect(1200, yy + 8, 40, 10, "#fff", C["sym"], 1)
        svg.text(1220, yy + 34, "R 470-1k", 8.5, C["muted"], "middle")
        svg.line(1240, yy + 13, 1290, yy + 13)
        svg.text(1295, yy + 17, f"{net}  [{pin}]", 9.5, C["wire"], "start", "600")
        svg.text(1133, yy + 40, f"{d} {colr} 0603", 8.5, C["muted"], "middle")
    svg.text(1080, 205, "open-drain outputs, LED on = pin low. PE3-PE5 double as TRACED0-2.", 9, C["muted"])

    # USB
    draw_part(svg, 1120, 255, 170, "USB", "OTG_FS via X1 (no connector on module)", "27 ohm series + ESD diodes belong on the base board",
              [("D+", "USB_D_P", "PA12"), ("D-", "USB_D_N", "PA11"), ("VBUS", "VBUS_SENSE", "PA9")], [("→ X1-76", "", None), ("→ X1-78", "", None), ("→ X1-80", "", None)])

    # HW ID ladder
    x0, y0 = 250, 640
    svg.text(x0, y0, "Hardware-ID resistor ladders (read by ADC3 at boot)", 12, C["sym"], "start", "700", FONT_UI)
    svg.pwr(x0 + 60, y0 + 45, "HW_VER_REV_DRIVE [PG0]")
    svg.line(x0 + 60, y0 + 45, x0 + 60, y0 + 70, C["wire"])
    svg.rect(x0 + 50, y0 + 70, 20, 40, "#fff", C["sym"], 1)
    svg.text(x0 + 80, y0 + 94, "R_up 24.9k", 9.5)
    svg.line(x0 + 60, y0 + 110, x0 + 60, y0 + 150, C["wire"])
    svg.dot(x0 + 60, y0 + 130)
    svg.line(x0 + 60, y0 + 130, x0 + 150, y0 + 130, C["wire"])
    svg.text(x0 + 155, y0 + 134, "HW_REV_SENSE  [PH4 / ADC3_INP15]  -> FMUM ID", 9.5, C["wire"], "start", "600")
    svg.rect(x0 + 50, y0 + 150, 20, 40, "#fff", C["sym"], 1)
    svg.text(x0 + 80, y0 + 174, "R_dn 442k", 9.5)
    svg.line(x0 + 60, y0 + 190, x0 + 60, y0 + 200, C["wire"])
    svg.gnd(x0 + 60, y0 + 200)
    svg.note(x0 + 160, y0 + 150, [
        "ID = 1 -> PX4 'V6X001' = CUAV sensor set rev 1.",
        "Ladder table (R_up/R_dn): 1: 24.9k/442k  2: 32.4k/174k  3: 38.3k/115k  4: 46.4k/84.5k",
        "5: 51.1k/61.9k  6: 61.9k/51.1k  7: 84.5k/46.4k  8: 115k/38.3k  9: 174k/32.4k  10: 442k/24.9k",
        "The BASE board carries the same kind of ladder on HW_VER_SENSE (X1-27, PH3); CUAV base = ID 2.",
        "PG0 is driven high only while sampling, then tri-stated, so the ladders draw nothing at rest.",
    ], 620, 9.5)

    # BOOT0 / NRST / trace
    x0, y0 = 250, 900
    svg.text(x0, y0, "Reset, boot and trace", 12, C["sym"], "start", "700", FONT_UI)
    svg.text(x0, y0 + 20, "BOOT0  -> test pad 'BT0' (top side) with 10k to GND. Short BT0 to 3.3 V at power-up to enter the ST DFU bootloader.", 9.5)
    svg.text(x0, y0 + 36, "NRST   -> X1-87 FMU_nRST, 100 nF to GND. Reset button lives on the base board (ADIO port).", 9.5)
    svg.text(x0, y0 + 52, "J1 TRACE (unpopulated 8+2 pad footprint, bottom-left, top side): 1 TRACECLK PE2 · 3 TRACED0 PE3 · 5 TRACED1 PE4 · 7 TRACED2 PE5 · 8 TRACED3 PE6 · GND (PX4 board_config.h, TRACE_PINS)", 9.5)
    svg.text(x0, y0 + 68, "SWD (PA13 SWDIO, PA14 SWCLK, PB3 SWO shared with SPI6_SCK) leaves on X1-75/77 and X2-35 to the base 'FMU debug' JST-SM10B port.", 9.5)
    svg.text(x0, y0 + 84, "Test pads seen on the photos: TP1 (bottom), TP2, TP3, TP4, TP7, BT0 (top). Only BT0 is identified with certainty.", 9.5, C["muted"])
    return svg.save("02_core_peripherals.svg")


# --------------------------------------------------------------------------
# Sheet 3 : power tree + on-module sensors + heater
# --------------------------------------------------------------------------
def sheet_power_sensors():
    W, H = 1600, 1080
    svg = SVG(W, H, "Sheet 3 · Power domains and on-module sensors", "VDD_5V_IN -> FMU 3.3 V rail; four switched sensor LDOs with ADC supervision; IMU3, BARO2, heater driver")
    # main regulator
    draw_part(svg, 330, 60, 170, "U_REG", "3.3 V step-down, ~1 A (QFN + 2.2 uH inductor, bottom-centre of MCU side)", "always on. Feeds U1, FRAM, SE050, LEDs, SD switch and X1-84/86",
              [("VIN", "VDD_5V_IN", None), ("EN", "VDD_5V_IN", None), ("GND", "GND", None)],
              [("VOUT", "FMU_VDD_3V3", None)])
    svg.text(330, 200, "VDD_5V_IN arrives on X1-49/51/53/55 (4 pins, 1.5 A budget) and also leaves to the IMU board on J3-28 for the heater.", 9.5, C["muted"])
    svg.text(330, 215, "Input: 2x 10 uF + 100 nF. Output: 22 uF + 100 nF. FMU_VDD_3V3 is exported so the base can power its EEPROM / LEDs / pull-ups.", 9.5, C["muted"])

    # sensor LDOs
    ldos = [
        ("U_LDO1", "VDD_3V3_SENSORS1", "VDD_3V3_SENSORS1_EN", "PI11", "SCALED_VDD_3V3_SENSORS1", "PA0", "domain 1: IMU3 ICM-20649 (on module, SPI1)"),
        ("U_LDO2", "VDD_3V3_SENSORS2", "VDD_3V3_SENSORS2_EN", "PF4", "SCALED_VDD_3V3_SENSORS2", "PA4", "domain 2: IMU2 ICM-42688-P (IMU board, SPI2) -> J3-32"),
        ("U_LDO3", "VDD_3V3_SENSORS3", "VDD_3V3_SENSORS3_EN", "PE7", "SCALED_VDD_3V3_SENSORS3", "PB0", "domain 3: IMU1 BMI088 (IMU board, SPI3) -> J3-6"),
        ("U_LDO4", "VDD_3V3_SENSORS4", "VDD_3V3_SENSORS4_EN", "PG8", "SCALED_VDD_3V3_SENSORS4", "PF12", "domain 4: I2C4 devices: RM3100, ICP-20100 #1, EEPROM (IMU board) -> J3-16"),
    ]
    for i, (ref, rail, en, enpin, sense, spin, desc) in enumerate(ldos):
        x, y = 330 + (i % 2) * 660, 270 + (i // 2) * 210
        draw_part(svg, x, y, 150, ref, "3.3 V LDO 300 mA w/ EN (SOT-23-5, e.g. TLV75533 / RT9080)", desc,
                  [("VIN", "VDD_5V_IN", None), ("EN", en, enpin), ("GND", "GND", None)],
                  [("VOUT", rail, None)])
        # divider
        dx = x + 300
        svg.line(dx, y + 36, dx + 60, y + 36, C["power"])
        svg.text(dx + 62, y + 40, rail, 9.5, C["power"], "start", "600")
        svg.line(dx + 30, y + 36, dx + 30, y + 50, C["power"])
        svg.rect(dx + 22, y + 50, 16, 30, "#fff", C["sym"], 1)
        svg.text(dx + 44, y + 68, "10k", 9)
        svg.line(dx + 30, y + 80, dx + 30, y + 100, C["wire"])
        svg.dot(dx + 30, y + 90)
        svg.line(dx + 30, y + 90, dx + 80, y + 90, C["wire"])
        svg.text(dx + 84, y + 94, f"{sense}  [{spin}]  (ADC1)", 9.5, C["wire"], "start", "600")
        svg.rect(dx + 22, y + 100, 16, 30, "#fff", C["sym"], 1)
        svg.text(dx + 44, y + 118, "10k", 9)
        svg.line(dx + 30, y + 130, dx + 30, y + 140, C["wire"])
        svg.gnd(dx + 30, y + 140)
        svg.text(dx - 40, y + 172, "10k/10k divider -> 1.65 V nominal at ADC1", 8.5, C["muted"])
    # V5 sense
    x, y = 330, 700
    svg.text(x, y, "SCALED_V5 [PB1 / ADC1_INP5]: VDD_5V_IN through 10k / 10k divider (2.5 V nominal). PX4 reports it as the 5 V rail voltage.", 9.5, C["muted"])

    # IMU3 on module
    draw_part(svg, 330, 740, 170, "U_IMU3", "TDK ICM-20649  QFN-24 3x3 (top-centre, MCU side)", "6-axis IMU #3, SPI1 mode 3, up to 7 MHz; PX4 rotation ROTATION_ROLL_180_YAW_270 (-R 14)",
              [("nCS", "SPI1_nCS1_IMU3", "PI9"), ("SCLK", "SPI1_SCK_SENSOR1", "PA5"), ("SDI", "SPI1_MOSI_SENSOR1", "PB5"), ("SDO/AD0", "SPI1_MISO_SENSOR1", "PG9"), ("INT1", "SPI1_DRDY1_IMU3_INT1", "PF2"), ("GND", "GND", None)],
              [("VDD", "VDD_3V3_SENSORS1", None), ("VDDIO", "VDD_3V3_SENSORS1", None), ("REGOUT", "", None), ("FSYNC", "GND", None)])
    svg.text(330, 920, "REGOUT: 100 nF to GND. VDD/VDDIO: 100 nF each. Decoupling right at the pins.", 9, C["muted"])

    # BARO2 on module
    draw_part(svg, 1000, 740, 170, "U_BARO2", "TDK ICP-20100  LGA-10 2.0x2.5 metal lid (in the slotted island)", "barometer #2, I2C2 addr 0x63; PX4 driver icp201xx -X (external bus 2)",
              [("SDA", "I2C2_SDA_BASE", "PF0"), ("SCL", "I2C2_SCL_BASE", "PF1"), ("INT", "I2C2_DRDY1_BARO2", "PG5"), ("GND", "GND", None)],
              [("VDD", "VDD_3V3_SENSORS2", None), ("VDDIO", "VDD_3V3_SENSORS2", None), ("AD0", "GND", None), ("I2C/SPI sel", "FMU_VDD_3V3", None)])
    svg.text(1000, 905, "The routed slot around it is mechanical stress relief: PCB flex would otherwise show up as pressure error.", 9, C["muted"])
    svg.text(1000, 919, "I2C2 is shared with the base (GPS2 / power monitor 2 connectors) and has 1.5k pull-ups to FMU_VDD_3V3 on the module.", 9, C["muted"])

    # heater
    svg.note(1060, 60, [
        "HEATER [PB10, TIM2_CH3 capable] runs straight to J3-30.",
        "The switching MOSFET and the heating resistors sit on the IMU board,",
        "fed from raw VDD_5V_IN on J3-28. PX4 drives it as a slow PWM/on-off",
        "output (GPIO_HEATER_OUTPUT) to hold the IMUs at a set temperature.",
    ], 400, 9.5)

    # pullups
    svg.note(1000, 940, [
        "I2C pull-ups (1.5k to FMU_VDD_3V3, required by DS-010) live on the FMUM for",
        "I2C1 (PB8/PB9), I2C2 (PF0/PF1), I2C3 (PA8/PH8) and I2C4 (PF14/PF15).",
    ], 410, 9.5)
    return svg.save("03_power_and_sensors.svg")


# --------------------------------------------------------------------------
# Connector sheets
# --------------------------------------------------------------------------
def connector_sheet(fname, title, subtitle, refdes, part, table, nc=set(), pitch=16.5, notes=None):
    n = len(table)
    rows = (n + 1) // 2
    H = rows * pitch + 260
    W = 1400
    svg = SVG(W, int(H), title, subtitle)
    cx, cw = 620, 160
    top = 70
    svg.rect(cx, top - 30, cw, rows * pitch + 50)
    svg.text(cx + cw / 2, top - 14, refdes, 12, C["sym"], "middle", "700")
    svg.text(cx + cw / 2, top - 2, part, 8.5, C["muted"], "middle")
    stub = 28
    for r in range(rows):
        y = top + 16 + r * pitch
        for side in (0, 1):
            pin = 2 * r + 1 + side
            if pin not in table:
                continue
            net = table[pin]
            mcu = [] if net in POWER_NETS else NET_TO_MCU.get(net, [])
            if net == "V_RTC_BAT":
                mcu = ["VBAT"]
            is_nc = net in nc
            col = C["nc"] if is_nc else net_color(net)
            if side == 0:
                svg.line(cx - stub, y, cx, y, col)
                svg.text(cx + 6, y + 3.5, str(pin), 9.5, C["ink"])
                if net == "GND":
                    svg.gnd(cx - stub, y)
                else:
                    lbl = net + ("  (n.c. on FMUv6X)" if is_nc else "")
                    svg.text(cx - stub - 5, y + 3.5, lbl, 9.5, col, "end", "600")
                    if mcu:
                        svg.text(40, y + 3.5, ", ".join(mcu), 9, C["mcu"], "start", "700")
            else:
                svg.line(cx + cw, y, cx + cw + stub, y, col)
                svg.text(cx + cw - 6, y + 3.5, str(pin), 9.5, C["ink"], "end")
                if net == "GND":
                    svg.gnd(cx + cw + stub, y)
                else:
                    lbl = net + ("  (n.c. on FMUv6X)" if is_nc else "")
                    svg.text(cx + cw + stub + 5, y + 3.5, lbl, 9.5, col, "start", "600")
                    if mcu:
                        svg.text(W - 40, y + 3.5, ", ".join(mcu), 9, C["mcu"], "end", "700")
    svg.text(40, top - 14, "U1 pin", 9, C["mcu"], "start", "700")
    svg.text(W - 40, top - 14, "U1 pin", 9, C["mcu"], "end", "700")
    if notes:
        svg.note(40, top + rows * pitch + 40, notes, 560, 9.5)
    return svg.save(fname)


def sheet_x1():
    return connector_sheet(
        "04_x1_pab_100pin.svg", "Sheet 4 · X1 Pixhawk Autopilot Bus, 100-pin",
        "Hirose DF40C-100DP-0.4V(51) (module side) mates DF40HC(3.0)-100DS-0.4V(58) on the base · 3 mm stack",
        "X1", "DF40C-100DP-0.4V(51)  ·  odd pins left, even pins right  ·  pin 1 = bottom-left of the module (bottom view)", X1,
        notes=[
            "VDD_5V_IN (49/51/53/55) is the only supply into the module. FMU_VDD_3V3 (84/86) is an OUTPUT to the base.",
            "V_RTC_BAT (29) connects the module's backup cell B1 to the base so either side can host the cell.",
            "HW_VER_SENSE (27) reads the base-board ID ladder; HW_VER_REV_DRIVE (25) powers both ladders during boot.",
            "I2C1/2/3 pull-ups (1.5k) are on this module. USB and CAN transceivers are NOT: only logic-level lines cross X1.",
            "All GND pins must be connected; the DF40 relies on them for return paths under the 100 MHz-class signals (SD, RMII).",
        ])


def sheet_x2():
    return connector_sheet(
        "05_x2_pab_50pin.svg", "Sheet 5 · X2 Pixhawk Autopilot Bus, 50-pin",
        "Hirose DF40C-50DP-0.4V(51) (module side) · RMII Ethernet, external SPI6, spares",
        "X2", "DF40C-50DP-0.4V(51)  ·  odd pins left, even pins right", X2, X2_NC,
        notes=[
            "RMII goes to a LAN8742A PHY on the base board (PX4 defconfig CONFIG_ETH0_PHY_LAN8742A); the 50 MHz REF_CLK",
            "is generated by the PHY and fed into PA1. ETH_POWER_EN (PG15) lets the FMU switch the PHY off.",
            "SPI6 'EXTERNAL1' is the payload SPI bus: 2 chip selects, 2 data-ready inputs, a reset and SPIX_SYNC.",
            "FMU_CH9-12, CAN3, SPAREnn, ETH_RX_ER and ETH_PHY_nINT are defined by DS-010 but unconnected on FMUv6X.",
            "PH11 on pin 50 is the same MCU pin as FMU_CH3 (X1-13); the base exposes it on the debug port pin 8.",
        ])


def sheet_j3():
    return connector_sheet(
        "06_j3_imu_flex_34pin.svg", "Sheet 6 · J3 IMU flex connector, 34-pin",
        "Hirose BM20B(0.8)-34DP-0.4V(53) · FPC to the vibration-isolated IMU board (BMI088, ICM-42688-P, RM3100, ICP-20100, 24LC64)",
        "J3 'FLEX'", "BM20B(0.8)-34DP-0.4V(53)  ·  M1-M4 = shield/GND", J3,
        notes=[
            "Two SPI buses cross the flex: SPI3 (BMI088: separate accel and gyro chip selects, gyro INT3 as DRDY)",
            "and SPI2 (ICM-42688-P: one chip select, INT2 as DRDY). Both run at up to 10 MHz, so every signal has a GND neighbour.",
            "I2C4 (PF14/PF15) reaches the IMU board for RM3100 (0x20), ICP-20100 #1 (0x63/0x64), and the 24LC64 cal EEPROM (0x50).",
            "Three switched 3.3 V rails cross (SENSORS2/3/4) plus raw VDD_5V_IN for the heater resistors; HEATER is the control line.",
            "Pinout is taken from DS-012 p.17 (the standard flex pinout); CUAV's silkscreen 'FLEX' and connector position match the reference.",
        ])


# --------------------------------------------------------------------------
# netlist.csv
# --------------------------------------------------------------------------
def write_netlist():
    rows = []
    for pin, fn, net, dest in PINS:
        rows.append(("U1", pin, fn, net, dest))
    for p, net in X1.items():
        rows.append(("X1", str(p), "PAB 100-pin", net, ", ".join(NET_TO_MCU.get(net, [])) or ("rail" if net in POWER_NETS or net == "GND" else "")))
    for p, net in X2.items():
        rows.append(("X2", str(p), "PAB 50-pin", net, "n.c. on FMUv6X" if net in X2_NC else (", ".join(NET_TO_MCU.get(net, [])) or ("rail" if net in POWER_NETS or net == "GND" else ""))))
    for p, net in J3.items():
        rows.append(("J3", str(p), "IMU flex 34-pin", net, ", ".join(NET_TO_MCU.get(net, [])) or ("rail" if net in POWER_NETS or net == "GND" else "")))
    with open(os.path.join(HERE, "netlist.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["refdes", "pin", "function", "net", "connects_to"])
        w.writerows(rows)
    return len(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    out = [sheet_mcu(), sheet_core(), sheet_power_sensors(), sheet_x1(), sheet_x2(), sheet_j3()]
    n = write_netlist()
    for p in out:
        print("wrote", os.path.relpath(p, HERE))
    print(f"wrote netlist.csv ({n} rows)")
    # sanity: every X1/X2/J3 signal net that is not GND/power/NC must map to an MCU pin
    missing = []
    for name, tbl, nc in (("X1", X1, set()), ("X2", X2, X2_NC), ("J3", J3, set())):
        for p, net in tbl.items():
            if net in ("GND",) or net in POWER_NETS or net in nc:
                continue
            if net not in NET_TO_MCU:
                missing.append(f"{name}-{p} {net}")
    if missing:
        print("WARNING unmapped nets:", missing)


if __name__ == "__main__":
    main()
