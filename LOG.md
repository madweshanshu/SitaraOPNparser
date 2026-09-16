# OPN Parser - Project Log

## Project Links

- **Live App**: https://madweshanshu.github.io/SitaraOPNparser/
- **GitHub**: https://github.com/madweshanshu/SitaraOPNparser
- **Bitbucket**: https://bitbucket.itg.ti.com/users/a0507831/repos/sitara-opn-parser/browse
- **Confluence**: https://confluence.itg.ti.com/display/LinuxApps/Sitara+OPN+Parser

## 2026-09-10

- Log file created. Ready to document progress.
- **Goal defined:** User inputs an OPN (Orderable Part Number); tool outputs all capabilities and features of that device as described in its datasheet.

### Open questions / decisions needed

1. **Datasheet source** - Where do we fetch datasheets from? Options:
   - TI product pages (ti.com) - requires resolving OPN -> product page -> PDF link
   - Local cached PDFs
   - PDS system (internal TI database - already have MCP tools for this)

2. **Output format** - Plain text summary, structured JSON, markdown?

3. **LLM extraction** - Use an LLM to parse the PDF and extract features, or regex/structured parsing?

---

## 2026-09-10 - AM625 datasheet table extraction

- Downloaded `am625_datasheet.pdf` (SPRSP58C) from `ti.com/lit/ds/sprsp58/sprsp58.pdf` - 276 pages
- TI document viewer uses client-side JS fragments; direct PDF fetch was required
- Installed `pdfplumber` for PDF table extraction
- Wrote `extract_tables.py`

### Output CSVs

| File | Rows | Description |
|---|---|---|
| `orderable_info.csv` | 88 | Full OPN table (pages 256-263): Status, Package, Op Temp, MSL, etc. |
| `device_comparison.csv` | 35 | Table 4-1: Feature comparison across AM6201/02/04/31/32/34/51/52/54 |
| `speed_grades.csv` | 5 | Table 6-1: Speed grades G/K/S/T with max frequencies per subsystem |

### Notes
- Speed grade T has two rows in the source: 1250MHz @ 0.75/0.85V and 1400MHz @ 0.85V only (preserved as-is)
- Orderable pages span 256-263; each page is a separate table instance in pdfplumber

---

## 2026-09-10 - OPN parser script

- Wrote `parse_opn.py` - accepts an AM62x OPN (CLI arg or interactive prompt)
- Naming convention implemented per SPRSP58C section 9.1.2 (page 247)
- Format: `[a] BBBBBB r Z f Y y t PPP [R][Q1]`
- Handles .B packaging revision suffix (stripped before parsing)
- Feature lookup uses fallback chain to handle PDF merged cells:
  device column -> family lead column (e.g. AM6234 for AM623x) -> AM6254 (cross-family merges)

### Output sections
1. Parsed fields with human-readable descriptions
2. Device features from device_comparison.csv
3. Speed grade frequencies from speed_grades.csv
4. Orderable info lookup (exact match, then closest match)

---

## 2026-09-10 - Help menu

- Added `-h` / `--help` flag to `parse_opn.py`
- Help output covers: usage, examples, full field-by-field format breakdown, output section descriptions
- Interactive prompt now shows "run with -h for help" hint
- Confirmed `XAM6254ATCGHAALW` (Experimental prefix) parses correctly; not found in orderable table as expected

---

## 2026-09-10 - Speed grade display fix

- Removed redundant "Speed Grades (See Device Speed Grades)" row from DEVICE FEATURES section (already shown in PARSED FIELDS)
- Replaced flat speed grade output with a two-column table split by VDD_CORE voltage (0.75V vs 0.85V)
- Grade T correctly shows 1250 MHz @ 0.75V and 1400 MHz @ 0.85V for A53; all other subsystems identical at both voltages
- All other grades (G/K/S) show matching values in both voltage columns

---

---

## 2026-09-10 - AM62L device added

- Downloaded `am62l_datasheet.pdf` (SPRSPA1B) from `ti.com/lit/ds/symlink/am62l.pdf` - 225 pages
- Refactored `extract_tables.py` to support multiple device PDFs with shared extractor functions
- Added AM62L-specific CSVs: `am62l_orderable_info.csv` (5 rows), `am62l_device_comparison.csv` (32 rows), `am62l_speed_grades.csv` (2 rows)
- Extended `parse_opn.py` to detect and handle both AM62x and AM62L OPNs

### AM62L naming convention differences vs AM62x (SPRSPA1B section 9.1.2)

| Field | AM62x | AM62L |
|---|---|---|
| Base part length | 6 chars (AM6254) | 7 chars (AM62L32) |
| Speed grades | G/K/S/T | E (833 MHz) / O (1250 MHz) |
| Security field | Separate `y` field (G=Non-Secure, other=Secure) | Combined `Y` field: 1-9=Dummy Key/No FS, H-R=Prod Key/No FS, S-Z=Prod Key/FS |
| Functional Safety field | Separate `Y` field (G/F) | Merged into `Y` above |
| Temperature | A/H/I | A/I only (no commercial H) |
| Package | ALW or AMC | ANB only (373-pin, 11.8x12mm) |

