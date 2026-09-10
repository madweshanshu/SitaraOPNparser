"""
Build the three master CSVs from the device-specific extracted CSVs.

Run this once after extract_tables.py, or whenever a new device is added.
After this script, parse_opn.py only needs the master_*.csv files.

Outputs:
  master_orderable.csv   - all OPNs across all device lines
  master_speed_grades.csv - all speed grades with unified column names
  master_features.csv    - one row per device variant with standardised features
"""

import csv
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def path(name):
    return os.path.join(SCRIPT_DIR, name)


def load_csv(name):
    with open(path(name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(name, header, rows):
    with open(path(name), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {name}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_base(opn, known_bases):
    """Return the base part from an OPN string."""
    for length in (7, 6):
        candidate = opn[:length]
        if candidate in known_bases:
            return candidate
    return ""


AM62X_BASES = {
    "AM6254", "AM6252", "AM6251",
    "AM6234", "AM6232", "AM6231",
    "AM6204", "AM6202", "AM6201",
}
AM62L_BASES = {"AM62L32", "AM62L31"}
AM62A_BASES = {"AM62A74", "AM62A72", "AM62A34", "AM62A32", "AM62A31", "AM62A14", "AM62A12"}
AM62P_BASES = {"AM62P54", "AM62P52", "AM62P34", "AM62P32"}


# ---------------------------------------------------------------------------
# master_orderable.csv
# ---------------------------------------------------------------------------

def build_orderable():
    header = [
        "Device Line", "Base Part",
        "Orderable Part Number", "Status", "Material Type",
        "Package | Pins", "Package Qty | Carrier", "RoHS",
        "Lead Finish / Ball Material", "MSL Rating / Peak Reflow",
        "Op Temp (C)", "Part Marking",
    ]
    rows = []

    for fname, device_line, bases in [
        ("orderable_info.csv",       "AM62x", AM62X_BASES),
        ("am62l_orderable_info.csv", "AM62L", AM62L_BASES),
        ("am62a_orderable_info.csv", "AM62A", AM62A_BASES),
        ("am62p_orderable_info.csv", "AM62P", AM62P_BASES),
    ]:
        for r in load_csv(fname):
            opn = r.get("Orderable Part Number", "").strip()
            base = detect_base(opn, bases)
            rows.append({
                "Device Line":               device_line,
                "Base Part":                 base,
                "Orderable Part Number":     opn,
                "Status":                    r.get("Status", ""),
                "Material Type":             r.get("Material Type", ""),
                "Package | Pins":            r.get("Package | Pins", ""),
                "Package Qty | Carrier":     r.get("Package Qty | Carrier", ""),
                "RoHS":                      r.get("RoHS", ""),
                "Lead Finish / Ball Material": r.get("Lead Finish / Ball Material", ""),
                "MSL Rating / Peak Reflow":  r.get("MSL Rating / Peak Reflow", ""),
                "Op Temp (C)":               r.get("Op Temp (C)", ""),
                "Part Marking":              r.get("Part Marking", ""),
            })

    write_csv("master_orderable.csv", header, rows)


# ---------------------------------------------------------------------------
# master_speed_grades.csv
#
# Unified columns for both families.
# AM62x columns: A53SS @ 0.75V, A53SS @ 0.85V, GPU, PRU, Main Infra/CBA,
#                MCUSS/M4F, Device/Power Mgr, SMS Subsystem, OCSRAM
# AM62L columns: MAIN_SYSCLK0, PER_SYSCLK0, WKUP_SYSCLK0
# Shared: DDR4, LPDDR4
# ---------------------------------------------------------------------------

def build_speed_grades():
    header = [
        "Device Line", "Speed Grade",
        "A53SS @ 0.75V (MHz)", "A53SS @ 0.85V (MHz)",
        # AM62x subsystems
        "GPU (MHz)", "PRU (MHz)", "Main Infra/CBA (MHz)",
        "MCUSS/M4F (MHz)", "Device/Power Mgr (MHz)", "SMS Subsystem (MHz)",
        "OCSRAM (MHz)",
        # AM62L subsystems
        "MAIN_SYSCLK0 (MHz)", "PER_SYSCLK0 (MHz)", "WKUP_SYSCLK0 (MHz)",
        # AM62A subsystems
        "C7x @ 0.75V (MHz)", "C7x @ 0.85V (MHz)",
        "MAIN_SYSCLK (MHz)", "MCU R5F (MHz)", "Device Mgr R5F (MHz)",
        "HSM (MHz)", "VPAC (MHz)", "VENC/VDEC (MHz)", "MJPEG (MHz)",
        # AM62P subsystems (GPU has voltage split)
        "GPU @ 0.75V (MHz)", "GPU @ 0.85V (MHz)", "VPU (MHz)",
        # Shared memory
        "DDR4 (MT/s)", "LPDDR4 (MT/s)",
    ]

    rows = []

    # AM62x: grade T has two raw rows (0.75/0.85 and 0.85-only 1400 override)
    am62x_raw = load_csv("speed_grades.csv")
    grade_rows = {}
    for r in am62x_raw:
        g = r.get("Speed Grade", "").strip()
        if g:
            grade_rows[g] = r
        else:
            # Continuation row for T (1400 MHz @ 0.85V only)
            grade_rows["T_085"] = r

    for grade, r in [("G", grade_rows.get("G", {})),
                     ("K", grade_rows.get("K", {})),
                     ("S", grade_rows.get("S", {})),
                     ("T", grade_rows.get("T", {}))]:
        a53_075 = r.get("MAXIMUM OPERATING FREQUENCY (MHz) A53SS (Cortex- A53x)", "")
        a53_085 = (grade_rows.get("T_085", {})
                   .get("MAXIMUM OPERATING FREQUENCY (MHz) A53SS (Cortex- A53x)", "")
                   if grade == "T" else a53_075)
        rows.append({
            "Device Line":              "AM62x",
            "Speed Grade":              grade,
            "A53SS @ 0.75V (MHz)":      a53_075,
            "A53SS @ 0.85V (MHz)":      a53_085 or a53_075,
            "GPU (MHz)":                r.get("GPU", ""),
            "PRU (MHz)":                r.get("PRU", ""),
            "Main Infra/CBA (MHz)":     r.get("Main Infra (CBA)", ""),
            "MCUSS/M4F (MHz)":          r.get("MCUSS (Cortex- M4F)", ""),
            "Device/Power Mgr (MHz)":   r.get("Device/ Power Manager (Cortex- R5F)", ""),
            "SMS Subsystem (MHz)":      r.get("SMS Subsystem (Dual Cortex- M4F)", ""),
            "OCSRAM (MHz)":             r.get("OCSRAM", ""),
            "MAIN_SYSCLK0 (MHz)":       "",
            "PER_SYSCLK0 (MHz)":        "",
            "WKUP_SYSCLK0 (MHz)":       "",
            "DDR4 (MT/s)":              r.get("MAXIMUM TRANSITION RATE (MT/s)(2) DDR4", ""),
            "LPDDR4 (MT/s)":            r.get("LPDDR4", ""),
        })

    # AM62L
    for r in load_csv("am62l_speed_grades.csv"):
        g = r.get("Speed Grade", "").strip()
        if not g:
            continue
        a53 = r.get("MAXIMUM OPERATING FREQUNCY (MHz) A53SS (Cortex-A53x)", "")
        rows.append({
            "Device Line":              "AM62L",
            "Speed Grade":              g,
            "A53SS @ 0.75V (MHz)":      a53,
            "A53SS @ 0.85V (MHz)":      a53,
            "GPU (MHz)":                "",
            "PRU (MHz)":                "",
            "Main Infra/CBA (MHz)":     "",
            "MCUSS/M4F (MHz)":          "",
            "Device/Power Mgr (MHz)":   "",
            "SMS Subsystem (MHz)":      "",
            "OCSRAM (MHz)":             "",
            "MAIN_SYSCLK0 (MHz)":       r.get("MAIN_SYSCLK0", ""),
            "PER_SYSCLK0 (MHz)":        r.get("PER_SYSCLK0", ""),
            "WKUP_SYSCLK0 (MHz)":       r.get("WKUP_SYSCLK0", ""),
            "DDR4 (MT/s)":              r.get("MAXIMUM TRANSITION RATE (MT/s)(1) DDR4", ""),
            "LPDDR4 (MT/s)":            r.get("LPDDR4", ""),
        })

    # AM62A: 10 grades (M-V), many with 0.75V/0.85V split rows
    # Continuation rows have blank Speed Grade cell; merge into previous grade.
    A53_COL  = "MAXIMUM OPERATING FREQUENCY (MHz) A53SS (Cortex- A53x)"
    C7X_COL  = "C7x"
    MAIN_COL = "MAIN SYSCLK"
    MCU_COL  = "MCU R5F / SYSCLK"
    DEV_COL  = "DEVICE MANAGER R5F / CLK"
    HSM_COL  = "HSM"
    VPAC_COL = "VPAC"
    VENC_COL = "VENC / VDEC"
    MJPEG_COL = "MJPEG"
    LPDDR4_COL = "MAXIMUM TRANSITION RATE (MT/s) (2) LPDDR4"

    am62a_raw = load_csv("am62a_speed_grades.csv")
    # Build a dict: grade -> {base_row, cont_row}
    am62a_grades = {}
    last_grade = None
    for r in am62a_raw:
        g = r.get("Speed Grade", "").strip()
        if g:
            last_grade = g
            am62a_grades[g] = {"base": r, "cont": {}}
        elif last_grade:
            am62a_grades[last_grade]["cont"] = r

    for grade in ["M","N","O","P","Q","R","S","T","U","V"]:
        if grade not in am62a_grades:
            continue
        base = am62a_grades[grade]["base"]
        cont = am62a_grades[grade]["cont"]
        a53_075 = base.get(A53_COL, "")
        a53_085 = cont.get(A53_COL, "") or a53_075
        c7x_075 = base.get(C7X_COL, "")
        c7x_085 = cont.get(C7X_COL, "") or c7x_075
        rows.append({
            "Device Line":           "AM62A",
            "Speed Grade":           grade,
            "A53SS @ 0.75V (MHz)":   a53_075,
            "A53SS @ 0.85V (MHz)":   a53_085,
            "C7x @ 0.75V (MHz)":     c7x_075,
            "C7x @ 0.85V (MHz)":     c7x_085,
            "MAIN_SYSCLK (MHz)":     base.get(MAIN_COL, ""),
            "MCU R5F (MHz)":         base.get(MCU_COL, ""),
            "Device Mgr R5F (MHz)":  base.get(DEV_COL, ""),
            "HSM (MHz)":             base.get(HSM_COL, ""),
            "VPAC (MHz)":            base.get(VPAC_COL, ""),
            "VENC/VDEC (MHz)":       base.get(VENC_COL, ""),
            "MJPEG (MHz)":           base.get(MJPEG_COL, ""),
            "DDR4 (MT/s)":           "",
            "LPDDR4 (MT/s)":         base.get(LPDDR4_COL, ""),
        })

    # AM62P: grades O/S/T/U/V; GPU has voltage split on U/V
    P_A53_COL  = "MAXIMUM OPERATING FREQUNCY (MHz) A53SS (Cortex- A53x)"
    P_MAIN_COL = "MAIN DOMAIN SYSCLK"
    P_MCU_R5F  = "MCU R5F"
    P_MCU_SYS  = "MCU DOMAIN SYSCLK"
    P_DEV_R5F  = "DEVICE MANAGER R5F"
    P_DEV_CLK  = "DEVICE MANAGER DOMAIN CLK"
    P_HSM_COL  = "HSM"
    P_GPU_COL  = "GPU"
    P_VPU_COL  = "VPU"
    P_DDR_COL  = "MAXIMUM TRANSITION RATE (MT/s) (2) LPDDR4"

    am62p_raw = load_csv("am62p_speed_grades.csv")
    am62p_grades = {}
    last_pg = None
    for r in am62p_raw:
        g = r.get("Speed Grade", "").strip()
        if g:
            last_pg = g
            am62p_grades[g] = {"base": r, "cont": {}}
        elif last_pg:
            am62p_grades[last_pg]["cont"] = r

    for grade in ["O", "S", "T", "U", "V"]:
        if grade not in am62p_grades:
            continue
        base = am62p_grades[grade]["base"]
        cont = am62p_grades[grade]["cont"]
        a53_075 = base.get(P_A53_COL, "")
        a53_085 = cont.get(P_A53_COL, "") or a53_075
        gpu_075 = base.get(P_GPU_COL, "")
        gpu_085 = cont.get(P_GPU_COL, "") or gpu_075
        mcu_combined = f"{base.get(P_MCU_R5F,'')} / {base.get(P_MCU_SYS,'')}".strip(" /")
        dev_combined = f"{base.get(P_DEV_R5F,'')} / {base.get(P_DEV_CLK,'')}".strip(" /")
        rows.append({
            "Device Line":           "AM62P",
            "Speed Grade":           grade,
            "A53SS @ 0.75V (MHz)":   a53_075,
            "A53SS @ 0.85V (MHz)":   a53_085,
            "MAIN_SYSCLK (MHz)":     base.get(P_MAIN_COL, ""),
            "MCU R5F (MHz)":         mcu_combined,
            "Device Mgr R5F (MHz)":  dev_combined,
            "HSM (MHz)":             base.get(P_HSM_COL, ""),
            "GPU @ 0.75V (MHz)":     gpu_075,
            "GPU @ 0.85V (MHz)":     gpu_085,
            "VPU (MHz)":             base.get(P_VPU_COL, ""),
            "DDR4 (MT/s)":           "",
            "LPDDR4 (MT/s)":         base.get(P_DDR_COL, ""),
        })

    write_csv("master_speed_grades.csv", header, rows)


# ---------------------------------------------------------------------------
# master_features.csv
#
# One row per device variant. Columns are standardised feature names.
# Empty cell = feature not present / not applicable for that device.
# ---------------------------------------------------------------------------

FEATURES_HEADER = [
    "Device Line", "Base Part", "Family", "Description", "A53 Cores",
    "Speed Grades Available",
    "GPU", "PRUSS", "Cortex-M4F", "Security Controller",
    "Crypto Accelerators",
    # AM62A-specific accelerators
    "C7x AI Accel", "VPAC", "VENC/VDEC", "MJPEG",
    # AM62P-specific
    "VPU",
    "CSI-RX", "ADC",
    "Display",
    "CAN", "I2C", "UART", "SPI", "McASP",
    "eMMC", "SD/SDIO",
    "USB 2.0", "Ethernet (CPSW3G)",
    "GPIO", "ePWM", "eCAP", "eQEP", "Timers", "GTC",
    "OCSRAM Main", "OCSRAM MCU",
    "DDR Support", "GPMC", "OSPI/QSPI", "RTC",
]

# Map verbose PDF feature names to our standard column names
AM62X_FEAT_MAP = {
    "Arm Cortex-A53 Microprocessor Subsystem":                   "A53 Cores",
    "3D Graphics Engine (OpenGL ES 3.1, Vulkan 1.2)":            "GPU",
    "Programmable Real-Time Unit Subsystem(3)":                  "PRUSS",
    "Arm Cortex-M4F in MCU domain":                              "Cortex-M4F",
    "Crypto Accelerators":                                        "Crypto Accelerators",
    "CSI2-RX Controller with DPHY":                              "CSI-RX",
    "Display Subsystem":                                          "Display",
    "Modular Controller Area Network Interface with Full CAN-FD Support": "CAN",
    "Inter-Integrated Circuit Interface":                         "I2C",
    "Universal Asynchronous Receiver and Transmitter":            "UART",
    "Multichannel Serial Peripheral Interface":                   "SPI",
    "Multichannel Audio Serial Port":                             "McASP",
    "Multi-Media Card/ Secure Digital Interface":                 "eMMC/SD raw",
    "USB2.0 Controller with PHY":                                 "USB 2.0",
    "Gigabit Ethernet Interface":                                 "Ethernet (CPSW3G)",
    "General-Purpose I/O":                                        "GPIO",
    "Enhanced Pulse-Width Modulator Module":                      "ePWM",
    "Enhanced Capture Module":                                    "eCAP",
    "Enhanced Quadrature Encoder Pulse Module":                   "eQEP",
    "General-Purpose Timers":                                     "Timers",
    "Global Timer Counter":                                       "GTC",
    "On-Chip Shared Memory (RAM) in MAIN Domain":                "OCSRAM Main",
    "On-Chip Shared Memory (RAM) in M4F Domain":                 "OCSRAM MCU",
    "DDR4/LPDDR4 DDR Subsystem":                                  "DDR Support",
    "General-Purpose Memory Controller":                          "GPMC",
    "Flash Subsystem (FSS)(2)":                                   "OSPI/QSPI",
}

AM62L_FEAT_MAP = {
    "Arm Cortex-A53 Microprocessor Subsystem":                   "A53 Cores",
    "Security Controller":                                        "Security Controller",
    "Crypto Accelerators":                                        "Crypto Accelerators",
    "Analog-to-Digital Converter":                               "ADC",
    "Display Subsystem":                                          "Display",
    "Modular Controller Area Network with Full CAN-FD Support":  "CAN",
    "Inter-Integrated Circuit Interface":                         "I2C",
    "Universal Asynchronous Receiver and Transmitter":            "UART",
    "Multichannel Serial Peripheral Interface":                   "SPI",
    "Multichannel Audio Serial Port":                             "McASP",
    "Multi-Media Card/Secure Digital Interface":                  "eMMC/SD raw",
    "USB2.0 Controller with PHY":                                 "USB 2.0",
    "Gigabit Ethernet Interface":                                 "Ethernet (CPSW3G)",
    "General-Purpose I/O":                                        "GPIO",
    "Enhanced Pulse-Width Modulator Module":                      "ePWM",
    "Enhanced Capture Module":                                    "eCAP",
    "Enhanced Quadrature Encoder Pulse Module":                   "eQEP",
    "General-Purpose Timers":                                     "Timers",
    "Global Timer Counter":                                       "GTC",
    "On-Chip Shared Memory (RAM)":                               "OCSRAM Main",
    "OCSRAM in WKUP Domain":                                     "OCSRAM MCU",
    "DDR Subsystem":                                              "DDR Support",
    "DDRSS with LPDDR4":                                          "DDR Support LPDDR4",
    "General-Purpose Memory Controller":                          "GPMC",
    "Flash Subsystem (FSS)(2)":                                   "OSPI/QSPI",
    "Real Time Clock":                                            "RTC",
}

AM62X_DEVICE_META = {
    "AM6254": {"family": "AM625",    "desc": "Human-machine Interaction SoC",   "speed_grades": "G/K/S/T"},
    "AM6252": {"family": "AM625",    "desc": "Human-machine Interaction SoC",   "speed_grades": "G/K/S/T"},
    "AM6251": {"family": "AM625",    "desc": "Human-machine Interaction SoC",   "speed_grades": "G/K/S/T"},
    "AM6234": {"family": "AM623",    "desc": "IoT and Gateway SoC",             "speed_grades": "G/K/S/T"},
    "AM6232": {"family": "AM623",    "desc": "IoT and Gateway SoC",             "speed_grades": "G/K/S/T"},
    "AM6231": {"family": "AM623",    "desc": "IoT and Gateway SoC",             "speed_grades": "G/K/S/T"},
    "AM6204": {"family": "AM620-Q1", "desc": "Automotive Display SoC",         "speed_grades": "G/K/S/T"},
    "AM6202": {"family": "AM620-Q1", "desc": "Automotive Display SoC",         "speed_grades": "G/K/S/T"},
    "AM6201": {"family": "AM620-Q1", "desc": "Automotive Display SoC",         "speed_grades": "G/K/S/T"},
}

AM62L_DEVICE_META = {
    "AM62L32": {"family": "AM62L", "desc": "Low-power IoT/HMI SoC", "speed_grades": "E/O"},
    "AM62L31": {"family": "AM62L", "desc": "Low-power IoT/HMI SoC", "speed_grades": "E/O"},
}

AM62A_FEAT_MAP = {
    "Arm Cortex-A53 Microprocessor Subsystem":           "A53 Cores",
    "Arm Cortex-R5F in MCU domain":                      "Cortex-M4F",   # R5F fills same safety role
    "C7xV-256 Deep Learning Accelerator":                "C7x AI Accel",
    "Vision Processing Accelerators":                    "VPAC",
    "Video Encoder / Decoder":                           "VENC/VDEC",
    "Motion JPEG Encoder":                               "MJPEG",
    "Hardware Security Module":                          "Security Controller",
    "Crypto Accelerators":                               "Crypto Accelerators",
    "Display Subsystem(2)":                              "Display",
    "Modular Controller Area Network Interface":         "CAN",
    "Inter-Integrated Circuit Interface":                "I2C",
    "Universal Asynchronous Receiver and Transmitter":   "UART",
    "Multichannel Serial Peripheral Interface":          "SPI",
    "Multichannel Audio Serial Port":                    "McASP",
    "Multi-Media Card/ Secure Digital Interface":        "eMMC/SD raw",
    "USB2.0 Controller with PHY":                        "USB 2.0",
    "Gigabit Ethernet Interface":                        "Ethernet (CPSW3G)",
    "General-Purpose I/O":                               "GPIO",
    "Enhanced Pulse-Width Modulator Module":             "ePWM",
    "Enhanced Capture Module":                           "eCAP",
    "Enhanced Quadrature Encoder Pulse Module":          "eQEP",
    "General-Purpose Timers":                            "Timers",
    "On-Chip Shared Memory (RAM) in MAIN Domain":        "OCSRAM Main",
    "On-Chip Shared Memory (RAM) in MCU Domain":         "OCSRAM MCU",
    "LPDDR4 DDR Subsystem":                              "DDR Support",
    "General-Purpose Memory Controller":                 "GPMC",
    "OSPI/QSPI/SPI(3) Flash Subsystem":                  "OSPI/QSPI",
    "CSI2-RX Controller with DPHY":                      "CSI-RX",
}

AM62P_FEAT_MAP = {
    "Arm Cortex-A53 Microprocessor Subsystem":            "A53 Cores",
    "Arm Cortex-R5F in MCU domain":                       "Cortex-M4F",
    "Graphics Processing Unit":                           "GPU",
    "Video Encoder / Decoder":                            "VENC/VDEC",
    "Hardware Security Module":                           "Security Controller",
    "Crypto Accelerators":                                "Crypto Accelerators",
    "Display Subsystem":                                  "Display",
    "Modular Controller Area Network Interface":          "CAN",
    "Inter-Integrated Circuit Interface":                 "I2C",
    "Universal Asynchronous Receiver and Transmitter":    "UART",
    "Multichannel Serial Peripheral Interface":           "SPI",
    "Multichannel Audio Serial Port":                     "McASP",
    "Multi-Media Card/ Secure Digital Interface":         "eMMC/SD raw",
    "USB2.0 Controller with PHY":                         "USB 2.0",
    "Gigabit Ethernet Interface":                         "Ethernet (CPSW3G)",
    "General-Purpose I/O":                                "GPIO",
    "Enhanced Pulse-Width Modulator Module":              "ePWM",
    "Enhanced Capture Module":                            "eCAP",
    "Enhanced Quadrature Encoder Pulse Module":           "eQEP",
    "General-Purpose Timers":                             "Timers",
    "Global Timer Counter":                               "GTC",
    "On-Chip Shared Memory (RAM) in MAIN Domain":         "OCSRAM Main",
    "On-Chip Shared Memory (RAM) in MCU Domain":          "OCSRAM MCU",
    "LPDDR4 DDR Subsystem":                               "DDR Support",
    "General-Purpose Memory Controller":                  "GPMC",
    "Flash Subsystem (FSS)(2)":                           "OSPI/QSPI",
    "CSI2-RX Controller with DPHY":                       "CSI-RX",
    "VENC/VDEC":                                          "VENC/VDEC",
}

AM62P_DEVICE_META = {
    "AM62P54": {"family": "AM62P5",    "desc": "Premium HMI SoC with GPU",    "speed_grades": "O/S/T/U/V"},
    "AM62P52": {"family": "AM62P5",    "desc": "Premium HMI SoC with GPU",    "speed_grades": "O/S/T/U/V"},
    "AM62P34": {"family": "AM62P3",    "desc": "Premium HMI SoC without GPU", "speed_grades": "O/S/T/U/V"},
    "AM62P32": {"family": "AM62P3",    "desc": "Premium HMI SoC without GPU", "speed_grades": "O/S/T/U/V"},
}

AM62A_DEVICE_META = {
    "AM62A74": {"family": "AM62A7",    "desc": "Edge AI Vision SoC", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
    "AM62A72": {"family": "AM62A7",    "desc": "Edge AI Vision SoC", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
    "AM62A34": {"family": "AM62A3",    "desc": "Edge AI Vision SoC", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
    "AM62A32": {"family": "AM62A3",    "desc": "Edge AI Vision SoC", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
    "AM62A31": {"family": "AM62A3",    "desc": "Edge AI Vision SoC", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
    "AM62A14": {"family": "AM62A1-Q1", "desc": "Edge AI Vision SoC (Automotive)", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
    "AM62A12": {"family": "AM62A1-Q1", "desc": "Edge AI Vision SoC (Automotive)", "speed_grades": "M/N/O/P/Q/R/S/T/U/V"},
}


def extract_features_for_variant(comp_rows, device_col, feat_map):
    """Read device_comparison rows and return a dict of standard_col -> value."""
    result = {}
    for row in comp_rows:
        feat_name = row.get("FEATURES", "").strip()
        std_col = feat_map.get(feat_name)
        if not std_col:
            continue
        val = row.get(device_col, "").strip()
        if val:
            result[std_col] = val
    return result


def split_emmc_sd(raw):
    """Split 'eMMC/SD raw' feature into separate eMMC and SD columns."""
    emmc, sd = "", ""
    if not raw:
        return emmc, sd
    parts = [p.strip() for p in re.split(r"\n|;", raw)]
    for p in parts:
        pl = p.lower()
        if "emmc" in pl:
            emmc = p
        elif "sd" in pl or "sdio" in pl:
            sd = (sd + " / " + p).strip(" / ") if sd else p
    return emmc, sd


def build_features():
    rows = []

    # --- AM62x ---
    comp_rows = load_csv("device_comparison.csv")
    # Column names in the comparison CSV for each base part
    col_map = {
        "AM6254": "AM625, AM625-Q1 AM6254",
        "AM6252": "AM6252",
        "AM6251": "AM6251",
        "AM6234": "AM623 AM6234",
        "AM6232": "AM6232",
        "AM6231": "AM6231",
        "AM6204": "AM620-Q1 AM6204",
        "AM6202": "AM6202",
        "AM6201": "AM6201",
    }
    # Family fallback for merged cells
    family_lead = {
        "AM6254": "AM625, AM625-Q1 AM6254",
        "AM6252": "AM625, AM625-Q1 AM6254",
        "AM6251": "AM625, AM625-Q1 AM6254",
        "AM6234": "AM623 AM6234",
        "AM6232": "AM623 AM6234",
        "AM6231": "AM623 AM6234",
        "AM6204": "AM620-Q1 AM6204",
        "AM6202": "AM620-Q1 AM6204",
        "AM6201": "AM620-Q1 AM6204",
    }

    def get_feat(base, feat_map):
        direct = extract_features_for_variant(comp_rows, col_map[base], feat_map)
        lead   = extract_features_for_variant(comp_rows, family_lead[base], feat_map)
        fallback = extract_features_for_variant(comp_rows, "AM625, AM625-Q1 AM6254", feat_map)
        merged = {}
        for col in set(list(direct) + list(lead) + list(fallback)):
            merged[col] = direct.get(col) or lead.get(col) or fallback.get(col) or ""
        return merged

    for base, meta in AM62X_DEVICE_META.items():
        f = get_feat(base, AM62X_FEAT_MAP)
        emmc, sd = split_emmc_sd(f.get("eMMC/SD raw", ""))
        row = {col: "" for col in FEATURES_HEADER}
        row.update({
            "Device Line":          "AM62x",
            "Base Part":            base,
            "Family":               meta["family"],
            "Description":          meta["desc"],
            "Speed Grades Available": meta["speed_grades"],
            "A53 Cores":            f.get("A53 Cores", ""),
            "GPU":                  f.get("GPU", ""),
            "PRUSS":                f.get("PRUSS", ""),
            "Cortex-M4F":           f.get("Cortex-M4F", ""),
            "Security Controller":  "Yes",
            "Crypto Accelerators":  f.get("Crypto Accelerators", ""),
            "CSI-RX":               f.get("CSI-RX", ""),
            "ADC":                  "",
            "Display":              f.get("Display", ""),
            "CAN":                  f.get("CAN", ""),
            "I2C":                  f.get("I2C", ""),
            "UART":                 f.get("UART", ""),
            "SPI":                  f.get("SPI", ""),
            "McASP":                f.get("McASP", ""),
            "eMMC":                 emmc,
            "SD/SDIO":              sd,
            "USB 2.0":              f.get("USB 2.0", ""),
            "Ethernet (CPSW3G)":    f.get("Ethernet (CPSW3G)", ""),
            "GPIO":                 f.get("GPIO", ""),
            "ePWM":                 f.get("ePWM", ""),
            "eCAP":                 f.get("eCAP", ""),
            "eQEP":                 f.get("eQEP", ""),
            "Timers":               f.get("Timers", ""),
            "GTC":                  f.get("GTC", ""),
            "OCSRAM Main":          f.get("OCSRAM Main", ""),
            "OCSRAM MCU":           f.get("OCSRAM MCU", ""),
            "DDR Support":          f.get("DDR Support", ""),
            "GPMC":                 f.get("GPMC", ""),
            "OSPI/QSPI":            f.get("OSPI/QSPI", ""),
            "RTC":                  "",
        })
        rows.append(row)

    # --- AM62L ---
    comp_rows_l = load_csv("am62l_device_comparison.csv")
    col_map_l = {"AM62L32": "AM62L32", "AM62L31": "AM62L31"}

    for base, meta in AM62L_DEVICE_META.items():
        f = extract_features_for_variant(comp_rows_l, col_map_l[base], AM62L_FEAT_MAP)
        # Fallback to AM62L32 for merged cells
        if base == "AM62L31":
            fb = extract_features_for_variant(comp_rows_l, "AM62L32", AM62L_FEAT_MAP)
            for col in fb:
                if not f.get(col):
                    f[col] = fb[col]
        emmc, sd = split_emmc_sd(f.get("eMMC/SD raw", ""))
        # Combine DDR fields
        ddr = f.get("DDR Support", "")
        ddr_lp = f.get("DDR Support LPDDR4", "")
        ddr_combined = "; ".join(x for x in [ddr, ddr_lp] if x)
        row = {col: "" for col in FEATURES_HEADER}
        row.update({
            "Device Line":          "AM62L",
            "Base Part":            base,
            "Family":               meta["family"],
            "Description":          meta["desc"],
            "Speed Grades Available": meta["speed_grades"],
            "A53 Cores":            f.get("A53 Cores", ""),
            "GPU":                  "No",
            "PRUSS":                "No",
            "Cortex-M4F":           "No",
            "Security Controller":  f.get("Security Controller", ""),
            "Crypto Accelerators":  f.get("Crypto Accelerators", ""),
            "CSI-RX":               "No",
            "ADC":                  f.get("ADC", ""),
            "Display":              f.get("Display", ""),
            "CAN":                  f.get("CAN", ""),
            "I2C":                  f.get("I2C", ""),
            "UART":                 f.get("UART", ""),
            "SPI":                  f.get("SPI", ""),
            "McASP":                f.get("McASP", ""),
            "eMMC":                 emmc,
            "SD/SDIO":              sd,
            "USB 2.0":              f.get("USB 2.0", ""),
            "Ethernet (CPSW3G)":    f.get("Ethernet (CPSW3G)", ""),
            "GPIO":                 f.get("GPIO", ""),
            "ePWM":                 f.get("ePWM", ""),
            "eCAP":                 f.get("eCAP", ""),
            "eQEP":                 f.get("eQEP", ""),
            "Timers":               f.get("Timers", ""),
            "GTC":                  f.get("GTC", ""),
            "OCSRAM Main":          f.get("OCSRAM Main", ""),
            "OCSRAM MCU":           f.get("OCSRAM MCU", ""),
            "DDR Support":          ddr_combined,
            "GPMC":                 f.get("GPMC", ""),
            "OSPI/QSPI":            f.get("OSPI/QSPI", ""),
            "RTC":                  f.get("RTC", ""),
        })
        rows.append(row)

    # --- AM62A ---
    comp_rows_a = load_csv("am62a_device_comparison.csv")
    col_map_a = {
        "AM62A74": "AM62A7, AM62A7-Q1 AM62A74",
        "AM62A72": "AM62A72",
        "AM62A34": "AM62A3, AM62A3-Q1 AM62A34",
        "AM62A32": "AM62A32",
        "AM62A31": "AM62A31",
        "AM62A14": "AM62A1-Q1 AM62A14",
        "AM62A12": "AM62A12",
    }
    family_lead_a = {
        "AM62A74": "AM62A7, AM62A7-Q1 AM62A74",
        "AM62A72": "AM62A7, AM62A7-Q1 AM62A74",
        "AM62A34": "AM62A3, AM62A3-Q1 AM62A34",
        "AM62A32": "AM62A3, AM62A3-Q1 AM62A34",
        "AM62A31": "AM62A3, AM62A3-Q1 AM62A34",
        "AM62A14": "AM62A1-Q1 AM62A14",
        "AM62A12": "AM62A1-Q1 AM62A14",
    }
    fallback_a = "AM62A7, AM62A7-Q1 AM62A74"

    for base, meta in AM62A_DEVICE_META.items():
        direct   = extract_features_for_variant(comp_rows_a, col_map_a[base],    AM62A_FEAT_MAP)
        lead     = extract_features_for_variant(comp_rows_a, family_lead_a[base], AM62A_FEAT_MAP)
        fb       = extract_features_for_variant(comp_rows_a, fallback_a,          AM62A_FEAT_MAP)
        f = {}
        for col in set(list(direct) + list(lead) + list(fb)):
            f[col] = direct.get(col) or lead.get(col) or fb.get(col) or ""
        emmc, sd = split_emmc_sd(f.get("eMMC/SD raw", ""))
        row = {col: "" for col in FEATURES_HEADER}
        row.update({
            "Device Line":          "AM62A",
            "Base Part":            base,
            "Family":               meta["family"],
            "Description":          meta["desc"],
            "Speed Grades Available": meta["speed_grades"],
            "A53 Cores":            f.get("A53 Cores", ""),
            "GPU":                  "No",
            "PRUSS":                "No",
            "Cortex-M4F":           f.get("Cortex-M4F", ""),
            "Security Controller":  f.get("Security Controller", ""),
            "Crypto Accelerators":  f.get("Crypto Accelerators", ""),
            "C7x AI Accel":         f.get("C7x AI Accel", ""),
            "VPAC":                 f.get("VPAC", ""),
            "VENC/VDEC":            f.get("VENC/VDEC", ""),
            "MJPEG":                f.get("MJPEG", ""),
            "CSI-RX":               f.get("CSI-RX", ""),
            "ADC":                  "No",
            "Display":              f.get("Display", ""),
            "CAN":                  f.get("CAN", ""),
            "I2C":                  f.get("I2C", ""),
            "UART":                 f.get("UART", ""),
            "SPI":                  f.get("SPI", ""),
            "McASP":                f.get("McASP", ""),
            "eMMC":                 emmc,
            "SD/SDIO":              sd,
            "USB 2.0":              f.get("USB 2.0", ""),
            "Ethernet (CPSW3G)":    f.get("Ethernet (CPSW3G)", ""),
            "GPIO":                 f.get("GPIO", ""),
            "ePWM":                 f.get("ePWM", ""),
            "eCAP":                 f.get("eCAP", ""),
            "eQEP":                 f.get("eQEP", ""),
            "Timers":               f.get("Timers", ""),
            "GTC":                  "",
            "OCSRAM Main":          f.get("OCSRAM Main", ""),
            "OCSRAM MCU":           f.get("OCSRAM MCU", ""),
            "DDR Support":          f.get("DDR Support", ""),
            "GPMC":                 f.get("GPMC", ""),
            "OSPI/QSPI":            f.get("OSPI/QSPI", ""),
            "RTC":                  "",
        })
        rows.append(row)

    # --- AM62P ---
    comp_rows_p = load_csv("am62p_device_comparison.csv")
    col_map_p = {
        "AM62P54": "AM62P, AM62P-Q1 AM62P54",
        "AM62P52": "AM62P52",
        "AM62P34": "AM62P34",
        "AM62P32": "AM62P32",
    }
    family_lead_p = {
        "AM62P54": "AM62P, AM62P-Q1 AM62P54",
        "AM62P52": "AM62P, AM62P-Q1 AM62P54",
        "AM62P34": "AM62P34",
        "AM62P32": "AM62P34",
    }
    fallback_p = "AM62P, AM62P-Q1 AM62P54"

    for base, meta in AM62P_DEVICE_META.items():
        direct = extract_features_for_variant(comp_rows_p, col_map_p[base],    AM62P_FEAT_MAP)
        lead   = extract_features_for_variant(comp_rows_p, family_lead_p[base], AM62P_FEAT_MAP)
        fb     = extract_features_for_variant(comp_rows_p, fallback_p,          AM62P_FEAT_MAP)
        f = {}
        for col in set(list(direct) + list(lead) + list(fb)):
            f[col] = direct.get(col) or lead.get(col) or fb.get(col) or ""
        emmc, sd = split_emmc_sd(f.get("eMMC/SD raw", ""))
        row = {col: "" for col in FEATURES_HEADER}
        row.update({
            "Device Line":          "AM62P",
            "Base Part":            base,
            "Family":               meta["family"],
            "Description":          meta["desc"],
            "Speed Grades Available": meta["speed_grades"],
            "A53 Cores":            f.get("A53 Cores", ""),
            "GPU":                  f.get("GPU", ""),
            "PRUSS":                "No",
            "Cortex-M4F":           f.get("Cortex-M4F", ""),
            "Security Controller":  f.get("Security Controller", ""),
            "Crypto Accelerators":  f.get("Crypto Accelerators", ""),
            "VENC/VDEC":            f.get("VENC/VDEC", ""),
            "VPU":                  "Yes",
            "CSI-RX":               f.get("CSI-RX", ""),
            "ADC":                  "No",
            "Display":              f.get("Display", ""),
            "CAN":                  f.get("CAN", ""),
            "I2C":                  f.get("I2C", ""),
            "UART":                 f.get("UART", ""),
            "SPI":                  f.get("SPI", ""),
            "McASP":                f.get("McASP", ""),
            "eMMC":                 emmc,
            "SD/SDIO":              sd,
            "USB 2.0":              f.get("USB 2.0", ""),
            "Ethernet (CPSW3G)":    f.get("Ethernet (CPSW3G)", ""),
            "GPIO":                 f.get("GPIO", ""),
            "ePWM":                 f.get("ePWM", ""),
            "eCAP":                 f.get("eCAP", ""),
            "eQEP":                 f.get("eQEP", ""),
            "Timers":               f.get("Timers", ""),
            "GTC":                  f.get("GTC", ""),
            "OCSRAM Main":          f.get("OCSRAM Main", ""),
            "OCSRAM MCU":           f.get("OCSRAM MCU", ""),
            "DDR Support":          f.get("DDR Support", ""),
            "GPMC":                 f.get("GPMC", ""),
            "OSPI/QSPI":            f.get("OSPI/QSPI", ""),
            "RTC":                  "",
        })
        rows.append(row)

    write_csv("master_features.csv", FEATURES_HEADER, rows)


# ---------------------------------------------------------------------------
# master.csv - single denormalized file
# One row per OPN; features and speed grade data joined in.
# ---------------------------------------------------------------------------

def build_consolidated():
    import sys
    sys.path.insert(0, SCRIPT_DIR)
    from parse_opn import parse_opn as _parse_opn

    orderable_rows   = load_csv("master_orderable.csv")
    features_by_base = {r["Base Part"]: r for r in load_csv("master_features.csv")}
    speed_by_key     = {(r["Device Line"], r["Speed Grade"]): r
                        for r in load_csv("master_speed_grades.csv")}

    # Column names from features and speed tables (skip keys already in orderable)
    feat_sample  = load_csv("master_features.csv")[0]
    speed_sample = load_csv("master_speed_grades.csv")[0]

    feat_cols  = [c for c in feat_sample  if c not in ("Device Line", "Base Part")]
    speed_cols = [c for c in speed_sample if c not in ("Device Line", "Speed Grade")]

    header = list(orderable_rows[0].keys()) + ["Speed Grade"] + feat_cols + speed_cols

    rows = []
    for ord_row in orderable_rows:
        opn = ord_row["Orderable Part Number"]
        parsed, _   = _parse_opn(opn)
        speed_grade = parsed["speed_grade"] if parsed else ""
        base        = ord_row["Base Part"]
        dl          = ord_row["Device Line"]

        row = dict(ord_row)
        row["Speed Grade"] = speed_grade

        feat = features_by_base.get(base, {})
        for c in feat_cols:
            row[c] = feat.get(c, "")

        sg_data = speed_by_key.get((dl, speed_grade), {})
        for c in speed_cols:
            row[c] = sg_data.get(c, "")

        rows.append(row)

    write_csv("master.csv", header, rows)


# ---------------------------------------------------------------------------

def main():
    build_orderable()
    build_speed_grades()
    build_features()
    build_consolidated()
    print("\nDone. parse_opn.py now only needs the master_*.csv files.")


if __name__ == "__main__":
    main()
