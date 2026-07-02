"""Capture all execution-evidence screenshots for the Final Execution Report.

Produces, in outputs/screenshots/ (all at device_scale_factor=2):
  01_pipeline_run.png   - the full `python run_pipeline.py` terminal output
  02_database_query.png - sqlite3 querying .tables / load_audit / evaluation_summary
                          / a sample of consumption_daily
  03_dashboard.png      - the LIVE Streamlit dashboard at localhost:8501
  fig_<name>.png        - one framed card per figure in outputs/figures/

Prereqs: run_pipeline.py has run; /tmp/run_log.txt and /tmp/db_log.txt exist;
Streamlit is serving dashboard/app.py on http://localhost:8501.
"""
import base64
import html
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = ROOT / "outputs" / "screenshots"
FIGS = ROOT / "outputs" / "figures"
SHOTS.mkdir(parents=True, exist_ok=True)


def term_html(text, title):
    body = html.escape(text)
    for k, col in [("[acquire]", "#6fb3ff"), ("[clean]", "#6fb3ff"), ("[storage]", "#6fb3ff"),
                   ("[features]", "#6fb3ff"), ("[models]", "#6fb3ff"), ("[anomaly]", "#6fb3ff"),
                   ("[viz]", "#6fb3ff"), ("[dashboard]", "#6fb3ff")]:
        body = body.replace(k, f'<span style="color:{col}">{k}</span>')
    body = body.replace("best:", '<span style="color:#7CFC98">best:</span>')
    body = body.replace("sqlite&gt;", '<span style="color:#7CFC98">sqlite&gt;</span>')
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


def shoot_html(pw, html_str, out, width=980, height=None):
    f = SHOTS / "_tmp.html"
    f.write_text(html_str)
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": width, "height": height or 700}, device_scale_factor=2)
    pg.goto("file://" + str(f))
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(SHOTS / out), full_page=(height is None))
    b.close()
    print("wrote", (SHOTS / out).relative_to(ROOT))


def fig_card(title, fig):
    p = FIGS / fig
    b64 = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return f"""<html><head><meta charset='utf-8'><style>
      body{{margin:0;background:#eef2ef;font-family:Arial,Helvetica,sans-serif}}
      .card{{margin:16px;background:#fff;border:1px solid #e2e8e3;border-radius:10px;
             padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
      h3{{margin:0 0 10px;font-size:15px;color:#1f7045}}
      img{{width:100%;height:auto;border-radius:4px}}
    </style></head><body><div class='card'><h3>{title}</h3>
      <img src='{b64}'></div></body></html>"""


FIGURES = [
    ("Average Hourly Load Profile (weekday vs weekend)", "load_profile.png"),
    ("Forecast vs Actual — Final Test Week", "forecast.png"),
    ("Model Error Comparison (60-day hold-out)", "model_metrics.png"),
    ("Anomaly Detection — Robust z-score + Persistence", "anomaly.png"),
    ("Daily Consumption vs Temperature", "load_temp.png"),
    ("Wind Capacity Factor by Month", "capacity_factor.png"),
]


def main():
    run_log = pathlib.Path("/tmp/run_log.txt").read_text()
    db_log = pathlib.Path("/tmp/db_log.txt").read_text()

    with sync_playwright() as pw:
        # 01 + 02 terminal shots
        shoot_html(pw, term_html(run_log, "python run_pipeline.py"), "01_pipeline_run.png", 1000)
        shoot_html(pw, term_html(db_log, "sqlite3 data/greenpower.db  —  query results"),
                   "02_database_query.png", 1000)

        # 03 LIVE Streamlit dashboard
        ok = False
        try:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 1600}, device_scale_factor=2)
            pg.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
            # let plotly charts finish drawing
            pg.wait_for_selector("text=GreenPower Utilities", timeout=20000)
            pg.wait_for_timeout(4500)
            pg.screenshot(path=str(SHOTS / "03_dashboard.png"), full_page=True)
            b.close()
            print("wrote", (SHOTS / "03_dashboard.png").relative_to(ROOT), "(live Streamlit)")
            ok = True
        except Exception as e:
            print("streamlit shot failed, falling back to static html:", e, file=sys.stderr)
        if not ok:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 1500}, device_scale_factor=2)
            pg.goto("file://" + str(ROOT / "dashboard" / "dashboard.html"))
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(SHOTS / "03_dashboard.png"), full_page=True)
            b.close()
            print("wrote", (SHOTS / "03_dashboard.png").relative_to(ROOT), "(static fallback)")

        # one card per figure
        for title, fig in FIGURES:
            name = "fig_" + fig
            shoot_html(pw, fig_card(title, fig), name, 900)

    (SHOTS / "_tmp.html").unlink(missing_ok=True)
    print("done")


if __name__ == "__main__":
    main()
