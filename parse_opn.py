"""
AM62x / AM62L / AM62A / AM62P OPN parser.

Usage:
    python3 parse_opn.py AM6254ATCGHIALWR
    python3 parse_opn.py AM62L32BOGHAANBR
    python3 parse_opn.py AM62A74AVMHIANFR
    python3 parse_opn.py          (interactive prompt)

AM62x naming convention (SPRSP58C section 9.1.2):
    [a] BBBBBB r Z f Y y t PPP [R][Q1]

AM62L naming convention (SPRSPA1B section 9.1.2):
    [a] BBBBBBB r Z f Y t PPP [R][Q1]
    (7-char base, combined security+FS Y, speed grades E/O, package ANB)

AM62A naming convention (SPRSP77E section 9.1.2):
    [a] BBBBBBB r Z f Y t PPP [R][Q1]
    (7-char base, combined security+FS Y, speed grades M-V, packages AMB/ANF)
"""

import csv
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# AM62x base parts (6-char)
AM62X_BASE_PARTS = {
    "AM6254": {"family": "AM625",    "device_line": "AM62x", "cores": 4, "desc": "Human-machine Interaction SoC"},
    "AM6252": {"family": "AM625",    "device_line": "AM62x", "cores": 2, "desc": "Human-machine Interaction SoC"},
    "AM6251": {"family": "AM625",    "device_line": "AM62x", "cores": 1, "desc": "Human-machine Interaction SoC"},
    "AM6234": {"family": "AM623",    "device_line": "AM62x", "cores": 4, "desc": "IoT and Gateway SoC"},
    "AM6232": {"family": "AM623",    "device_line": "AM62x", "cores": 2, "desc": "IoT and Gateway SoC"},
    "AM6231": {"family": "AM623",    "device_line": "AM62x", "cores": 1, "desc": "IoT and Gateway SoC"},
    "AM6204": {"family": "AM620-Q1", "device_line": "AM62x", "cores": 4, "desc": "Automotive Display SoC"},
    "AM6202": {"family": "AM620-Q1", "device_line": "AM62x", "cores": 2, "desc": "Automotive Display SoC"},
    "AM6201": {"family": "AM620-Q1", "device_line": "AM62x", "cores": 1, "desc": "Automotive Display SoC"},
}

# AM62L base parts (7-char)
AM62L_BASE_PARTS = {
    "AM62L32": {"family": "AM62L", "device_line": "AM62L", "cores": 2, "desc": "Low-power IoT/HMI SoC"},
    "AM62L31": {"family": "AM62L", "device_line": "AM62L", "cores": 1, "desc": "Low-power IoT/HMI SoC"},
}

# AM62A base parts (7-char)
AM62A_BASE_PARTS = {
    "AM62A74": {"family": "AM62A7",    "device_line": "AM62A", "cores": 4, "desc": "Edge AI Vision SoC"},
    "AM62A72": {"family": "AM62A7",    "device_line": "AM62A", "cores": 2, "desc": "Edge AI Vision SoC"},
    "AM62A34": {"family": "AM62A3",    "device_line": "AM62A", "cores": 4, "desc": "Edge AI Vision SoC"},
    "AM62A32": {"family": "AM62A3",    "device_line": "AM62A", "cores": 2, "desc": "Edge AI Vision SoC"},
    "AM62A31": {"family": "AM62A3",    "device_line": "AM62A", "cores": 1, "desc": "Edge AI Vision SoC"},
    "AM62A14": {"family": "AM62A1-Q1", "device_line": "AM62A", "cores": 4, "desc": "Edge AI Vision SoC (Automotive)"},
    "AM62A12": {"family": "AM62A1-Q1", "device_line": "AM62A", "cores": 2, "desc": "Edge AI Vision SoC (Automotive)"},
}

# AM62P base parts (7-char)
AM62P_BASE_PARTS = {
    "AM62P54": {"family": "AM62P5", "device_line": "AM62P", "cores": 4, "desc": "Premium HMI SoC with GPU"},
    "AM62P52": {"family": "AM62P5", "device_line": "AM62P", "cores": 2, "desc": "Premium HMI SoC with GPU"},
    "AM62P34": {"family": "AM62P3", "device_line": "AM62P", "cores": 4, "desc": "Premium HMI SoC without GPU"},
    "AM62P32": {"family": "AM62P3", "device_line": "AM62P", "cores": 2, "desc": "Premium HMI SoC without GPU"},
}

