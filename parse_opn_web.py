"""
AM62x OPN Parser - interactive web UI.

Starts a local HTTP server, opens the browser, and lets the user
search part numbers directly in the page.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_opn import (
    parse_opn,
    load_features, load_speed_grades, load_orderable,
    BASE_PARTS, CORE_COUNT, EVOLUTION_STAGE, REVISION, PACKAGE,
    AM62X_SPEED_GRADE, AM62L_SPEED_GRADE, AM62A_SPEED_GRADE, AM62P_SPEED_GRADE,
    AM62X_FEATURES, AM62L_FEATURES, AM62A_FEATURES, AM62P_FEATURES,
    AM62X_FUNCTIONAL_SAFETY, AM62X_TEMPERATURE, AM62L_TEMPERATURE,
    decode_am62l_security_fs,
    get_device_features, get_speed_grade_details, get_orderable_matches,
    SPEED_DISPLAY_COLS, _V85_MAP,
)
from parse_opn_html import (
    e, badge, CSS,
    render_parsed, render_features, render_speed_grade, render_orderable,
)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

# ---------------------------------------------------------------------------
# Load data once at startup
# ---------------------------------------------------------------------------

try:
    FEATURE_ROWS   = load_features()
    SPEED_ROWS     = load_speed_grades()
    ORDERABLE_ROWS = load_orderable()
except FileNotFoundError as ex:
    print(f"ERROR: {ex}")
    print("Run build_master_csv.py first.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Page templates
# ---------------------------------------------------------------------------

EXTRA_CSS = """
.search-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 28px;
    align-items: center;
}
.search-bar input[type=text] {
    flex: 1;
    padding: 10px 14px;
    font-size: 15px;
    border: 2px solid #ddd;
    border-radius: 6px;
    font-family: monospace;
    outline: none;
    transition: border-color .2s;
}
.search-bar input[type=text]:focus { border-color: #c41230; }
.search-bar button {
    padding: 10px 22px;
    background: #c41230;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background .2s;
}
.search-bar button:hover { background: #a00f26; }
.error-box {
    background: #fce8e8;
    border-left: 4px solid #c41230;
    padding: 14px 18px;
    border-radius: 4px;
    color: #7a0e1e;
    font-size: 14px;
}
.welcome {
    text-align: center;
    padding: 40px 20px;
    color: #888;
}
.welcome h3 { font-size: 18px; margin-bottom: 10px; color: #555; }
.welcome p  { font-size: 13px; line-height: 1.7; }
.examples   { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 16px; }
.example-btn {
    background: #f0f2f5;
    border: 1px solid #d0d4db;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    font-family: monospace;
    cursor: pointer;
    text-decoration: none;
    color: #333;
    transition: background .15s;
}
.example-btn:hover { background: #e2e6ec; }
"""

EXAMPLES = [
    "AM6254ATCGHIALWR",
    "AM62L32BOGHAANBR",
    "AM62A74AVMHIANFR",
    "AM62P54CVMHIAMHR",
    "AM62A12AQMSIANFRQ1",
    "AM62P34CSMSIAMHRQ1",
    "XAM6254ATCGHAALW",
]

SUPPORTED_DEVICES = sorted(BASE_PARTS.keys())


def page_shell(body_content, current_opn=""):
    example_links = "\n".join(
        f'<a class="example-btn" href="/?opn={ex}">{ex}</a>'
        for ex in EXAMPLES
    )
    supported = ", ".join(SUPPORTED_DEVICES)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AM62 OPN Parser</title>
<style>
{CSS}
{EXTRA_CSS}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <div class="opn">Supported: AM62x &bull; AM62L &bull; AM62A &bull; AM62P</div>
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
    <div style="margin-top:24px;padding-top:16px;border-top:1px solid #eee;font-size:12px;color:#aaa;">
      Supported base parts: {e(supported)}
    </div>
  </div>
</div>
<footer>AM62 OPN Parser &nbsp;&bull;&nbsp; Data sourced from TI datasheets</footer>
<script>
  // Let example links fill the input instead of navigating immediately
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


def welcome_content():
    example_links = "\n".join(
        f'<a class="example-btn" href="/?opn={ex}">{ex}</a>'
        for ex in EXAMPLES
    )
    return f"""
<div class="welcome">
  <h3>Enter an Orderable Part Number above to get started</h3>
  <p>The parser decodes every field of the OPN and shows device features,<br>
     speed grade frequencies, and orderable information from the datasheet.</p>
  <div class="examples">{example_links}</div>
</div>"""


def result_content(parsed):
    dl = parsed["device_line"]
    sections = "\n".join([
        render_parsed(parsed),
        render_features(parsed["base"], FEATURE_ROWS),
        render_speed_grade(parsed["speed_grade"], SPEED_ROWS, dl),
        render_orderable(parsed["raw"], ORDERABLE_ROWS),
    ])
    return sections


def error_content(opn, message):
    return f'<div class="error-box"><strong>Cannot parse &ldquo;{e(opn)}&rdquo;</strong><br>{e(message)}</div>'


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress request logging

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query      = urllib.parse.parse_qs(parsed_url.query)
        opn        = query.get("opn", [""])[0].strip()

        if opn:
            parsed, err = parse_opn(opn)
            if err:
                body = error_content(opn, err)
            else:
                body = result_content(parsed)
        else:
            body = welcome_content()
            opn  = ""

        html_page = page_shell(body, opn)
        encoded   = html_page.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


# ---------------------------------------------------------------------------
# Start server
# ---------------------------------------------------------------------------

def main():
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    url    = f"http://localhost:{PORT}"
    print(f"OPN Parser running at {url}")
    print("Press Ctrl+C to stop.")

    # Open browser after a short delay so the server is ready
    threading.Timer(0.4, webbrowser.open, args=[url]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
