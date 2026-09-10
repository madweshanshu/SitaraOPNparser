# Sitara OPN Parser

**Confluence**: https://confluence.itg.ti.com/display/LinuxApps/Sitara+OPN+Parser  
**Bitbucket**: https://bitbucket.itg.ti.com/users/a0507831/repos/sitara-opn-parser/browse

Decode any AM62x / AM62L / AM62A / AM62P orderable part number (OPN) and display the device's capabilities, speed grades, and orderable information sourced directly from TI datasheets.

## Supported Devices

| Family | Base Parts | Speed Grades | Package(s) |
|---|---|---|---|
| AM62x (AM625/AM623/AM620-Q1) | AM6254/52/51, AM6234/32/31, AM6204/02/01 | G / K / S / T | ALW, AMC |
| AM62L | AM62L32, AM62L31 | E / O | ANB |
| AM62A | AM62A74/72, AM62A34/32/31, AM62A14/12 | M / N / O / P / Q / R / S / T / U / V | AMB, ANF |
| AM62P | AM62P54/52, AM62P34/32 | O / S / T / U / V | AMH |

## Quick Start

```bash
# Terminal output
python3 parse_opn_terminal.py AM62P54CVMHIAMHR

# Interactive web UI (type OPNs directly in the browser)
python3 parse_opn_web.py
```

### Prerequisites

```bash
pip install pdfplumber   # only needed to re-extract data from PDFs
```

The three parser scripts (`parse_opn.py`, `parse_opn_html.py`, `parse_opn_web.py`) have **no external dependencies** beyond the standard library — they read only from the `master_*.csv` files included in the repo.

## Usage

### Terminal (`parse_opn_terminal.py`)

```
python3 parse_opn_terminal.py <OPN>    decode a specific part number
python3 parse_opn_terminal.py          interactive prompt
python3 parse_opn_terminal.py -h       show help and field format reference
```

Output sections:
- **Parsed Fields** — every field decoded with plain-English descriptions
- **Device Features** — full feature table for this device variant
- **Speed Grade** — max frequencies per subsystem, split by VDD_CORE voltage
- **Orderable Info** — status, MSL rating, part marking from the datasheet

### Interactive Web UI (`parse_opn_web.py`)

```
python3 parse_opn_web.py          starts on http://localhost:8080
python3 parse_opn_web.py 5000     custom port
```

Opens the browser automatically. Type any OPN into the search field and press Enter. Clickable example OPNs are shown on the welcome page.

## OPN Format Reference

### AM62x (SPRSP58C section 9.1.2)

```
[a] BBBBBB r Z f Y y t PPP [R][Q1]
```

| Field | Meaning | Values |
|---|---|---|
| a | Evolution stage | (blank)=Production, X=Experimental, P=Preproduction |
| BBBBBB | Base part (6 chars) | AM6254, AM6252, AM6251, AM6234, AM6232, AM6231, AM6204, AM6202, AM6201 |
| r | Silicon revision | A=SR1.0, B=SR1.1 |
| Z | Speed grade | G=300MHz, K=800MHz, S=1000MHz, T=1400MHz |
| f | Features | G=Base, C=Base+PRUSS |
| Y | Functional safety | G=Non-FS, F=Functional Safety |
| y | Security | G=Non-Secure, other=Secure |
| t | Temperature | A=-40 to 105C, H=0 to 95C, I=-40 to 125C |
| PPP | Package | ALW=FCCSP 425-pin, AMC=FCBGA 441-pin |
| R | Tape & reel | (present=reel, omit=tray) |
| Q1 | AEC-Q100 | (present=automotive qualified) |

### AM62L (SPRSPA1B section 9.1.2)

```
[a] BBBBBBB r Z f Y t PPP [R][Q1]
```

Same structure as AM62x but: 7-char base part, security+FS combined into one Y field, speed grades E/O, package ANB only.

| Y value | Meaning |
|---|---|
| 1–9 | Secure with Dummy Key / No Functional Safety |
| H–R | Secure with Production Key / No Functional Safety |
| S–Z | Secure with Production Key / Functional Safety |

### AM62A (SPRSP77E section 9.1.2)

```
[a] BBBBBBB r Z f Y t PPP [R][Q1]
```

Same 5-field structure as AM62L. Speed grades M–V (10 grades). Features: G=Base, L=+MJPEG, M=+MJPEG+Display. Packages: AMB (FCBGA 484), ANF (FCCSP 484).

### AM62P (SPRSP89E section 9.1.2)

```
[a] BBBBBBB r Z f Y t PPP [Q1]
```

Same 5-field structure. Revisions A/B/C. Speed grades O/S/T/U/V. Features: G=Base, M=+MJPEG+Display. Temperature I only. Package: AMH (FCBGA 466). Q1 also changes eMMC speed (HS400 vs HS200).

## File Structure

```
sitara-opn-parser/
├── README.md
├── LOG.md
│
├── parse_opn_engine.py       Core naming convention logic (shared, not run directly)
├── parse_opn_terminal.py     Terminal UI — reads master.csv
├── parse_opn_web.py          Interactive web UI — reads master.csv
│
└── data/
    ├── master.csv                Single denormalized file (127 OPNs x 77 cols)
    ├── master_orderable.csv      All OPNs across all device lines (127 rows)
    ├── master_features.csv       One row per device variant (22 rows)
    ├── master_speed_grades.csv   Speed grades for all families (21 rows)
    ├── build_master_csv.py       Rebuilds master CSVs from data/raw/ (run when adding a device)
    └── raw/                      Only needed when adding a new device or re-extracting
        ├── extract_tables.py     Extracts tables from PDFs into this folder
        ├── am62*.pdf             Datasheet PDFs
        └── am62*_*.csv           Raw tables extracted from PDFs
│
└── archive/                  Earlier multi-CSV scripts (superseded by master.csv)
    ├── parse_opn_html.py
    └── parse_opn_web.py
```

## Data Architecture

```
data/raw/*.pdf  ->  data/raw/extract_tables.py  ->  data/raw/*.csv
                                                            |
                                                  data/build_master_csv.py
                                                            |
                                                     data/master.csv
                                                     data/master_*.csv
                                                            |
                                                 parse_opn_terminal.py
                                                 parse_opn_web.py
```

The `data/` CSVs are the single source of truth. PDFs and raw CSVs in `data/raw/` are only needed when adding a new device.

## Adding a New Device Family

1. Download the datasheet PDF into `data/raw/`.
2. Add page ranges and an `extract_<family>()` function to `data/raw/extract_tables.py`.
3. Run `python3 data/raw/extract_tables.py` to produce raw CSVs in `data/raw/`.
4. Add device meta, feature mapping, and speed grade processing to `data/build_master_csv.py`.
5. Run `python3 data/build_master_csv.py` to regenerate the master CSVs.
6. Add base parts, speed grades, features, and package codes to `parse_opn_engine.py`.
7. Add speed grade display columns to `SPEED_DISPLAY_COLS` in `parse_opn_engine.py`.

## Datasheet References

| Device | Document | Naming Convention Section |
|---|---|---|
| AM62x | SPRSP58C | Section 9.1.2 |
| AM62L | SPRSPA1B | Section 9.1.2 |
| AM62A | SPRSP77E | Section 9.1.2 |
| AM62P | SPRSP89E | Section 9.1.2 |
