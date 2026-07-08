"""Consumption Analysis page — load profiles, heatmap, weather relationship."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import lib

lib.setup_page("Consumption", "🔌")
lib.sidebar()
if not lib.require_data():
    st.stop()

lib.hero("Consumption Analysis",
         "Household electricity demand patterns — daily rhythm, weekly structure "
         "and the effect of temperature.")

# ---- load data -----------------------------------------------------------
feat = lib.query(
    "SELECT time, active_power_kwh, hour, dow, month, is_weekend, season, "
    "tavg_c, hdh, cdh, sub_kitchen_kwh, sub_laundry_kwh, sub_climate_kwh "
    "FROM consumption_features_hourly"
)
feat["time"] = pd.to_datetime(feat["time"], utc=True)
daily = lib.query("SELECT * FROM consumption_daily")
daily["day"] = pd.to_datetime(daily["day"], utc=True)

# ---- filters -------------------------------------------------------------
min_d, max_d = feat["time"].min().date(), feat["time"].max().date()
fc1, fc2 = st.columns([2, 1])
with fc1:
    dr = st.slider("Date range", min_value=min_d, max_value=max_d,
                   value=(min_d, max_d), format="MMM YYYY")
with fc2:
    day_type = st.radio("Day type", ["All", "Weekday", "Weekend"], horizontal=True)

mask = (feat["time"].dt.date >= dr[0]) & (feat["time"].dt.date <= dr[1])
if day_type == "Weekday":
    mask &= feat["is_weekend"] == 0
elif day_type == "Weekend":
    mask &= feat["is_weekend"] == 1
f = feat[mask]
dmask = (daily["day"].dt.date >= dr[0]) & (daily["day"].dt.date <= dr[1])
d = daily[dmask]

# ---- KPIs for selection --------------------------------------------------
k = st.columns(4)
lib.kpi(k[0], "Hours in view", f"{len(f):,}")
lib.kpi(k[1], "Mean load", f"{f['active_power_kwh'].mean():.3f} kW" if len(f) else "—")
lib.kpi(k[2], "Peak load", f"{f['active_power_kwh'].max():.2f} kW" if len(f) else "—")
lib.kpi(k[3], "Avg temperature",
        f"{f['tavg_c'].mean():.1f} °C" if len(f) and f['tavg_c'].notna().any() else "—")

st.markdown("")

# ---- row 1: load profile + heatmap --------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Average hourly load profile")
    prof = feat[mask].copy()
    wd = prof[prof["is_weekend"] == 0].groupby("hour")["active_power_kwh"].mean()
    we = prof[prof["is_weekend"] == 1].groupby("hour")["active_power_kwh"].mean()
    fig = go.Figure()
    if not wd.empty:
        fig.add_trace(go.Scatter(x=wd.index, y=wd.values, name="Weekday",
                                 line=dict(color=lib.DARK, width=2.5), mode="lines+markers"))
    if not we.empty:
        fig.add_trace(go.Scatter(x=we.index, y=we.values, name="Weekend",
                                 line=dict(color=lib.ORANGE, width=2.2), mode="lines+markers"))
    fig.update_xaxes(title="Hour of day", dtick=3)
    fig.update_yaxes(title="Mean active power (kW)")
    st.plotly_chart(lib.style_fig(fig), use_container_width=True)

with c2:
    st.markdown("#### Consumption heatmap · hour × weekday")
    piv = (f.groupby(["dow", "hour"])["active_power_kwh"].mean()
           .reset_index().pivot(index="dow", columns="hour", values="active_power_kwh"))
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    piv = piv.reindex(range(7))
    fig = px.imshow(piv, color_continuous_scale="Greens", aspect="auto",
                    labels=dict(x="Hour of day", y="", color="kW"))
    fig.update_yaxes(tickvals=list(range(7)), ticktext=days)
    fig.update_xaxes(dtick=3)
    st.plotly_chart(lib.style_fig(fig, legend=False), use_container_width=True)

# ---- row 2: temperature scatter + monthly -------------------------------
c3, c4 = st.columns(2)

with c3:
    st.markdown("#### Daily consumption vs temperature")
    dd = d.dropna(subset=["temp_c", "total_kwh"])
    if len(dd) > 2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dd["temp_c"], y=dd["total_kwh"], mode="markers",
                                 marker=dict(size=6, color=lib.MID, opacity=0.45),
                                 name="Day"))
        b = np.polyfit(dd["temp_c"], dd["total_kwh"], 1)
        xs = np.linspace(dd["temp_c"].min(), dd["temp_c"].max(), 100)
        fig.add_trace(go.Scatter(x=xs, y=np.polyval(b, xs), mode="lines",
                                 line=dict(color=lib.DARK, width=3), name="Trend"))
        r = dd["temp_c"].corr(dd["total_kwh"])
        fig.update_xaxes(title="Daily mean temperature (°C)")
        fig.update_yaxes(title="Daily consumption (kWh)")
        fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper",
                           text=f"<b>r = {r:.2f}</b>", showarrow=False,
                           bgcolor="rgba(255,255,255,.8)", font=dict(color=lib.DARK))
        st.plotly_chart(lib.style_fig(fig), use_container_width=True)
    else:
        st.info("Not enough data in the selected range.")

with c4:
    st.markdown("#### Monthly consumption by season")
    mm = f.copy()
    mm["ym"] = mm["time"].dt.to_period("M").dt.to_timestamp()
    grp = mm.groupby(["ym", "season"])["active_power_kwh"].sum().reset_index()
    season_colors = {"winter": "#2c5f8a", "spring": lib.MID,
                     "summer": lib.ORANGE, "autumn": "#b07d3f"}
    fig = px.bar(grp, x="ym", y="active_power_kwh", color="season",
                 color_discrete_map=season_colors,
                 labels=dict(ym="Month", active_power_kwh="Consumption (kWh)", season="Season"))
    st.plotly_chart(lib.style_fig(fig), use_container_width=True)

# ---- row 3: sub-meter breakdown -----------------------------------------
st.markdown("#### Appliance sub-meter breakdown (monthly totals)")
sm = f.copy()
sm["ym"] = sm["time"].dt.to_period("M").dt.to_timestamp()
sub = sm.groupby("ym")[["sub_kitchen_kwh", "sub_laundry_kwh", "sub_climate_kwh"]].sum().reset_index()
sub = sub.melt("ym", var_name="circuit", value_name="kwh")
labels = {"sub_kitchen_kwh": "Kitchen", "sub_laundry_kwh": "Laundry", "sub_climate_kwh": "Climate"}
sub["circuit"] = sub["circuit"].map(labels)
fig = px.bar(sub, x="ym", y="kwh", color="circuit",
             color_discrete_map={"Kitchen": lib.ORANGE, "Laundry": lib.LIGHT, "Climate": lib.DARK},
             labels=dict(ym="Month", kwh="Energy (kWh)", circuit="Circuit"))
st.plotly_chart(lib.style_fig(fig, height=320), use_container_width=True)