BASE_PARTS = {**AM62X_BASE_PARTS, **AM62L_BASE_PARTS, **AM62A_BASE_PARTS, **AM62P_BASE_PARTS}

EVOLUTION_STAGE = {
    "X": "Experimental (not representative of final specs)",
    "P": "Preproduction (production test flow, no reliability data)",
    "":  "Production",
}

REVISION = {
    "A": "SR1.0",
    "B": "SR1.1",
}

# AM62x speed grades
AM62X_SPEED_GRADE = {
    "G": "G - A53 up to 300 MHz",
    "K": "K - A53 up to 800 MHz",
    "S": "S - A53 up to 1000 MHz",
    "T": "T - A53 up to 1400 MHz",
}

# AM62L speed grades
AM62L_SPEED_GRADE = {
    "E": "E - A53 up to 833 MHz",
    "O": "O - A53 up to 1250 MHz",
}

# AM62P speed grades (note O/S/T/U/V overlap with AM62A letters but different specs)
AM62P_SPEED_GRADE = {
    "O": "O - A53 up to 1000 MHz, GPU 560 MHz,      LPDDR4 3200 MT/s",
    "S": "S - A53 up to 1400 MHz, GPU 560 MHz,      LPDDR4 3200 MT/s",
    "T": "T - A53 up to 1400 MHz, GPU 320 MHz,      LPDDR4 3200 MT/s",
    "U": "U - A53 up to 1400 MHz, GPU up to 800 MHz, LPDDR4 3200 MT/s",
    "V": "V - A53 up to 1400 MHz, GPU up to 800 MHz, LPDDR4 3733 MT/s",
}

# AM62A speed grades
AM62A_SPEED_GRADE = {
    "M": "M - A53 up to 800 MHz,  C7x up to 500 MHz,  LPDDR4 3200 MT/s",
    "N": "N - A53 up to 800 MHz,  C7x up to 1000 MHz, LPDDR4 3200 MT/s",
    "O": "O - A53 up to 1000 MHz, C7x up to 500 MHz,  LPDDR4 3200 MT/s",
    "P": "P - A53 up to 1000 MHz, C7x up to 500 MHz,  LPDDR4 3733 MT/s",
    "Q": "Q - A53 up to 1000 MHz, C7x up to 1000 MHz, LPDDR4 3200 MT/s",
    "R": "R - A53 up to 1000 MHz, C7x up to 1000 MHz, LPDDR4 3733 MT/s",
    "S": "S - A53 up to 1400 MHz, C7x up to 500 MHz,  LPDDR4 3200 MT/s",
    "T": "T - A53 up to 1400 MHz, C7x up to 500 MHz,  LPDDR4 3733 MT/s",
    "U": "U - A53 up to 1400 MHz, C7x up to 1000 MHz, LPDDR4 3200 MT/s",
    "V": "V - A53 up to 1400 MHz, C7x up to 1000 MHz, LPDDR4 3733 MT/s",
}

AM62X_FEATURES = {
    "G": "Base (no additional features)",
    "C": "Base + PRU Subsystem (PRUSS) enabled",
}

AM62L_FEATURES = {
    "G": "Base",
}

AM62A_FEATURES = {
    "G": "Base (no display, no MJPEG)",
    "L": "Base + Motion JPEG Encoder",
    "M": "Base + MJPEG + Display Subsystem",
}

AM62P_FEATURES = {
    "G": "Base (no display, no MJPEG)",
    "M": "Base + MJPEG + Display Subsystem",
}

AM62X_FUNCTIONAL_SAFETY = {
    "G": "Non-Functional Safety",
    "F": "Functional Safety (ISO 26262)",
}

# AM62L combines security + FS into one field
def decode_am62l_security_fs(code):
    if code.isdigit() or (len(code) == 1 and "1" <= code <= "9"):
        return "Secure with Dummy Key / No Functional Safety"
    c = code.upper()
    if "H" <= c <= "R":
        return "Secure with Production Key / No Functional Safety"
    if "S" <= c <= "Z":
        return "Secure with Production Key / Functional Safety (ISO 26262)"
    return f"Unknown ({code})"

AM62X_TEMPERATURE = {
    "A": "-40 to 105 C (Extended Industrial)",
    "H": "0 to 95 C (Commercial)",
    "I": "-40 to 125 C (Automotive)",
}

AM62L_TEMPERATURE = {
    "A": "-40 to 105 C (Extended Industrial)",
    "I": "-40 to 125 C (125 C Industrial)",
}

