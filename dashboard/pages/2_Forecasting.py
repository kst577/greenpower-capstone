"""Forecasting page — model comparison, forecast vs actual, residual analysis."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import lib

lib.setup_page("Forecasting", "📈")
lib.sidebar()
if not lib.require_data():
    st.stop()

lib.hero("Demand Forecasting",
         "Predicting next-hour household demand on a 60-day chronological hold-out — "
         "from a seasonal baseline to a neural network.")

mdl = lib.stat("model_stats.json")
summary = lib.csv("evaluation_summary.csv")
fc = lib.csv("forecasts.csv")
if fc.empty or summary.empty:
    st.error("Forecast outputs not found. Run the pipeline first.")
    st.stop()
fc["time"] = pd.to_datetime(fc["time"], utc=True)

model_cols = [c for c in fc.columns if c not in ("time", "actual")]

# ---- KPIs ----------------------------------------------------------------
best = mdl.get("best_model", "—")
k = st.columns(4)
lib.kpi(k[0], "Best model", best)
lib.kpi(k[1], "Best MAPE", f"{mdl.get('best_mape','—')}%",
        f"↓{mdl.get('improve_vs_baseline_pct','—')}% RMSE vs baseline")
lib.kpi(k[2], "Train / Test hours",
        f"{mdl.get('train_hours','—'):,} / {mdl.get('test_hours','—'):,}"
        if isinstance(mdl.get("train_hours"), int) else "—")
lib.kpi(k[3], "Hold-out split", str(mdl.get("split_date", "—")))

st.markdown("")

# ---- model selector ------------------------------------------------------
chosen = st.multiselect("Models to display", model_cols, default=model_cols)

# ---- row 1: improvement bar + leaderboard -------------------------------
c1, c2 = st.columns([1, 1.1])

with c1:
    st.markdown("#### Error reduction across models")
    s = summary.copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=s["model"], y=s["MAPE_pct"],
                         marker_color=[lib.MODEL_COLORS.get(m, lib.MID) for m in s["model"]],
                         text=[f"{v:.1f}%" for v in s["MAPE_pct"]], textposition="outside"))
    fig.update_yaxes(title="MAPE (%)", range=[0, s["MAPE_pct"].max() * 1.2])
    st.plotly_chart(lib.style_fig(fig, legend=False), use_container_width=True)

with c2:
    st.markdown("#### Model leaderboard")
    s = summary.sort_values("RMSE_kW").reset_index(drop=True)
    s.index = s.index + 1
    styled = (s.style
              .format({"MAE_kW": "{:.3f}", "RMSE_kW": "{:.3f}", "MAPE_pct": "{:.1f}"})
              .background_gradient(cmap="Greens_r", subset=["MAE_kW", "RMSE_kW", "MAPE_pct"]))
    st.dataframe(styled, use_container_width=True)
    st.caption("Lower is better · ranked by RMSE. "
               f"Winner: **{best}**.")

# ---- row 2: forecast vs actual ------------------------------------------
st.markdown("#### Forecast vs actual")
window = st.radio("Window", ["Final week (168 h)", "Full hold-out (60 days)"],
                  horizontal=True)
view = fc.tail(168) if window.startswith("Final") else fc
fig = go.Figure()
fig.add_trace(go.Scatter(x=view["time"], y=view["actual"], name="Actual",
                         line=dict(color=lib.MODEL_COLORS["actual"], width=2.4)))
for m in chosen:
    fig.add_trace(go.Scatter(x=view["time"], y=view[m], name=m,
                             line=dict(color=lib.MODEL_COLORS.get(m, lib.MID),
                                       width=1.6,
                                       dash="dash" if m == "Ridge regression" else "solid")))
fig.update_yaxes(title="Active power (kW)")
st.plotly_chart(lib.style_fig(fig, height=380), use_container_width=True)

# ---- row 3: residuals + scatter -----------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.markdown("#### Prediction error distribution")
    fig = go.Figure()
    for m in chosen:
        resid = (fc[m] - fc["actual"]).dropna()
        fig.add_trace(go.Histogram(x=resid, name=m, opacity=0.55, nbinsx=40,
                                   marker_color=lib.MODEL_COLORS.get(m, lib.MID)))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Prediction error (kW)")
    fig.update_yaxes(title="Count")
    st.plotly_chart(lib.style_fig(fig), use_container_width=True)

with c4:
    st.markdown("#### Predicted vs actual")
    fig = go.Figure()
    lim = [fc["actual"].min(), fc["actual"].max()]
    fig.add_trace(go.Scatter(x=lim, y=lim, mode="lines", name="Perfect",
                             line=dict(color="#999", width=1.5, dash="dot")))
    for m in chosen:
        sub = fc[["actual", m]].dropna()
        fig.add_trace(go.Scatter(x=sub["actual"], y=sub[m], mode="markers", name=m,
                                 marker=dict(size=4, opacity=0.4,
                                             color=lib.MODEL_COLORS.get(m, lib.MID))))
    fig.update_xaxes(title="Actual (kW)")
    fig.update_yaxes(title="Predicted (kW)")
    st.plotly_chart(lib.style_fig(fig), use_container_width=True)

# ---- download ------------------------------------------------------------
st.download_button("⬇ Download forecasts.csv",
                   fc.to_csv(index=False).encode(), "forecasts.csv", "text/csv")
