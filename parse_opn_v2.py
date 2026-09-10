"""
AM62x / AM62L / AM62A / AM62P OPN parser - single master.csv version.

Reads only master.csv (one row per OPN, all data pre-joined).
For OPNs not in the orderable table the naming convention is still
decoded and features/speed data are looked up by base part and speed grade.

Usage:
    python3 parse_opn_v2.py <OPN>
    python3 parse_opn_v2.py          (interactive prompt)
    python3 parse_opn_v2.py -h
"""

import csv
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Reuse naming convention logic from parse_opn.py
sys.path.insert(0, SCRIPT_DIR)
from parse_opn import (
    parse_opn, HELP,
    BASE_PARTS, CORE_COUNT, EVOLUTION_STAGE, REVISION, PACKAGE,
    AM62X_SPEED_GRADE, AM62L_SPEED_GRADE, AM62A_SPEED_GRADE, AM62P_SPEED_GRADE,
    AM62X_FEATURES, AM62L_FEATURES, AM62A_FEATURES, AM62P_FEATURES,
    AM62X_FUNCTIONAL_SAFETY, AM62X_TEMPERATURE, AM62L_TEMPERATURE,
    decode_am62l_security_fs,
)

MASTER_CSV = os.path.join(SCRIPT_DIR, "master.csv")

# Columns from master.csv that belong to each section
ORDERABLE_COLS = [
    "Status", "Material Type", "Package | Pins", "Package Qty | Carrier",
    "RoHS", "Lead Finish / Ball Material", "MSL Rating / Peak Reflow",
    "Op Temp (C)", "Part Marking",
]

FEATURE_COLS = [
    "A53 Cores", "GPU", "PRUSS", "Cortex-M4F", "Security Controller",
    "Crypto Accelerators", "C7x AI Accel", "VPAC", "VENC/VDEC", "MJPEG", "VPU",
    "CSI-RX", "ADC", "Display", "CAN", "I2C", "UART", "SPI", "McASP",
    "eMMC", "SD/SDIO", "USB 2.0", "Ethernet (CPSW3G)", "GPIO",
    "ePWM", "eCAP", "eQEP", "Timers", "GTC",
    "OCSRAM Main", "OCSRAM MCU", "DDR Support", "GPMC", "OSPI/QSPI", "RTC",
]