PACKAGE = {
    "ALW": "FCCSP BGA, 425-pin, 13 mm x 13 mm, 0.5 mm pitch",
    "AMC": "FCBGA, 441-pin, 17.2 mm x 17.2 mm, 0.8 mm pitch",
    "ANB": "FCCSP BGA, 373-pin, 11.8 mm x 12 mm, 0.5 mm pitch",
    "AMB": "FCBGA, 484-pin",
    "ANF": "FCCSP BGA, 484-pin",
    "AMH": "FCBGA, 466-pin",
}

CORE_COUNT = {1: "Single-core", 2: "Dual-core", 4: "Quad-core"}


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------

def load_csv(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_features():
    return load_csv("master_features.csv")


def load_speed_grades():
    return load_csv("master_speed_grades.csv")


def load_orderable():
    return load_csv("master_orderable.csv")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_opn(raw_opn):
    """Parse an AM62x or AM62L OPN string into its component fields."""
    opn = raw_opn.strip()

    if "." in opn:
        opn = opn.split(".")[0]

    # Evolution stage
    if opn and opn[0] in ("X", "P"):
        evolution = opn[0]
        opn = opn[1:]
    else:
        evolution = ""

    # Detect device line: try 7-char AM62L base first, then 6-char AM62x
    base = None
    device_line = None
    for length in (7, 6):
        candidate = opn[:length]
        if candidate in BASE_PARTS:
            base = candidate
            device_line = BASE_PARTS[candidate]["device_line"]
            break

    if base is None:
        all_bases = ", ".join(sorted(BASE_PARTS))
        return None, f"Unknown base part number in '{raw_opn}'. Supported: {all_bases}"

    opn = opn[len(base):]

    # Package designator
    if device_line == "AM62L":
        pkg_options = ("ANB",)
    elif device_line == "AM62A":
        pkg_options = ("AMB", "ANF")
    elif device_line == "AM62P":
        pkg_options = ("AMH",)
    else:
        pkg_options = ("ALW", "AMC")
    package, pkg_pos = None, None
    for pkg in pkg_options:
        pos = opn.find(pkg)
        if pos != -1:
            package, pkg_pos = pkg, pos
            break
    if package is None:
        return None, f"Cannot find package designator in '{raw_opn}'"

    fields_str = opn[:pkg_pos]
    suffix     = opn[pkg_pos + 3:]

    # AM62x: r Z f Y y t = 6 fields
    # AM62L / AM62A / AM62P: r Z f Y t = 5 fields (security+FS merged into Y)
    expected = 5 if device_line in ("AM62L", "AM62A", "AM62P") else 6
    if len(fields_str) != expected:
        return None, (
            f"Expected {expected} field characters before package, "
            f"got {len(fields_str)} ('{fields_str}') in '{raw_opn}'"
        )

    r        = fields_str[0]
    speed    = fields_str[1]
    features = fields_str[2]

    if device_line in ("AM62L", "AM62A", "AM62P"):
        security_fs = fields_str[3]
        func_safety = None
        security    = None
        temperature = fields_str[4]
    else:
        func_safety  = fields_str[3]
        security     = fields_str[4]
        security_fs  = None
        temperature  = fields_str[5]

    return {
        "raw":          raw_opn,
        "device_line":  device_line,
        "evolution":    evolution,
        "base":         base,
        "revision":     r,
        "speed_grade":  speed,
        "features":     features,
        "func_safety":  func_safety,    # AM62x only
        "security":     security,       # AM62x only
        "security_fs":  security_fs,    # AM62L only
        "temperature":  temperature,
        "package":      package,
        "tape_reel":    "R" in suffix,
        "automotive_q1": "Q1" in suffix,
    }, None


# ---------------------------------------------------------------------------
# Feature lookup
# ---------------------------------------------------------------------------

def get_device_features(base_part, feature_rows):
    """Return an ordered dict of feature -> value from master_features.csv."""
    for row in feature_rows:
        if row.get("Base Part", "").strip() == base_part:
            return {k: v for k, v in row.items()
                    if k not in ("Device Line", "Base Part", "Family",
                                 "Description", "Speed Grades Available")
                    and v.strip()}
    return {}


def get_speed_grade_details(grade, speed_rows, device_line):
    """Return the speed grade row from master_speed_grades.csv."""
    for row in speed_rows:
        if row.get("Device Line") == device_line and row.get("Speed Grade") == grade:
            return row
    return {}


def get_orderable_matches(raw_opn, orderable_rows):
    """Find exact match and same-base-OPN variants in master_orderable.csv."""
    clean      = raw_opn.strip().split(".")[0].upper()
    exact      = [r for r in orderable_rows if r["Orderable Part Number"].upper().rstrip(".B") == clean]
    same_base  = [r for r in orderable_rows if r["Orderable Part Number"].upper().startswith(clean)]
    return exact, same_base


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

HELP = """
AM62x OPN Parser
================

USAGE
  python3 parse_opn.py <OPN>         Decode a specific part number
  python3 parse_opn.py               Interactive prompt
  python3 parse_opn.py -h | --help   Show this help

EXAMPLES
  python3 parse_opn.py AM6254ATCGHIALWR
  python3 parse_opn.py XAM6254ATCGHAALW
  python3 parse_opn.py AM6201ASGFHIAMCRQ1

PART NUMBER FORMAT  (SPRSP58C section 9.1.2)
  [a] BBBBBB r Z f Y y t PPP [R] [Q1]

  FIELD  LEN  VALUES & MEANING
  -----  ---  ----------------
  a       0-1  Evolution stage
                 (blank) = Production
                 X       = Experimental
                 P       = Preproduction

  BBBBBB  6    Base part number
                 AM6254 / AM6252 / AM6251  (AM625  - HMI SoC, quad/dual/single A53)
                 AM6234 / AM6232 / AM6231  (AM623  - IoT & Gateway SoC)
                 AM6204 / AM6202 / AM6201  (AM620-Q1 - Automotive Display SoC)

  r       1    Silicon revision
                 A = SR1.0
                 B = SR1.1

  Z       1    Speed grade (max A53 frequency)
                 G = 300 MHz
                 K = 800 MHz
                 S = 1000 MHz
                 T = 1400 MHz

  f       1    Features
                 G = Base only
                 C = Base + PRU Subsystem (PRUSS) enabled

  Y       1    Functional safety
                 G = Non-Functional Safety
                 F = Functional Safety (ISO 26262)

  y       1    Security
                 G = Non-Secure
                 (other) = Secure

  t       1    Temperature range
                 A = -40 to 105 C  (Extended Industrial)
                 H =   0 to  95 C  (Commercial)
                 I = -40 to 125 C  (Automotive)

  PPP     3    Package
                 ALW = FCCSP BGA, 425-pin, 13 x 13 mm, 0.5 mm pitch
                 AMC = FCBGA,     441-pin, 17.2 x 17.2 mm, 0.8 mm pitch

  R       0-1  Tape & reel packaging (omit = JEDEC tray)

  Q1      0-2  AEC-Q100 automotive qualification (omit = standard)

OUTPUT SECTIONS
  PARSED FIELDS    Every field decoded with plain-English descriptions
  DEVICE FEATURES  Full feature table for this device variant
  SPEED GRADE      Max frequencies per subsystem at this speed grade
  ORDERABLE INFO   Status, MSL rating, part marking from the datasheet OPN table
"""


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def hr(char="-", width=60):
    return char * width


def print_parsed(parsed):
    base_info   = BASE_PARTS.get(parsed["base"], {})
    device_line = parsed["device_line"]

    if device_line == "AM62L":
        speed_desc = AM62L_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62L_FEATURES.get(parsed["features"], f"Unknown ({parsed['features']})")
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], f"Unknown ({parsed['temperature']})")
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    elif device_line == "AM62A":
        speed_desc = AM62A_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62A_FEATURES.get(parsed["features"], f"Unknown ({parsed['features']})")
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], f"Unknown ({parsed['temperature']})")
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    elif device_line == "AM62P":
        speed_desc = AM62P_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62P_FEATURES.get(parsed["features"], f"Unknown ({parsed['features']})")
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], f"Unknown ({parsed['temperature']})")
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    else:
        speed_desc = AM62X_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62X_FEATURES.get(parsed["features"], f"Unknown ({parsed['features']})")
        temp_desc  = AM62X_TEMPERATURE.get(parsed["temperature"], f"Unknown ({parsed['temperature']})")

    print(hr("="))
    print(f"  OPN: {parsed['raw']}")
    print(hr("="))
    print("\n--- PARSED FIELDS ---")

    rows = [
        ("Base Part",       parsed["base"]),
        ("Family",          f"{base_info.get('family', '?')} - {base_info.get('desc', '?')}"),
        ("A53 Core Count",  f"{base_info.get('cores', '?')} ({CORE_COUNT.get(base_info.get('cores'), '?')})"),
        ("Evolution Stage", EVOLUTION_STAGE.get(parsed["evolution"], parsed["evolution"])),
        ("Revision",        REVISION.get(parsed["revision"], parsed["revision"])),
        ("Speed Grade",     speed_desc),
        ("Features",        feat_desc),
    ]

    if device_line in ("AM62L", "AM62A", "AM62P"):
        rows.append(("Security / Safety", sec_fs))
    else:
        rows.append(("Functional Safety", AM62X_FUNCTIONAL_SAFETY.get(parsed["func_safety"], f"Unknown ({parsed['func_safety']})")))
        rows.append(("Security",          "Non-Secure" if parsed["security"] == "G" else f"Secure ({parsed['security']})"))

    rows += [
        ("Temperature",  temp_desc),
        ("Package",      f"{parsed['package']} - {PACKAGE.get(parsed['package'], '?')}"),
        ("Tape & Reel",  "Yes" if parsed["tape_reel"] else "No (tray)"),
        ("AEC-Q100 (Q1)","Yes" if parsed["automotive_q1"] else "No"),
    ]

    col_w = max(len(k) for k, _ in rows) + 2
    for key, val in rows:
        print(f"  {key:<{col_w}} {val}")


