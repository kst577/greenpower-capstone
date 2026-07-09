"""GreenPower Utilities — Energy Analytics Dashboard (Streamlit).

Multi-page interactive dashboard built on the pipeline outputs. This file is the
landing / Overview page; the other sections live in dashboard/pages/.

Run:
    streamlit run dashboard/app.py
Requires: streamlit, plotly (pip install streamlit plotly).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import lib

lib.setup_page("Overview", "⚡")
if not lib.require_login():
    st.stop()
lib.sidebar()

if not lib.require_data():
    st.stop()

feat = lib.stat("feature_stats.json")
mdl = lib.stat("model_stats.json")
anom = lib.stat("anomaly_stats.json")
clean = lib.stat("cleaning_report.json")

lib.hero(
    "GreenPower Utilities — Energy Analytics",
    "End-to-end energy consumption analytics: cleaned time-series, demand "
    "forecasting, anomaly detection and wind-generation insight.",
)

# ---- headline KPIs -------------------------------------------------------
mean_completeness = None
if clean:
    vals = [v.get("mean_completeness") for v in clean.values() if isinstance(v, dict)]
    vals = [v for v in vals if v is not None]
    mean_completeness = sum(vals) / len(vals) if vals else None

st.markdown("### Key results at a glance")
r1 = st.columns(4)
lib.kpi(r1[0], "Avg daily consumption", f"{feat.get('daily_total_mean_kwh','—')} kWh")
lib.kpi(r1[1], "Peak hour",
        f"{int(feat['median_peak_hour']):02d}:00" if feat.get("median_peak_hour") is not None else "—",
        f"{feat.get('evening_peak_share','—')}% of days")
lib.kpi(r1[2], "Peak-to-average ratio", f"{feat.get('par_mean','—')}")
lib.kpi(r1[3], "Load factor",
        f"{feat['load_factor_mean']*100:.1f}%" if feat.get("load_factor_mean") is not None else "—")

r2 = st.columns(4)
lib.kpi(r2[0], "Best model MAPE", f"{mdl.get('best_mape','—')}%",
        f"↓{mdl.get('improve_vs_baseline_pct','—')}% RMSE vs baseline")
lib.kpi(r2[1], "Wind capacity factor", f"{feat.get('wind_cf_mean','—')}%")
lib.kpi(r2[2], "Anomaly precision", f"{anom.get('precision','—')}",
        f"recall {anom.get('recall','—')}")
lib.kpi(r2[3], "Data completeness",
        f"{mean_completeness*100:.1f}%" if mean_completeness is not None else "—")

st.markdown("")

# ---- pipeline flow + summary --------------------------------------------
left, right = st.columns([1.35, 1])

with left:
    st.markdown("#### Pipeline")
    stages = ["Acquire", "Clean", "Store", "Features", "Models", "Anomaly", "Dashboard"]
    fig = go.Figure()
    for i, s in enumerate(stages):
        fig.add_shape(type="rect", x0=i, x1=i + 0.82, y0=0, y1=1,
                      line=dict(color=lib.DARK, width=1.5),
                      fillcolor=lib.DARK if i == len(stages) - 1 else "#e9f3ee")
        fig.add_annotation(x=i + 0.41, y=0.5, text=f"<b>{s}</b>", showarrow=False,
                           font=dict(size=12, color="#fff" if i == len(stages) - 1 else lib.DARK))
        if i < len(stages) - 1:
            fig.add_annotation(x=i + 0.91, y=0.5, text="→", showarrow=False,
                               font=dict(size=18, color=lib.MID))
    fig.update_xaxes(visible=False, range=[-0.1, len(stages)])
    fig.update_yaxes(visible=False, range=[-0.2, 1.2])
    fig.update_layout(height=120, margin=dict(l=0, r=0, t=6, b=0),
                      paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f"""
        <div class="gp-card">
        This dashboard is generated from the live pipeline outputs. It ingests
        household electricity consumption, wind-turbine generation and weather
        data, cleans and stores them, engineers features, then trains three
        forecasting models and a robust anomaly detector.
        <br><br>
        The best model (<b>{mdl.get('best_model','—')}</b>) reaches
        <b>{mdl.get('best_mape','—')}% MAPE</b> on a
        {mdl.get('test_days','—')}-day hold-out — about
        <b>{mdl.get('improve_vs_baseline_pct','—')}% lower error</b> than the
        seasonal-naive baseline. The anomaly detector runs at
        <b>{anom.get('precision','—')} precision</b> /
        <b>{anom.get('recall','—')} recall</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown("#### Dataset coverage")
    src = lib.query("SELECT * FROM data_source")
    audit = lib.query("SELECT * FROM load_audit")
    rows = {
        "Consumption (UCI household)": audit.loc[audit["table"] == "consumption", "rows_loaded"].squeeze() if not audit.empty else "—",
        "Generation (SCADA wind)": audit.loc[audit["table"] == "generation", "rows_loaded"].squeeze() if not audit.empty else "—",
        "Weather (NOAA)": audit.loc[audit["table"] == "weather", "rows_loaded"].squeeze() if not audit.empty else "—",
    }
    cov = pd.DataFrame(
        {"Dataset": list(rows.keys()), "Hourly rows": [f"{int(v):,}" if str(v).isdigit() else v for v in rows.values()]}
    )
    st.dataframe(cov, use_container_width=True, hide_index=True)
    st.caption("Navigate the sections in the left sidebar for detailed analysis.")

# ---- full consumption trend ---------------------------------------------
st.markdown("#### Daily consumption trend (full history)")
daily = lib.query("SELECT day, total_kwh FROM consumption_daily")
daily["day"] = pd.to_datetime(daily["day"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=daily["day"], y=daily["total_kwh"], mode="lines",
                         line=dict(color=lib.DARK, width=1.2), name="Daily kWh",
                         fill="tozeroy", fillcolor="rgba(31,112,69,0.08)"))
roll = daily.set_index("day")["total_kwh"].rolling(30, min_periods=1).mean()
fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines",
                         line=dict(color=lib.ORANGE, width=2), name="30-day average"))
fig.update_yaxes(title="Daily consumption (kWh)")
st.plotly_chart(lib.style_fig(fig, height=320), use_container_width=True)
