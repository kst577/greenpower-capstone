"""Render screenshots of the pipeline output for the execution report."""
import html, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = ROOT / "outputs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)


def term_html(text, title):
    body = html.escape(text)
    # colourise a few tokens
    for k, col in [("[acquire]", "#6fb3ff"), ("[clean]", "#6fb3ff"), ("[storage]", "#6fb3ff"),
                   ("[features]", "#6fb3ff"), ("[models]", "#6fb3ff"), ("[anomaly]", "#6fb3ff"),
                   ("[viz]", "#6fb3ff"), ("[dashboard]", "#6fb3ff")]:
        body = body.replace(k, f'<span style="color:{col}">{k}</span>')
    body = body.replace("best:", '<span style="color:#7CFC98">best:</span>')
    return f"""<html><head><meta charset='utf-8'><style>
      body{{margin:0;background:#0d1117}}
      .win{{margin:14px;border-radius:8px;overflow:hidden;border:1px solid #30363d;font-family:'DejaVu Sans Mono',monospace}}
      .bar{{background:#21262d;padding:8px 12px;color:#c9d1d9;font-size:12px;font-family:sans-serif}}
      .bar .dot{{height:11px;width:11px;border-radius:50%;display:inline-block;margin-right:6px}}
      pre{{margin:0;padding:14px 16px;background:#0d1117;color:#d1d5db;font-size:12.5px;line-height:1.5;white-space:pre-wrap}}
    </style></head><body><div class='win'>
      <div class='bar'><span class='dot' style='background:#ff5f56'></span>
      <span class='dot' style='background:#ffbd2e'></span>
      <span class='dot' style='background:#27c93f'></span>&nbsp; {title}</div>
      <pre>{body}</pre></div></body></html>"""


def shoot(html_str, out, width=980, height=None):
    f = SHOTS / "_tmp.html"; f.write_text(html_str)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        vp = {"width": width, "height": height or 700}
        pg = b.new_page(viewport=vp, device_scale_factor=2)
        pg.goto("file://" + str(f))
        pg.screenshot(path=str(SHOTS / out), full_page=(height is None))
        b.close()
    print("wrote", (SHOTS / out).relative_to(ROOT))


run_log = pathlib.Path("/tmp/run_log.txt").read_text()
db_log = pathlib.Path("/tmp/db_log.txt").read_text()
shoot(term_html(run_log, "python run_pipeline.py"), "01_pipeline_run.png", 980)
shoot(term_html(db_log, "sqlite3 data/greenpower.db  —  query results"), "02_database_query.png", 980)

# dashboard screenshot
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 1500}, device_scale_factor=2)
    pg.goto("file://" + str(ROOT / "dashboard" / "dashboard.html"))
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(SHOTS / "03_dashboard.png"), full_page=True)
    b.close()
print("wrote", (SHOTS / "03_dashboard.png").relative_to(ROOT))