# Speed grade columns grouped by device line (only non-empty ones will print)
SPEED_COLS = [
    ("A53SS @ 0.75V (MHz)", "A53SS @ 0.85V (MHz)", "A53SS (Cortex-A53)"),
    ("C7x @ 0.75V (MHz)",   "C7x @ 0.85V (MHz)",   "C7x AI Accel"),
    ("GPU @ 0.75V (MHz)",   "GPU @ 0.85V (MHz)",    "GPU"),
    ("GPU (MHz)",           None,                   "GPU"),
    ("PRU (MHz)",           None,                   "PRU"),
    ("Main Infra/CBA (MHz)",None,                   "Main Infra/CBA"),
    ("MCUSS/M4F (MHz)",     None,                   "MCUSS/M4F"),
    ("Device/Power Mgr (MHz)", None,                "Device/Power Mgr"),
    ("SMS Subsystem (MHz)", None,                   "SMS Subsystem"),
    ("OCSRAM (MHz)",        None,                   "OCSRAM"),
    ("MAIN_SYSCLK0 (MHz)",  None,                   "MAIN_SYSCLK0"),
    ("PER_SYSCLK0 (MHz)",   None,                   "PER_SYSCLK0"),
    ("WKUP_SYSCLK0 (MHz)",  None,                   "WKUP_SYSCLK0"),
    ("MAIN_SYSCLK (MHz)",   None,                   "MAIN_SYSCLK"),
    ("MCU R5F (MHz)",       None,                   "MCU R5F"),
    ("Device Mgr R5F (MHz)",None,                   "Device Mgr R5F"),
    ("HSM (MHz)",           None,                   "HSM"),
    ("VPAC (MHz)",          None,                   "VPAC"),
    ("VENC/VDEC (MHz)",     None,                   "VENC/VDEC"),
    ("MJPEG (MHz)",         None,                   "MJPEG"),
    ("VPU (MHz)",           None,                   "VPU"),
    ("DDR4 (MT/s)",         None,                   "DDR4"),
    ("LPDDR4 (MT/s)",       None,                   "LPDDR4"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_master():
    with open(MASTER_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Build lookup by normalised OPN (strip .B suffix, uppercase)
    by_opn = {}
    by_base = {}
    for r in rows:
        key = r["Orderable Part Number"].upper().rstrip(".B").rstrip(".")
        by_opn.setdefault(key, r)          # first match wins
        by_base.setdefault(r["Base Part"], r)
    return rows, by_opn, by_base


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def hr(char="-", width=60):
    return char * width


def decode_speed(parsed):
    dl = parsed["device_line"]
    sg = parsed["speed_grade"]
    if dl == "AM62L":  return AM62L_SPEED_GRADE.get(sg, sg)
    if dl == "AM62A":  return AM62A_SPEED_GRADE.get(sg, sg)
    if dl == "AM62P":  return AM62P_SPEED_GRADE.get(sg, sg)
    return AM62X_SPEED_GRADE.get(sg, sg)


def decode_features(parsed):
    dl = parsed["device_line"]
    f  = parsed["features"]
    if dl == "AM62L":  return AM62L_FEATURES.get(f, f)
    if dl == "AM62A":  return AM62A_FEATURES.get(f, f)
    if dl == "AM62P":  return AM62P_FEATURES.get(f, f)
    return AM62X_FEATURES.get(f, f)


def decode_temp(parsed):
    dl = parsed["device_line"]
    t  = parsed["temperature"]
    if dl == "AM62x":
        return AM62X_TEMPERATURE.get(t, t)
    return AM62L_TEMPERATURE.get(t, t)


def print_parsed_fields(parsed, row):
    base_info = BASE_PARTS.get(parsed["base"], {})
    dl        = parsed["device_line"]

    rows = [
        ("Base Part",       parsed["base"]),
        ("Family",          f"{row.get('Family', base_info.get('family','?'))} - {row.get('Description', base_info.get('desc','?'))}"),
        ("A53 Core Count",  f"{base_info.get('cores','?')} ({CORE_COUNT.get(base_info.get('cores'),'?')})"),
        ("Evolution Stage", EVOLUTION_STAGE.get(parsed["evolution"], parsed["evolution"])),
        ("Revision",        REVISION.get(parsed["revision"], parsed["revision"])),
        ("Speed Grade",     decode_speed(parsed)),
        ("Features",        decode_features(parsed)),
    ]
    if dl in ("AM62L", "AM62A", "AM62P"):
        rows.append(("Security / Safety", decode_am62l_security_fs(parsed["security_fs"])))
    else:
        rows.append(("Functional Safety", AM62X_FUNCTIONAL_SAFETY.get(parsed["func_safety"], parsed["func_safety"])))
        rows.append(("Security",          "Non-Secure" if parsed["security"] == "G" else f"Secure ({parsed['security']})"))
    rows += [
        ("Temperature",   decode_temp(parsed)),
        ("Package",       f"{parsed['package']} - {PACKAGE.get(parsed['package'], '?')}"),
        ("Tape & Reel",   "Yes" if parsed["tape_reel"] else "No (tray)"),
        ("AEC-Q100 (Q1)", "Yes" if parsed["automotive_q1"] else "No"),
    ]
    col_w = max(len(k) for k, _ in rows) + 2
    print("\n--- PARSED FIELDS ---")
    for k, v in rows:
        print(f"  {k:<{col_w}} {v}")


def print_device_features(base_part, row):
    print(f"\n--- DEVICE FEATURES ({base_part}) ---")
    col_w = max(len(c) for c in FEATURE_COLS) + 2
    for col in FEATURE_COLS:
        val = row.get(col, "").strip()
        if val:
            print(f"  {col:<{col_w}} {val}")


def print_speed_grade(parsed, row):
    sg = parsed["speed_grade"]
    print(f"\n--- SPEED GRADE {sg} ---")

    # Collect rows that have data, skip truly blank ones
    results = []
    seen_labels = set()
    for col75, col85, label in SPEED_COLS:
        if label in seen_labels:
            continue
        v75 = row.get(col75, "").strip()
        if not v75:
            continue
        seen_labels.add(label)
        if col85:
            v85 = row.get(col85, "").strip() or v75
            results.append((label, v75, v85))
        else:
            results.append((label, v75, None))

    if not results:
        print("  (no speed grade data)")
        return

    has_split = any(v85 is not None and v85 != v75 for _, v75, v85 in results)

    if has_split or parsed["device_line"] in ("AM62x", "AM62A", "AM62P"):
        label_w = max(len(lbl) for lbl, _, _ in results)
        col_w   = 14
        print(f"\n  {'SUBSYSTEM':<{label_w}}  {'@ 0.75 V':>{col_w}}  {'@ 0.85 V':>{col_w}}")
        print(f"  {'-' * label_w}  {'-' * col_w}  {'-' * col_w}")
        for lbl, v75, v85 in results:
            v85 = v85 or v75
            # Determine unit from column name
            unit = "MT/s" if "MT/s" in lbl or lbl in ("DDR4", "LPDDR4") else "MHz"
            print(f"  {lbl:<{label_w}}  {v75 + ' ' + unit:>{col_w}}  {v85 + ' ' + unit:>{col_w}}")
    else:
        label_w = max(len(lbl) for lbl, _, _ in results)
        col_w   = 12
        print(f"\n  {'SUBSYSTEM':<{label_w}}  {'MAX FREQ':>{col_w}}")
        print(f"  {'-' * label_w}  {'-' * col_w}")
        for lbl, v75, _ in results:
            unit = "MT/s" if "MT/s" in lbl or lbl in ("DDR4", "LPDDR4") else "MHz"
            print(f"  {lbl:<{label_w}}  {v75 + ' ' + unit:>{col_w}}")


def print_orderable(opn, row):
    print(f"\n--- ORDERABLE INFO ---")
    col_w = max(len(c) for c in ORDERABLE_COLS) + 2
    for col in ORDERABLE_COLS:
        val = row.get(col, "").strip()
        if val:
            print(f"  {col:<{col_w}} {val}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(HELP)
            sys.exit(0)
        raw_opn = sys.argv[1]
    else:
        print("AM62x OPN Parser v2 (master.csv)  |  run with -h for help")
        raw_opn = input("Enter OPN: ").strip()

    parsed, err = parse_opn(raw_opn)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)

    try:
        _, by_opn, by_base = load_master()
    except FileNotFoundError:
        print("ERROR: master.csv not found. Run build_master_csv.py first.")
        sys.exit(1)

    # Look up row: exact OPN first, then by base part
    clean_key = raw_opn.strip().upper().split(".")[0]
    row = by_opn.get(clean_key) or by_base.get(parsed["base"], {})

    print(hr("="))
    print(f"  OPN: {raw_opn}")
    print(hr("="))

    print_parsed_fields(parsed, row)
    print_device_features(parsed["base"], row)
    print_speed_grade(parsed, row)
    if row:
        print_orderable(raw_opn, row)
    else:
        print("\n  (OPN not found in master.csv orderable table)")

    print(f"\n{hr('=')}")


if __name__ == "__main__":
    main()
