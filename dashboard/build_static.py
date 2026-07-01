"""Build a self-contained static HTML dashboard from the pipeline outputs.

Embeds the generated figures and headline KPIs into a single styled HTML file
(dashboard/dashboard.html) that opens in any browser with no server. An
interactive Streamlit version reading the same database is in dashboard/app.py.
"""
from __future__ import annotations
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "outputs" / "figures"
OUT = ROOT / "dashboard" / "dashboard.html"


def _stat(name, default="—"):
    p = ROOT / "outputs" / name
    return json.loads(p.read_text()) if p.exists() else {}


def _b64(fig):
    p = FIGS / fig
    if not p.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def build():
    feat = _stat("feature_stats.json")
    mdl = _stat("model_stats.json")
    anom = _stat("anomaly_stats.json")
    kpis = [
        ("Avg daily consumption", f"{feat.get('daily_total_mean_kwh','—')} kWh"),
        ("Peak-to-average ratio", f"{feat.get('par_mean','—')}"),
        ("Best-model MAPE", f"{mdl.get('best_mape','—')}%"),
        ("Wind capacity factor", f"{feat.get('wind_cf_mean','—')}%"),
        ("Anomaly precision", f"{anom.get('precision','—')}"),
    ]
    panels = [
        ("Daily Load Profile & Evening Peak", "load_profile.png"),
        ("Forecast vs Actual (final test week)", "forecast.png"),
        ("Model Error Comparison", "model_metrics.png"),
        ("Anomaly Monitor", "anomaly.png"),
        ("Consumption vs Temperature", "load_temp.png"),
        ("Wind Capacity Factor by Month", "capacity_factor.png"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>' for l, v in kpis)
    panel_html = "".join(
        f'<div class="panel"><h3>{t}</h3><img src="{_b64(f)}"></div>' for t, f in panels)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>GreenPower Analytics Dashboard</title>
<style>
  body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef2ef;color:#1a1a1a}}
  header{{background:#1f7045;color:#fff;padding:16px 26px;display:flex;align-items:center;justify-content:space-between}}
  header h1{{font-size:20px;margin:0}}
  header .sub{{color:#cfe6d8;font-size:12px}}
  .kpis{{display:flex;gap:14px;padding:18px 26px;flex-wrap:wrap;background:#f6f8f6;border-bottom:1px solid #dfe6e0}}
  .kpi{{background:#fff;border:1px solid #e2e8e3;border-radius:8px;padding:12px 18px;min-width:150px}}
  .kpi .v{{font-size:22px;font-weight:700;color:#1f7045}}
  .kpi .l{{font-size:11px;color:#5a6b60;margin-top:3px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:22px 26px}}
  .panel{{background:#fff;border:1px solid #e2e8e3;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
  .panel h3{{margin:0 0 8px;font-size:13px;color:#1f7045}}
  .panel img{{width:100%;height:auto;border-radius:4px}}
  footer{{padding:14px 26px;color:#5a6b60;font-size:12px;text-align:center}}
</style></head><body>
<header><div><h1>GreenPower Utilities — Energy Analytics Dashboard</h1>
<div class="sub">Group 5 · IIT Jodhpur · built on the Week 4 feature layer</div></div>
<div class="sub">best model: {mdl.get('best_model','—')} · hold-out {mdl.get('test_days','—')} days</div></header>
<div class="kpis">{kpi_html}</div>
<div class="grid">{panel_html}</div>
<footer>Generated from live pipeline outputs · outputs/figures/ · GreenPower Utilities Capstone</footer>
</body></html>"""
    OUT.write_text(html)
    print(f"[dashboard] static dashboard written to {OUT.relative_to(ROOT)}")
    return OUT


if __name__ == "__main__":
    build()
