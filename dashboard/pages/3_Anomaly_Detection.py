"""Anomaly Detection page — detector performance, timeline, flagged hours."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import lib

lib.setup_page("Anomaly Detection", "🚨")
lib.sidebar()
if not lib.require_data():
    st.stop()

lib.hero("Anomaly Detection",
         "Robust z-score detector for outages, faults and sensor spikes — "
         "context-aware by hour-of-day and month.")

anom = lib.stat("anomaly_stats.json")
flags = lib.csv("anomaly_flags.csv")
if flags.empty:
    st.error("Anomaly outputs not found. Run the pipeline first.")
    st.stop()
flags["time"] = pd.to_datetime(flags["time"], utc=True)

tp = anom.get("true_positives", 0)
fp = anom.get("false_positives", 0)
fn = anom.get("false_negatives", 0)
prec = anom.get("precision", 0)
rec = anom.get("recall", 0)
f1 = round(2 * prec * rec / (prec + rec), 2) if (prec + rec) else 0

# ---- KPIs ----------------------------------------------------------------
k = st.columns(4)
lib.kpi(k[0], "Flagged hours", f"{anom.get('flagged_hours','—')}")
lib.kpi(k[1], "Precision", f"{prec}", "few false alarms")
lib.kpi(k[2], "Recall", f"{rec}", "faults caught")
lib.kpi(k[3], "F1 score", f"{f1}")

st.markdown("")

# ---- timeline ------------------------------------------------------------
st.markdown("#### Consumption stream with flagged anomalies")
flagged_idx = np.where(flags["is_anomaly"].values)[0]
if len(flagged_idx):
    center = flagged_idx[len(flagged_idx) // 3]
    lo, hi = max(0, center - 400), min(len(flags), center + 400)
else:
    lo, hi = 0, min(len(flags), 800)
zoom = st.checkbox("Zoom to a flagged region", value=True)
view = flags.iloc[lo:hi] if zoom else flags
an = view[view["is_anomaly"]]
fig = go.Figure()
fig.add_trace(go.Scatter(x=view["time"], y=view["value"], mode="lines",
                         line=dict(color=lib.DARK, width=1), name="Consumption"))
fig.add_trace(go.Scatter(x=an["time"], y=an["value"], mode="markers", name="Flagged anomaly",
                         marker=dict(color=lib.RED, size=8, symbol="circle",
                                     line=dict(color="white", width=1))))
fig.update_yaxes(title="Active power (kW)")
st.plotly_chart(lib.style_fig(fig, height=360), use_container_width=True)

# ---- confusion matrix + hour distribution -------------------------------
c1, c2 = st.columns([1, 1.3])

with c1:
    st.markdown("#### Detector confusion matrix")
    z = [[tp, fn], [fp, "—"]]
    text = [[f"TP<br><b>{tp}</b>", f"FN<br><b>{fn}</b>"],
            [f"FP<br><b>{fp}</b>", "TN<br><b>—</b>"]]
    fig = go.Figure(go.Heatmap(
        z=[[tp, fn], [fp, 0]],
        text=text, texttemplate="%{text}",
        x=["Predicted +", "Predicted −"], y=["Actual +", "Actual −"],
        colorscale=[[0, "#f2f6f3"], [1, lib.DARK]], showscale=False,
        hoverinfo="text"))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(lib.style_fig(fig, height=300, legend=False), use_container_width=True)
    st.caption(f"Injected anomalies: {anom.get('injected_anomaly_hours','—')} · "
               f"TN not shown (dominant class).")

with c2:
    st.markdown("#### When do anomalies occur?")
    an_all = flags[flags["is_anomaly"]].copy()
    an_all["hour"] = an_all["time"].dt.hour
    byhour = an_all.groupby("hour").size().reindex(range(24), fill_value=0)
    fig = go.Figure(go.Bar(x=byhour.index, y=byhour.values, marker_color=lib.ORANGE))
    fig.update_xaxes(title="Hour of day", dtick=3)
    fig.update_yaxes(title="Flagged count")
    st.plotly_chart(lib.style_fig(fig, height=300, legend=False), use_container_width=True)

# ---- flagged table -------------------------------------------------------
st.markdown("#### Flagged anomaly log")
tbl = flags[flags["is_anomaly"]].copy()
tbl["time"] = tbl["time"].dt.strftime("%Y-%m-%d %H:%M")
tbl = tbl.rename(columns={"time": "Timestamp (UTC)", "value": "Value (kW)",
                          "is_anomaly": "Anomaly"})[["Timestamp (UTC)", "Value (kW)"]]
st.dataframe(tbl, use_container_width=True, hide_index=True, height=300)
st.download_button("⬇ Download anomaly_flags.csv",
                   flags.to_csv(index=False).encode(), "anomaly_flags.csv", "text/csv")