def print_features(base_part, feature_rows):
    features = get_device_features(base_part, feature_rows)
    if not features:
        print("\n  (No device feature data found)")
        return

    print(f"\n--- DEVICE FEATURES ({base_part}) ---")
    col_w = max(len(k) for k in features) + 2
    for feat, val in features.items():
        print(f"  {feat:<{col_w}} {val}")


# (csv_col, display_label, unit, device_lines_shown)
# device_lines_shown: set of device lines where this row appears, or None for all
SPEED_DISPLAY_COLS = [
    ("A53SS @ 0.75V (MHz)",    "A53SS (Cortex-A53)",    "MHz",   None),
    ("A53SS @ 0.85V (MHz)",    None,                    "MHz",   None),   # 2nd voltage col
    ("GPU (MHz)",              "GPU",                   "MHz",   {"AM62x"}),
    ("PRU (MHz)",              "PRU",                   "MHz",   {"AM62x"}),
    ("Main Infra/CBA (MHz)",   "Main Infra/CBA",        "MHz",   {"AM62x"}),
    ("MCUSS/M4F (MHz)",        "MCUSS/M4F",             "MHz",   {"AM62x"}),
    ("Device/Power Mgr (MHz)", "Device/Power Mgr",      "MHz",   {"AM62x"}),
    ("SMS Subsystem (MHz)",    "SMS Subsystem",         "MHz",   {"AM62x"}),
    ("OCSRAM (MHz)",           "OCSRAM",                "MHz",   {"AM62x"}),
    ("MAIN_SYSCLK0 (MHz)",     "MAIN_SYSCLK0",          "MHz",   {"AM62L"}),
    ("PER_SYSCLK0 (MHz)",      "PER_SYSCLK0",           "MHz",   {"AM62L"}),
    ("WKUP_SYSCLK0 (MHz)",     "WKUP_SYSCLK0",          "MHz",   {"AM62L"}),
    ("C7x @ 0.75V (MHz)",      "C7x AI Accel",          "MHz",   {"AM62A"}),
    ("C7x @ 0.85V (MHz)",      None,                    "MHz",   {"AM62A"}),  # 2nd voltage col for C7x
    ("MAIN_SYSCLK (MHz)",      "MAIN_SYSCLK",           "MHz",   {"AM62A", "AM62P"}),
    ("MCU R5F (MHz)",          "MCU R5F",               "MHz",   {"AM62A", "AM62P"}),
    ("Device Mgr R5F (MHz)",   "Device Mgr R5F",        "MHz",   {"AM62A", "AM62P"}),
    ("HSM (MHz)",              "HSM",                   "MHz",   {"AM62A", "AM62P"}),
    ("VPAC (MHz)",             "VPAC",                  "MHz",   {"AM62A"}),
    ("VENC/VDEC (MHz)",        "VENC/VDEC",             "MHz",   {"AM62A"}),
    ("MJPEG (MHz)",            "MJPEG",                 "MHz",   {"AM62A"}),
    ("GPU @ 0.75V (MHz)",      "GPU",                   "MHz",   {"AM62P"}),
    ("GPU @ 0.85V (MHz)",      None,                    "MHz",   {"AM62P"}),  # 2nd voltage col for GPU
    ("VPU (MHz)",              "VPU",                   "MHz",   {"AM62P"}),
    ("DDR4 (MT/s)",            "DDR4",                  "MT/s",  {"AM62x"}),
    ("LPDDR4 (MT/s)",          "LPDDR4",                "MT/s",  None),
]


