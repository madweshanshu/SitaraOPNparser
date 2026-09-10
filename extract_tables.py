"""
Extract tables from AM62x and AM62L datasheet PDFs.

AM62x (am625_datasheet.pdf / SPRSP58C):
  orderable_info.csv, device_comparison.csv, speed_grades.csv

AM62L (am62l_datasheet.pdf / SPRSPA1B):
  am62l_orderable_info.csv, am62l_device_comparison.csv, am62l_speed_grades.csv
"""

import csv
import re
import pdfplumber

# ---- AM62x config ----
AM62X_PDF          = "am625_datasheet.pdf"
AM62X_ORD_PAGES    = range(256, 264)
AM62X_COMP_PAGES   = [7, 8]
AM62X_SPEED_PAGE   = 93

# ---- AM62L config ----
AM62L_PDF          = "am62l_datasheet.pdf"
AM62L_ORD_PAGES    = [220]
AM62L_COMP_PAGES   = [6, 7]
AM62L_SPEED_PAGE   = 70

# ---- AM62A config ----
AM62A_PDF          = "am62a_datasheet.pdf"
AM62A_ORD_PAGES    = range(238, 241)
AM62A_COMP_PAGES   = [7, 8]
AM62A_SPEED_PAGE   = 84

# ---- AM62P config ----
AM62P_PDF          = "am62p_datasheet.pdf"
AM62P_ORD_PAGES    = [233]
AM62P_COMP_PAGES   = [7, 8]
AM62P_SPEED_PAGE   = 84


def clean(val):
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val)).strip()


# ---------------------------------------------------------------------------
# Shared extractors
# ---------------------------------------------------------------------------

def extract_orderable(pdf, page_range, opn_prefix="AM"):
    header = [
        "Orderable Part Number", "Status", "Material Type",
        "Package | Pins", "Package Qty | Carrier", "RoHS",
        "Lead Finish / Ball Material", "MSL Rating / Peak Reflow",
        "Op Temp (C)", "Part Marking",
    ]
    rows = []
    for pg_num in page_range:
        page = pdf.pages[pg_num - 1]
        for table in page.extract_tables():
            if not table or len(table[0]) < 9:
                continue
            for row in table:
                cleaned = [clean(c) for c in row]
                if not cleaned[0] or cleaned[0].lower().startswith("orderable"):
                    continue
                if not re.match(rf"^{opn_prefix}", cleaned[0]):
                    continue
                rows.append(cleaned[:10])
    return header, rows


def extract_device_comparison(pdf, page_list, min_cols=4):
    all_rows = []
    for pg_num in page_list:
        page = pdf.pages[pg_num - 1]
        for table in page.extract_tables():
            if not table or len(table[0]) < min_cols:
                continue
            all_rows.extend([[clean(c) for c in row] for row in table])

    if not all_rows:
        return [], []

    r0 = all_rows[0]
    r1 = all_rows[1] if len(all_rows) > 1 else [""] * len(r0)
    header = []
    for a, b in zip(r0, r1):
        combined = " ".join(x for x in [a, b] if x).strip()
        header.append(combined if combined else "(blank)")

    skip_vals = {"FEATURES", "REFERENCE", "REFERENCE NAME", "NAME", ""}
    seen = set()
    data_rows = []
    for row in all_rows[2:]:
        cleaned = [clean(c) for c in row]
        if cleaned[0] in skip_vals and cleaned[1] in skip_vals:
            continue
        key = tuple(cleaned)
        if key in seen:
            continue
        seen.add(key)
        data_rows.append(cleaned)

    return header, data_rows


def extract_speed_grades(pdf, page_num):
    page = pdf.pages[page_num - 1]
    tables = page.extract_tables()
    raw = tables[0] if tables else []
    if not raw:
        return [], []

    r0 = [clean(c) for c in raw[0]]
    r1 = [clean(c) for c in raw[1]]
    header = []
    for a, b in zip(r0, r1):
        combined = " ".join(x for x in [a, b] if x).strip()
        header.append(combined if combined else "(blank)")

    data_rows = [[clean(c) for c in row] for row in raw[2:]]
    return header, data_rows


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {path}")


# ---------------------------------------------------------------------------
# Per-device main
# ---------------------------------------------------------------------------

def extract_am62x():
    with pdfplumber.open(AM62X_PDF) as pdf:
        print(f"\n[AM62x] {len(pdf.pages)} pages")
        h, r = extract_orderable(pdf, AM62X_ORD_PAGES)
        write_csv("orderable_info.csv", h, r)
        h, r = extract_device_comparison(pdf, AM62X_COMP_PAGES, min_cols=10)
        write_csv("device_comparison.csv", h, r)
        h, r = extract_speed_grades(pdf, AM62X_SPEED_PAGE)
        write_csv("speed_grades.csv", h, r)


def extract_am62l():
    with pdfplumber.open(AM62L_PDF) as pdf:
        print(f"\n[AM62L] {len(pdf.pages)} pages")
        h, r = extract_orderable(pdf, AM62L_ORD_PAGES, opn_prefix="AM62L")
        write_csv("am62l_orderable_info.csv", h, r)
        h, r = extract_device_comparison(pdf, AM62L_COMP_PAGES, min_cols=4)
        write_csv("am62l_device_comparison.csv", h, r)
        h, r = extract_speed_grades(pdf, AM62L_SPEED_PAGE)
        write_csv("am62l_speed_grades.csv", h, r)


def extract_am62a():
    with pdfplumber.open(AM62A_PDF) as pdf:
        print(f"\n[AM62A] {len(pdf.pages)} pages")
        h, r = extract_orderable(pdf, AM62A_ORD_PAGES, opn_prefix="AM62A")
        write_csv("am62a_orderable_info.csv", h, r)
        h, r = extract_device_comparison(pdf, AM62A_COMP_PAGES, min_cols=9)
        write_csv("am62a_device_comparison.csv", h, r)
        h, r = extract_speed_grades(pdf, AM62A_SPEED_PAGE)
        write_csv("am62a_speed_grades.csv", h, r)


def extract_am62p():
    with pdfplumber.open(AM62P_PDF) as pdf:
        print(f"\n[AM62P] {len(pdf.pages)} pages")
        h, r = extract_orderable(pdf, AM62P_ORD_PAGES, opn_prefix="AM62P")
        write_csv("am62p_orderable_info.csv", h, r)
        h, r = extract_device_comparison(pdf, AM62P_COMP_PAGES, min_cols=6)
        write_csv("am62p_device_comparison.csv", h, r)
        h, r = extract_speed_grades(pdf, AM62P_SPEED_PAGE)
        write_csv("am62p_speed_grades.csv", h, r)


def main():
    extract_am62x()
    extract_am62l()
    extract_am62a()
    extract_am62p()


if __name__ == "__main__":
    main()
