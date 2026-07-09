"""Wind Generation page — capacity factor, power curve, generation trends."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import lib

lib.setup_page("Wind Generation", "🌬️")
if not lib.require_login():
    st.stop()
lib.sidebar()
if not lib.require_data():
    st.stop()

lib.hero("Wind Generation",
         "SCADA wind-farm output — capacity factor, seasonality and the "
         "wind-speed power curve.")

feat = lib.stat("feature_stats.json")
gen = lib.query("SELECT time, power_kw, theoretical_power_kw, wind_speed_ms FROM generation")
gen["time"] = pd.to_datetime(gen["time"], utc=True)
gdaily = lib.query("SELECT * FROM generation_daily")
gdaily["day"] = pd.to_datetime(gdaily["day"], utc=True)

RATED = 3600.0

# ---- KPIs ----------------------------------------------------------------
k = st.columns(4)
lib.kpi(k[0], "Mean capacity factor", f"{feat.get('wind_cf_mean','—')}%")
lib.kpi(k[1], "Rated capacity", f"{RATED/1000:.1f} MW")
lib.kpi(k[2], "Mean output", f"{gen['power_kw'].mean():.0f} kW")
lib.kpi(k[3], "Peak output", f"{gen['power_kw'].max():.0f} kW")

st.markdown("")

# ---- row 1: monthly CF + daily generation -------------------------------
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Capacity factor by month")
    cf = gdaily.copy()
    cf["month"] = cf["day"].dt.month
    m = cf.groupby("month")["capacity_factor"].mean() * 100
    fig = go.Figure(go.Bar(x=m.index, y=m.values, marker_color=lib.DARK,
                           text=[f"{v:.0f}%" for v in m.values], textposition="outside"))
    fig.update_xaxes(title="Month", dtick=1)
    fig.update_yaxes(title="Capacity factor (%)")
    st.plotly_chart(lib.style_fig(fig, legend=False), use_container_width=True)

with c2:
    st.markdown("#### Daily generation trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=gdaily["day"], y=gdaily["gen_kwh"], mode="lines",
                             line=dict(color=lib.MID, width=1), name="Daily kWh",
                             fill="tozeroy", fillcolor="rgba(63,155,110,0.12)"))
    roll = gdaily.set_index("day")["gen_kwh"].rolling(30, min_periods=1).mean()
    fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines",
                             line=dict(color=lib.ORANGE, width=2), name="30-day avg"))
    fig.update_yaxes(title="Generation (kWh/day)")
    st.plotly_chart(lib.style_fig(fig), use_container_width=True)

# ---- row 2: power curve --------------------------------------------------
st.markdown("#### Wind power curve (output vs wind speed)")
sample = gen.dropna(subset=["wind_speed_ms", "power_kw"])
if len(sample) > 5000:
    sample = sample.sample(5000, random_state=1)
fig = go.Figure()
fig.add_trace(go.Scatter(x=sample["wind_speed_ms"], y=sample["power_kw"], mode="markers",
                         marker=dict(size=4, color=lib.MID, opacity=0.35), name="Hourly reading"))
binned = (gen.dropna(subset=["wind_speed_ms", "power_kw"])
          .assign(ws_bin=lambda x: x["wind_speed_ms"].round())
          .groupby("ws_bin")["power_kw"].mean())
fig.add_trace(go.Scatter(x=binned.index, y=binned.values, mode="lines+markers",
                         line=dict(color=lib.DARK, width=3), name="Mean curve"))
fig.add_vline(x=3, line=dict(color="#999", dash="dot"), annotation_text="cut-in")
fig.add_vline(x=12, line=dict(color="#999", dash="dot"), annotation_text="rated")
fig.add_vline(x=25, line=dict(color=lib.RED, dash="dot"), annotation_text="cut-out")
fig.update_xaxes(title="Wind speed (m/s)")
fig.update_yaxes(title="Power output (kW)")
st.plotly_chart(lib.style_fig(fig, height=380), use_container_width=True)
st.caption("Below cut-in (3 m/s) no power is produced; output plateaus at rated "
           "speed (12 m/s); the turbine shuts down above cut-out (25 m/s) for safety.")
