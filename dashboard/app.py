"""Interactive Streamlit dashboard (production/interactive view).

Reads the same SQLite database and outputs the pipeline produced. Run with:
    streamlit run dashboard/app.py

Requires: streamlit, plotly  (pip install streamlit plotly).
The static, dependency-free equivalent is dashboard/build_static.py.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "greenpower.db"

st.set_page_config(page_title="GreenPower Analytics", layout="wide")
st.title("GreenPower Utilities — Energy Analytics Dashboard")
st.caption("Group 5 · IIT Jodhpur · built on the Week 4 feature layer")


@st.cache_data
def q(sql):
    con = sqlite3.connect(DB)
    df = pd.read_sql(sql, con)
    con.close()
    return df


daily = q("SELECT * FROM consumption_daily")
daily["day"] = pd.to_datetime(daily["day"])
feat = q("SELECT time, active_power_kwh, hour, is_weekend FROM consumption_features_hourly")
feat["time"] = pd.to_datetime(feat["time"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg daily consumption", f"{daily['total_kwh'].mean():.1f} kWh")
c2.metric("Peak-to-average ratio", f"{daily['par'].mean():.2f}")
c3.metric("Mean daily peak", f"{daily['peak_kw'].mean():.2f} kW")
c4.metric("Median peak hour", f"{int(daily['peak_hour'].median())}:00")

left, right = st.columns(2)
with left:
    st.subheader("Daily consumption trend")
    st.plotly_chart(px.line(daily, x="day", y="total_kwh"), use_container_width=True)
    st.subheader("Load profile by hour")
    prof = feat.groupby("hour")["active_power_kwh"].mean().reset_index()
    st.plotly_chart(px.bar(prof, x="hour", y="active_power_kwh"), use_container_width=True)
with right:
    fc = pd.read_csv(ROOT / "outputs" / "forecasts.csv", parse_dates=["time"]).tail(168)
    st.subheader("Forecast vs actual (final week)")
    st.plotly_chart(px.line(fc, x="time", y=[c for c in fc.columns if c != "time"]),
                    use_container_width=True)
    st.subheader("Model evaluation")
    st.dataframe(pd.read_csv(ROOT / "outputs" / "evaluation_summary.csv"), use_container_width=True)