# Precompute: primary col -> its "@ 0.85V" partner col (the next entry with lbl=None)
_V85_MAP = {}
for _i, (_c, _lbl, _unit, _lines) in enumerate(SPEED_DISPLAY_COLS):
    if _lbl is not None and _i + 1 < len(SPEED_DISPLAY_COLS):
        _nc, _nlbl, _, _ = SPEED_DISPLAY_COLS[_i + 1]
        if _nlbl is None:
            _V85_MAP[_c] = _nc


def print_speed_grade(grade, speed_rows, device_line="AM62x"):
    row = get_speed_grade_details(grade, speed_rows, device_line)
    if not row:
        print(f"\n  (No speed grade data found for '{grade}')")
        return

    print(f"\n--- SPEED GRADE {grade} ---")

    cols = [(c, lbl, unit) for c, lbl, unit, lines in SPEED_DISPLAY_COLS
            if lbl is not None and (lines is None or device_line in lines)]

    if device_line == "AM62L":
        # Single value column (no VDD_CORE split)
        label_w = max(len(lbl) for _, lbl, _ in cols)
        col_w   = 12
        print(f"\n  {'SUBSYSTEM':<{label_w}}  {'MAX FREQ':>{col_w}}")
        print(f"  {'-' * label_w}  {'-' * col_w}")
        for csv_col, lbl, unit in cols:
            val = row.get(csv_col, "").strip()
            display = f"{val} {unit}" if val else "-"
            print(f"  {lbl:<{label_w}}  {display:>{col_w}}")
    else:
        # Two-column voltage split (AM62x and AM62A)
        label_w = max(len(lbl) for _, lbl, _ in cols)
        col_w   = 14
        print(f"\n  {'SUBSYSTEM':<{label_w}}  {'@ 0.75 V':>{col_w}}  {'@ 0.85 V':>{col_w}}")
        print(f"  {'-' * label_w}  {'-' * col_w}  {'-' * col_w}")
        for csv_col, lbl, unit in cols:
            v75 = row.get(csv_col, "").strip()
            v85_col = _V85_MAP.get(csv_col)
            v85 = (row.get(v85_col, "").strip() if v85_col else "") or v75
            v75_val = f"{v75} {unit}" if v75 else "-"
            v85_val = f"{v85} {unit}" if v85 else "-"
            print(f"  {lbl:<{label_w}}  {v75_val:>{col_w}}  {v85_val:>{col_w}}")


