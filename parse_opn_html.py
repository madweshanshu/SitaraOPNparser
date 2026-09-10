"""
AM62x / AM62L / AM62A / AM62P OPN parser - HTML output.

Usage:
    python3 parse_opn_html.py AM62P54CVMHIAMHR
    python3 parse_opn_html.py                   (interactive prompt)
    python3 parse_opn_html.py -h | --help

Generates output.html in the same directory and opens it in the default browser.
"""

import sys
import os
import webbrowser
import html as html_escape_mod

# Reuse all parsing/lookup logic from parse_opn.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_opn import (
    parse_opn, HELP,
    BASE_PARTS, CORE_COUNT, EVOLUTION_STAGE, REVISION, PACKAGE,
    AM62X_SPEED_GRADE, AM62L_SPEED_GRADE, AM62A_SPEED_GRADE, AM62P_SPEED_GRADE,
    AM62X_FEATURES, AM62L_FEATURES, AM62A_FEATURES, AM62P_FEATURES,
    AM62X_FUNCTIONAL_SAFETY, AM62X_TEMPERATURE, AM62L_TEMPERATURE,
    decode_am62l_security_fs,
    load_features, load_speed_grades, load_orderable,
    get_device_features, get_speed_grade_details, get_orderable_matches,
    SPEED_DISPLAY_COLS, _V85_MAP,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "output.html")


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def e(s):
    return html_escape_mod.escape(str(s))


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f0f2f5;
    color: #1a1a1a;
    padding: 24px;
    font-size: 14px;
}
.container { max-width: 960px; margin: 0 auto; }
header {
    background: #c41230;
    color: white;
    padding: 18px 24px;
    border-radius: 8px 8px 0 0;
    display: flex;
    align-items: center;
    gap: 16px;
}
header h1 { font-size: 20px; font-weight: 600; }
header .opn { font-size: 14px; opacity: 0.85; font-family: monospace; }
.body { background: white; border-radius: 0 0 8px 8px; padding: 24px; }
.section { margin-bottom: 28px; }
.section h2 {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #c41230;
    border-bottom: 2px solid #c41230;
    padding-bottom: 6px;
    margin-bottom: 14px;
}
table { width: 100%; border-collapse: collapse; }
td, th {
    padding: 7px 12px;
    text-align: left;
    border-bottom: 1px solid #e8e8e8;
    vertical-align: top;
}
tr:last-child td { border-bottom: none; }
td:first-child { color: #555; width: 220px; font-weight: 500; white-space: nowrap; }
tr:nth-child(even) { background: #fafafa; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
}
.badge-yes  { background: #e6f4ea; color: #1e7e34; }
.badge-no   { background: #fce8e8; color: #c41230; }
.badge-info { background: #e8f0fe; color: #1a56db; }
.tag {
    display: inline-block;
    background: #1a56db;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 4px;
}
.speed-table th {
    background: #f5f5f5;
    font-weight: 600;
    font-size: 12px;
    color: #444;
    text-align: right;
}
.speed-table th:first-child { text-align: left; }
.speed-table td { text-align: right; font-family: monospace; font-size: 13px; }
.speed-table td:first-child { text-align: left; font-family: inherit; font-size: 14px; color: #555; font-weight: 500; }
.speed-table td.highlight { color: #c41230; font-weight: 600; }
footer { text-align: center; color: #888; font-size: 12px; margin-top: 20px; }
"""


def badge(val):
    v = str(val).strip().lower()
    if v in ("yes", "true"):
        return f'<span class="badge badge-yes">Yes</span>'
    if v in ("no", "false", ""):
        return f'<span class="badge badge-no">No</span>'
    return e(val)


def render_parsed(parsed):
    base_info   = BASE_PARTS.get(parsed["base"], {})
    device_line = parsed["device_line"]

    if device_line == "AM62L":
        speed_desc = AM62L_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62L_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    elif device_line == "AM62A":
        speed_desc = AM62A_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62A_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    elif device_line == "AM62P":
        speed_desc = AM62P_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62P_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    else:
        speed_desc = AM62X_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62X_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62X_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])

    rows = [
        ("Base Part",       f'<span class="tag">{e(parsed["base"])}</span>'),
        ("Family",          e(f"{base_info.get('family','?')} - {base_info.get('desc','?')}")),
        ("A53 Core Count",  e(f"{base_info.get('cores','?')} ({CORE_COUNT.get(base_info.get('cores'),'?')})")),
        ("Evolution Stage", e(EVOLUTION_STAGE.get(parsed["evolution"], parsed["evolution"]))),
        ("Revision",        e(REVISION.get(parsed["revision"], parsed["revision"]))),
        ("Speed Grade",     e(speed_desc)),
        ("Features",        e(feat_desc)),
    ]
    if device_line in ("AM62L", "AM62A", "AM62P"):
        rows.append(("Security / Safety", e(sec_fs)))
    else:
        rows.append(("Functional Safety", e(AM62X_FUNCTIONAL_SAFETY.get(parsed["func_safety"], parsed["func_safety"]))))
        rows.append(("Security",          e("Non-Secure" if parsed["security"] == "G" else f"Secure ({parsed['security']})")))
    rows += [
        ("Temperature",  e(temp_desc)),
        ("Package",      e(f"{parsed['package']} - {PACKAGE.get(parsed['package'],'?')}")),
        ("Tape & Reel",  badge("Yes" if parsed["tape_reel"] else "No")),
        ("AEC-Q100 (Q1)",badge("Yes" if parsed["automotive_q1"] else "No")),
    ]

    trs = "\n".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return f'<div class="section"><h2>Parsed Fields</h2><table>{trs}</table></div>'


def render_features(base_part, feature_rows):
    features = get_device_features(base_part, feature_rows)
    if not features:
        return '<div class="section"><h2>Device Features</h2><p>No data.</p></div>'

    trs = []
    for feat, val in features.items():
        cell = badge(val) if val.lower() in ("yes","no") else e(val)
        trs.append(f"<tr><td>{e(feat)}</td><td>{cell}</td></tr>")

    return (f'<div class="section"><h2>Device Features ({e(base_part)})</h2>'
            f'<table>{"".join(trs)}</table></div>')


def render_speed_grade(grade, speed_rows, device_line):
    row = get_speed_grade_details(grade, speed_rows, device_line)
    if not row:
        return f'<div class="section"><h2>Speed Grade {e(grade)}</h2><p>No data.</p></div>'

    cols = [(c, lbl, unit) for c, lbl, unit, lines in SPEED_DISPLAY_COLS
            if lbl is not None and (lines is None or device_line in lines)]

    if device_line == "AM62L":
        ths = "<tr><th>Subsystem</th><th>Max Freq</th></tr>"
        trs = []
        for csv_col, lbl, unit in cols:
            val = row.get(csv_col, "").strip()
            display = f"{val} {unit}" if val else "-"
            trs.append(f"<tr><td>{e(lbl)}</td><td>{e(display)}</td></tr>")
    else:
        ths = "<tr><th>Subsystem</th><th>@ 0.75 V</th><th>@ 0.85 V</th></tr>"
        trs = []
        for csv_col, lbl, unit in cols:
            v75 = row.get(csv_col, "").strip()
            v85_col = _V85_MAP.get(csv_col)
            v85 = (row.get(v85_col, "").strip() if v85_col else "") or v75
            v75_fmt = f"{v75} {unit}" if v75 else "-"
            v85_fmt = f"{v85} {unit}" if v85 else "-"
            hi75 = ' class="highlight"' if v75 != v85 else ""
            hi85 = ' class="highlight"' if v75 != v85 else ""
            trs.append(
                f"<tr><td>{e(lbl)}</td>"
                f'<td{hi75}>{e(v75_fmt)}</td>'
                f'<td{hi85}>{e(v85_fmt)}</td></tr>'
            )

    return (f'<div class="section"><h2>Speed Grade {e(grade)}</h2>'
            f'<table class="speed-table">{ths}{"".join(trs)}</table></div>')


def render_orderable(raw_opn, orderable_rows):
    exact, same_base = get_orderable_matches(raw_opn, orderable_rows)
    source = exact[0] if exact else (same_base[0] if same_base else None)
    title = "Orderable Info" if exact else "Orderable Info (closest match)"
    if not source:
        return '<div class="section"><h2>Orderable Info</h2><p>OPN not found in orderable table.</p></div>'

    skip = {"Device Line", "Base Part"}
    trs = []
    for k, v in source.items():
        if k not in skip and v.strip():
            trs.append(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>")

    extras = ""
    if exact and len(exact) > 1:
        names = ", ".join(e(r["Orderable Part Number"]) for r in exact[1:])
        extras = f'<p style="margin-top:8px;color:#555;font-size:12px;">Also orderable as: {names}</p>'
    elif same_base and not exact and len(same_base) > 1:
        extras = f'<p style="margin-top:8px;color:#555;font-size:12px;">... and {len(same_base)-1} more variants with the same base OPN</p>'

    return (f'<div class="section"><h2>{title}</h2>'
            f'<table>{"".join(trs)}</table>{extras}</div>')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_html(parsed, feature_rows, speed_rows, orderable_rows):
    dl  = parsed["device_line"]
    opn = parsed["raw"]

    body = "\n".join([
        render_parsed(parsed),
        render_features(parsed["base"], feature_rows),
        render_speed_grade(parsed["speed_grade"], speed_rows, dl),
        render_orderable(opn, orderable_rows),
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OPN: {e(opn)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <div class="opn">AM62x / AM62L / AM62A / AM62P OPN Parser</div>
      <h1>{e(opn)}</h1>
    </div>
  </header>
  <div class="body">
{body}
  </div>
</div>
<footer>Generated by parse_opn_html.py &nbsp;&bull;&nbsp; Data sourced from TI datasheets</footer>
</body>
</html>"""


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(HELP)
            sys.exit(0)
        raw_opn = sys.argv[1]
    else:
        print("AM62x OPN Parser (HTML)  |  run with -h for help")
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
    except FileNotFoundError as e_:
        print(f"ERROR: Missing data file: {e_}")
        print("Run build_master_csv.py to generate the master CSV files.")
        sys.exit(1)

    html_content = build_html(parsed, feature_rows, speed_rows, orderable_rows)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Wrote {OUTPUT_PATH}")
    webbrowser.open(f"file://{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