### Speed grade display
- AM62L has no VDD_CORE column -> single-column flat table (no voltage split)
- AM62L subsystem columns: A53SS, MAIN_SYSCLK0, PER_SYSCLK0, WKUP_SYSCLK0, DDR4, LPDDR4

### Bug fixed
- Duplicate header rows from multi-page tables leaked into device comparison CSV for AM62L
- Fixed: added "REFERENCE NAME" to `skip_vals` in `extract_device_comparison()`

---

---

## 2026-09-10 - Master CSV consolidation

Replaced 6 device-specific raw CSVs with 3 clean master files. `parse_opn.py` now reads only from these; no PDFs or extraction scripts needed at runtime.

### New script: `build_master_csv.py`
Reads the 6 raw extracted CSVs and outputs the 3 master files. Run once after `extract_tables.py`, or after adding a new device.

### Master CSV schemas

**`master_orderable.csv`** (93 rows)
- Added `Device Line` and `Base Part` columns to the merged orderable table
- Single file covers all device families

**`master_speed_grades.csv`** (6 rows)
- Unified column names across AM62x and AM62L
- AM62x-only columns blank for AM62L rows, and vice versa
- Grade T stores both 0.75V (1250 MHz) and 0.85V (1400 MHz) A53 values in separate columns

**`master_features.csv`** (11 rows - one per device variant)
- Standardised feature column names; empty cell = feature not present
- Columns: Device Line, Base Part, Family, Description, A53 Cores, Speed Grades Available, GPU, PRUSS, Cortex-M4F, Security Controller, Crypto Accelerators, CSI-RX, ADC, Display, CAN, I2C, UART, SPI, McASP, eMMC, SD/SDIO, USB 2.0, Ethernet (CPSW3G), GPIO, ePWM, eCAP, eQEP, Timers, GTC, OCSRAM Main, OCSRAM MCU, DDR Support, GPMC, OSPI/QSPI, RTC

### Adding a new device family
1. Add PDF path and page ranges to `extract_tables.py`
2. Run `python3 extract_tables.py` to get raw CSVs
3. Add device config to `build_master_csv.py` (meta dict + feature mapping)
4. Run `python3 build_master_csv.py` to regenerate master CSVs
5. Add base parts and naming convention fields to `parse_opn.py`

---

---

## 2026-09-10 - AM62A device added

- Downloaded `am62a_datasheet.pdf` (SPRSP77E) from `ti.com/lit/ds/symlink/am62a7.pdf` - 250 pages
- Extended `extract_tables.py`, `build_master_csv.py`, and `parse_opn.py` for AM62A

### AM62A naming convention (SPRSP77E section 9.1.2)

Format: `[a] BBBBBBB r Z f Y t PPP [R][Q1]`  (same 5-field structure as AM62L)

| Field | AM62A values |
|---|---|
| Base part | AM62A74, AM62A72, AM62A34, AM62A32, AM62A31, AM62A14, AM62A12 (7 chars) |
| Speed grades | M / N / O / P / Q / R / S / T / U / V (10 grades) |
| Features | G (base), L (+ MJPEG encoder), M (+ Display Subsystem) |
| Security/FS | Same combined Y field as AM62L (1-9 / H-R / S-Z) |
| Temperature | A (-40 to 105) / I (-40 to 125) |
| Package | AMB (FCBGA 484-pin) / ANF (FCCSP 484-pin) |

### AM62A vs AM62x/AM62L speed grade differences
- 10 grades M-V vs 4 (AM62x) or 2 (AM62L)
- Many grades have 0.75V/0.85V VDD_CORE split (not just grade T)
- Unique subsystems: C7x AI accelerator, VPAC (vision), VENC/VDEC (video), MJPEG
- LPDDR4 only (no DDR4 column) with rates up to 3733 MT/s
- New columns added to master_speed_grades.csv: C7x @ 0.75V, C7x @ 0.85V, VPAC, VENC/VDEC, MJPEG, HSM, LPDDR4 @ 0.75V, LPDDR4 @ 0.85V

---

## 2026-09-10 - AM62P device added

- Downloaded `am62p_datasheet.pdf` (SPRSP89E) from `ti.com/lit/ds/symlink/am62p.pdf` - 238 pages

### AM62P naming convention (SPRSP89E section 9.1.2)

Format: `[a] BBBBBBB r Z f Y t PPP [Q1]` (same 5-field structure as AM62L/AM62A)