ORDERABLE_SKIP_COLS = {"Device Line", "Base Part"}


def _print_orderable_row(r):
    for k, v in r.items():
        if k not in ORDERABLE_SKIP_COLS and v.strip():
            print(f"  {k:<35} {v}")


def print_orderable(raw_opn, orderable_rows):
    exact, same_base = get_orderable_matches(raw_opn, orderable_rows)

    # Show only the first exact match (the .B sibling is the same part)
    if exact:
        print(f"\n--- ORDERABLE INFO ---")
        _print_orderable_row(exact[0])
        if len(exact) > 1:
            extras = [r["Orderable Part Number"] for r in exact[1:]]
            print(f"\n  Also orderable as: {', '.join(extras)}")
    elif same_base:
        print(f"\n--- ORDERABLE INFO (closest match) ---")
        _print_orderable_row(same_base[0])
        if len(same_base) > 1:
            print(f"\n  ... and {len(same_base) - 1} more variants with the same base OPN")
    else:
        print(f"\n  (OPN not found in orderable table)")


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
        print("AM62x OPN Parser  |  run with -h for help")
        raw_opn = input("Enter OPN: ").strip()

    parsed, err = parse_opn(raw_opn)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)

    dl = parsed["device_line"]

    try:
        feature_rows   = load_features()
        speed_rows     = load_speed_grades()
        orderable_rows = load_orderable()
    except FileNotFoundError as e:
        print(f"ERROR: Missing data file: {e}")
        print("Run build_master_csv.py to generate the master CSV files.")
        sys.exit(1)

    print_parsed(parsed)
    print_features(parsed["base"], feature_rows)
    print_speed_grade(parsed["speed_grade"], speed_rows, device_line=dl)
    print_orderable(raw_opn, orderable_rows)
    print(f"\n{hr('=')}")


if __name__ == "__main__":
    main()
