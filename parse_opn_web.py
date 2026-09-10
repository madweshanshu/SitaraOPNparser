"""
AM62x OPN Parser - interactive web UI backed by master.csv.

Starts a local HTTP server, opens the browser, and lets the user
search part numbers directly in the page. Reads only master.csv.

Usage:
    python3 parse_opn_web.py          (default port 8080)
    python3 parse_opn_web.py 5000     (custom port)
"""

import http.server
import urllib.parse
import webbrowser
import threading
import sys
import os
import html as _html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_opn import (
    parse_opn,
    BASE_PARTS, CORE_COUNT, EVOLUTION_STAGE, REVISION, PACKAGE,
    AM62X_SPEED_GRADE, AM62L_SPEED_GRADE, AM62A_SPEED_GRADE, AM62P_SPEED_GRADE,
    AM62X_FEATURES, AM62L_FEATURES, AM62A_FEATURES, AM62P_FEATURES,
    AM62X_FUNCTIONAL_SAFETY, AM62X_TEMPERATURE, AM62L_TEMPERATURE,
    decode_am62l_security_fs,
)
from parse_opn_terminal import (
    load_master,
    ORDERABLE_COLS, FEATURE_COLS, SPEED_COLS,
)
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
.speed-table td.diff { color: #c41230; font-weight: 600; }
footer { text-align: center; color: #888; font-size: 12px; margin-top: 20px; }
"""

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

# ---------------------------------------------------------------------------
# Load master.csv once at startup
# ---------------------------------------------------------------------------

try:
    ALL_ROWS, BY_OPN, BY_BASE = load_master()
except FileNotFoundError:
    print("ERROR: master.csv not found. Run build_master_csv.py first.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def e(s):
    return _html.escape(str(s))

def badge(val):
    v = str(val).strip().lower()
    if v in ("yes", "true"):
        return '<span class="badge badge-yes">Yes</span>'
    if v in ("no", "false", ""):
        return '<span class="badge badge-no">No</span>'
    return e(val)

EXTRA_CSS = """
.search-bar {
    display: flex; gap: 10px; margin-bottom: 28px; align-items: center;
}
.search-bar input[type=text] {
    flex: 1; padding: 10px 14px; font-size: 15px;
    border: 2px solid #ddd; border-radius: 6px;
    font-family: monospace; outline: none; transition: border-color .2s;
}
.search-bar input[type=text]:focus { border-color: #c41230; }
.search-bar button {
    padding: 10px 22px; background: #c41230; color: white;
    border: none; border-radius: 6px; font-size: 14px;
    font-weight: 600; cursor: pointer; transition: background .2s;
}
.search-bar button:hover { background: #a00f26; }
.error-box {
    background: #fce8e8; border-left: 4px solid #c41230;
    padding: 14px 18px; border-radius: 4px;
    color: #7a0e1e; font-size: 14px;
}
.welcome { text-align: center; padding: 40px 20px; color: #888; }
.welcome h3 { font-size: 18px; margin-bottom: 10px; color: #555; }
.welcome p  { font-size: 13px; line-height: 1.7; }
.examples   { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 16px; }
.example-btn {
    background: #f0f2f5; border: 1px solid #d0d4db; border-radius: 20px;
    padding: 5px 14px; font-size: 12px; font-family: monospace;
    cursor: pointer; text-decoration: none; color: #333; transition: background .15s;
}
.example-btn:hover { background: #e2e6ec; }
.speed-table th {
    background: #f5f5f5; font-weight: 600; font-size: 12px; color: #444; text-align: right;
}
.speed-table th:first-child { text-align: left; }
.speed-table td { text-align: right; font-family: monospace; font-size: 13px; }
.speed-table td:first-child { text-align: left; font-family: inherit; font-size: 14px; color: #555; font-weight: 500; }
.speed-table td.diff { color: #c41230; font-weight: 600; }
"""

EXAMPLES = [
    "AM6254ATCGHIALWR",
    "AM62L32BOGHAANBR",
    "AM62A74AVMHIANFR",
    "AM62P54CVMHIAMHR",
    "AM62A12AQMSIANFRQ1",
    "AM62P34CSMSIAMHRQ1",
]

# ---------------------------------------------------------------------------
# Section renderers (HTML)
# ---------------------------------------------------------------------------

def render_parsed(parsed, row):
    base_info = BASE_PARTS.get(parsed["base"], {})
    dl = parsed["device_line"]

    if dl == "AM62L":
        speed_desc = AM62L_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62L_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    elif dl == "AM62A":
        speed_desc = AM62A_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62A_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    elif dl == "AM62P":
        speed_desc = AM62P_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62P_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62L_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])
        sec_fs     = decode_am62l_security_fs(parsed["security_fs"])
    else:
        speed_desc = AM62X_SPEED_GRADE.get(parsed["speed_grade"], parsed["speed_grade"])
        feat_desc  = AM62X_FEATURES.get(parsed["features"], parsed["features"])
        temp_desc  = AM62X_TEMPERATURE.get(parsed["temperature"], parsed["temperature"])

    family = row.get("Family") or base_info.get("family", "?")
    desc   = row.get("Description") or base_info.get("desc", "?")

    rows_data = [
        ("Base Part",      f'<span style="background:#1a56db;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{e(parsed["base"])}</span>'),
        ("Family",         e(f"{family} - {desc}")),
        ("A53 Core Count", e(f"{base_info.get('cores','?')} ({CORE_COUNT.get(base_info.get('cores'),'?')})")),
        ("Evolution Stage",e(EVOLUTION_STAGE.get(parsed["evolution"], parsed["evolution"]))),
        ("Revision",       e(REVISION.get(parsed["revision"], parsed["revision"]))),
        ("Speed Grade",    e(speed_desc)),
        ("Features",       e(feat_desc)),
    ]
    if dl in ("AM62L", "AM62A", "AM62P"):
        rows_data.append(("Security / Safety", e(sec_fs)))
    else:
        rows_data.append(("Functional Safety", e(AM62X_FUNCTIONAL_SAFETY.get(parsed["func_safety"], parsed["func_safety"]))))
        rows_data.append(("Security", e("Non-Secure" if parsed["security"] == "G" else f"Secure ({parsed['security']})")))
    rows_data += [
        ("Temperature",   e(temp_desc)),
        ("Package",       e(f"{parsed['package']} - {PACKAGE.get(parsed['package'],'?')}")),
        ("Tape & Reel",   badge("Yes" if parsed["tape_reel"] else "No")),
        ("AEC-Q100 (Q1)", badge("Yes" if parsed["automotive_q1"] else "No")),
    ]

    trs = "\n".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows_data)
    return f'<div class="section"><h2>Parsed Fields</h2><table>{trs}</table></div>'


def render_features(base_part, row):
    trs = []
    for col in FEATURE_COLS:
        val = row.get(col, "").strip()
        if not val:
            continue
        cell = badge(val) if val.lower() in ("yes", "no") else e(val)
        trs.append(f"<tr><td>{e(col)}</td><td>{cell}</td></tr>")
    if not trs:
        return f'<div class="section"><h2>Device Features ({e(base_part)})</h2><p>No data.</p></div>'
    return (f'<div class="section"><h2>Device Features ({e(base_part)})</h2>'
            f'<table>{"".join(trs)}</table></div>')


def render_speed_grade(parsed, row):
    sg = parsed["speed_grade"]
    dl = parsed["device_line"]

    # Collect populated rows (deduplicated by label)
    results = []
    seen = set()
    for col75, col85, label in SPEED_COLS:
        if label in seen:
            continue
        v75 = row.get(col75, "").strip()
        if not v75:
            continue
        seen.add(label)
        v85 = (row.get(col85, "").strip() if col85 else "") or v75
        results.append((label, v75, v85))

    if not results:
        return f'<div class="section"><h2>Speed Grade {e(sg)}</h2><p>No data.</p></div>'

    if dl == "AM62L":
        ths = "<tr><th>Subsystem</th><th>Max Freq</th></tr>"
        trs = []
        for lbl, v75, _ in results:
            unit = "MT/s" if lbl in ("DDR4", "LPDDR4") else "MHz"
            trs.append(f"<tr><td>{e(lbl)}</td><td>{e(v75)} {unit}</td></tr>")
    else:
        ths = "<tr><th>Subsystem</th><th>@ 0.75 V</th><th>@ 0.85 V</th></tr>"
        trs = []
        for lbl, v75, v85 in results:
            unit   = "MT/s" if lbl in ("DDR4", "LPDDR4") else "MHz"
            differ = v75 != v85
            cls    = ' class="diff"' if differ else ""
            trs.append(
                f"<tr><td>{e(lbl)}</td>"
                f"<td{cls}>{e(v75)} {unit}</td>"
                f"<td{cls}>{e(v85)} {unit}</td></tr>"
            )

    return (f'<div class="section"><h2>Speed Grade {e(sg)}</h2>'
            f'<table class="speed-table">{ths}{"".join(trs)}</table></div>')


def render_orderable(opn, row):
    trs = []
    for col in ORDERABLE_COLS:
        val = row.get(col, "").strip()
        if val:
            trs.append(f"<tr><td>{e(col)}</td><td>{e(val)}</td></tr>")
    if not trs:
        return f'<div class="section"><h2>Orderable Info</h2><p>OPN not found in master.csv.</p></div>'
    return f'<div class="section"><h2>Orderable Info</h2><table>{"".join(trs)}</table></div>'


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def page_shell(body_content, current_opn=""):
    example_links = "\n".join(
        f'<a class="example-btn" href="/?opn={ex}">{ex}</a>'
        for ex in EXAMPLES
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AM62 OPN Parser v2</title>
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <div class="opn">AM62x &bull; AM62L &bull; AM62A &bull; AM62P &nbsp;&mdash;&nbsp; powered by master.csv</div>
      <h1>AM62 OPN Parser</h1>
    </div>
  </header>
  <div class="body">
    <form class="search-bar" method="GET" action="/">
      <input type="text" name="opn" value="{e(current_opn)}"
             placeholder="Enter OPN e.g. AM62P54CVMHIAMHR"
             autofocus autocomplete="off" spellcheck="false">
      <button type="submit">Search</button>
    </form>
    {body_content}
  </div>
</div>
<footer>AM62 OPN Parser v2 &nbsp;&bull;&nbsp; Single master.csv &nbsp;&bull;&nbsp; Data from TI datasheets</footer>
<script>
  document.querySelectorAll('.example-btn').forEach(a => {{
    a.addEventListener('click', ev => {{
      ev.preventDefault();
      document.querySelector('input[name=opn]').value = a.textContent.trim();
      document.querySelector('form').submit();
    }});
  }});
</script>
</body>
</html>"""


def welcome_body():
    example_links = "\n".join(
        f'<a class="example-btn" href="/?opn={ex}">{ex}</a>'
        for ex in EXAMPLES
    )
    total = len(ALL_ROWS)
    return f"""
<div class="welcome">
  <h3>Enter an Orderable Part Number above to get started</h3>
  <p>All data is served from a single <code>master.csv</code> ({total} OPNs).<br>
     Features, speed grades, and orderable info are all in one lookup.</p>
  <div class="examples">{example_links}</div>
</div>"""


def result_body(parsed, row):
    dl = parsed["device_line"]
    return "\n".join([
        render_parsed(parsed, row),
        render_features(parsed["base"], row),
        render_speed_grade(parsed, row),
        render_orderable(parsed["raw"], row),
    ])


def error_body(opn, message):
    return f'<div class="error-box"><strong>Cannot parse &ldquo;{e(opn)}&rdquo;</strong><br>{e(message)}</div>'


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        opn   = query.get("opn", [""])[0].strip()

        if opn:
            parsed, err = parse_opn(opn)
            if err:
                body = error_body(opn, err)
            else:
                clean_key = opn.upper().split(".")[0]
                row = BY_OPN.get(clean_key) or BY_BASE.get(parsed["base"], {})
                body = result_body(parsed, row)
        else:
            body = welcome_body()
            opn  = ""

        html_page = page_shell(body, opn)
        encoded   = html_page.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    url    = f"http://localhost:{PORT}"
    print(f"OPN Parser v2 running at {url}  (master.csv: {len(ALL_ROWS)} OPNs)")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.4, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