| Field | AM62P values |
|---|---|
| Base part | AM62P54, AM62P52, AM62P34, AM62P32 (7 chars) |
| Revision | A (SR1.0), B (SR1.1), C (SR1.2) - 3 revisions unlike other families |
| Speed grades | O / S / T / U / V (5 grades, letters overlap with AM62A but different specs) |
| Features | G (base), M (+ MJPEG + Display) — no L code unlike AM62A |
| Security/FS | Same combined Y field (1-9 / H-R / S-Z) |
| Temperature | I only (-40 to 125°C) — single temperature grade |
| Package | AMH (FCBGA 466-pin) — single package |
| Q1 | Also changes eMMC speed: Q1=HS400, blank=HS200 |

### AM62P speed grade differences
- GPU and VPU are unique subsystems vs other AM62 families
- GPU has voltage-dependent frequency on grades U/V (720 MHz @ 0.75V, 800 MHz @ 0.85V)
- AM62P5x (AM62P54/52) has GPU; AM62P3x (AM62P34/32) does not
- New columns added to master_speed_grades.csv: GPU @ 0.75V, GPU @ 0.85V, VPU

---

## 2026-09-10 - Interactive web UI

- Created `parse_opn_web.py` - starts a local HTTP server and opens the browser
- User types OPN directly into an input field; page updates with results (full GET request, no JS framework needed)
- Uses Python's built-in `http.server` - zero extra dependencies
- Imports all rendering logic from `parse_opn_html.py` - no duplication
- Welcome page shows clickable example OPNs for all four device lines
- Error messages displayed inline (red bordered box) when OPN is unrecognized
- Usage: `python3 parse_opn_web.py` (default port 8080) or `python3 parse_opn_web.py 5000`

---

## 2026-09-10 - HTML output version

- Created `parse_opn_html.py` - same functionality as `parse_opn.py` but outputs a styled HTML page
- Imports all parsing/lookup logic from `parse_opn.py` (no duplication)
- Writes `output.html` to the project directory and opens it in the default browser
- Styled with TI red (#c41230) branding, clean table layout, Yes/No badges
- Speed grade table highlights cells where 0.75V and 0.85V values differ
- Usage: `python3 parse_opn_html.py <OPN>` or interactive prompt

---

## Current file inventory

| File | Purpose |
|---|---|
| `am625_datasheet.pdf` | SPRSP58C source PDF (downloaded from ti.com) |
| `extract_tables.py` | Extracts 3 tables from the PDF into CSVs |
| `orderable_info.csv` | OPN orderable table (88 rows) |
| `device_comparison.csv` | Device feature comparison table (35 rows) |
| `speed_grades.csv` | Speed grade frequency table (5 rows) |
| `parse_opn.py` | Terminal output: `python3 parse_opn.py <OPN>` |
| `parse_opn_html.py` | Static HTML: generates `output.html` and opens in browser |
| `parse_opn_web.py` | Interactive web UI (three-CSV backend) |
| `parse_opn_v2.py` | Terminal output backed by single `master.csv` |
| `parse_opn_v2_web.py` | Interactive web UI backed by single `master.csv` |
| `build_master_csv.py` | One-time consolidation script: raw CSVs -> master CSVs |
| `master_orderable.csv` | **[source of truth]** All OPNs (127 rows) |
| `master_features.csv` | **[source of truth]** One row per device variant (22 rows) |
| `master_speed_grades.csv` | **[source of truth]** Speed grades for all families (21 rows) |
| `am62l_datasheet.pdf` | SPRSPA1B source PDF (bootstrap only) |
| `am62l_orderable_info.csv` | AM62L raw extracted (bootstrap only) |
| `am62l_device_comparison.csv` | AM62L raw extracted (bootstrap only) |
| `am62l_speed_grades.csv` | AM62L raw extracted (bootstrap only) |
| `am62a_datasheet.pdf` | SPRSP77E source PDF (bootstrap only) |
| `am62a_orderable_info.csv` | AM62A raw extracted (bootstrap only) |
| `am62a_device_comparison.csv` | AM62A raw extracted (bootstrap only) |
| `am62a_speed_grades.csv` | AM62A raw extracted (bootstrap only) |
| `am62p_datasheet.pdf` | SPRSP89E source PDF (bootstrap only) |
| `am62p_orderable_info.csv` | AM62P raw extracted (bootstrap only) |
| `am62p_device_comparison.csv` | AM62P raw extracted (bootstrap only) |
| `am62p_speed_grades.csv` | AM62P raw extracted (bootstrap only) |

## Architecture decisions made

- **Datasheet source**: Direct PDF download from ti.com/lit/ds (TI document viewer is JS-rendered, unusable via HTTP fetch)
- **Parsing approach**: Regex/structured parsing of naming convention + CSV lookups (no LLM needed for AM62x - the naming convention is fully documented)
- **Output format**: Plain-text terminal output (sections: parsed fields, device features, speed grade, orderable info)
- **Merged cell handling**: Fallback chain in feature lookup (device col -> family lead -> AM6254) rather than forward-filling the CSV

## Known limitations / next steps

- Currently supports AM62x only (AM625, AM623, AM620-Q1 families)
- Adding more devices will require: new datasheet PDF, new extract run, updated BASE_PARTS/naming convention tables in parse_opn.py
