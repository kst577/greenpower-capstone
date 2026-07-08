"""Data Quality page — cleaning report, completeness, database inventory."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import lib

lib.setup_page("Data Quality", "🧹")
lib.sidebar()
if not lib.require_data():
    st.stop()

lib.hero("Data Quality & Cleaning",
         "Week-2 cleaning results — spike removal, gap imputation and hourly-grid "
         "alignment across the three source datasets.")

clean = lib.stat("cleaning_report.json")
if not clean:
    st.error("Cleaning report not found. Run the pipeline first.")
    st.stop()

labels = {"consumption": "Consumption (UCI)", "generation": "Generation (SCADA)",
          "weather": "Weather (NOAA)"}
icons = {"consumption": "🔌", "generation": "🌬️", "weather": "🌡️"}

# ---- dataset cards -------------------------------------------------------
st.markdown("### Cleaning summary by dataset")
cols = st.columns(len(clean))
for col, (key, r) in zip(cols, clean.items()):
    with col:
        comp = r.get("mean_completeness", 0)
        st.markdown(
            f"""<div class="gp-card">
            <div style="font-size:16px;font-weight:800;color:{lib.DARK}">
            {icons.get(key,'')} {labels.get(key, key)}</div>
            <div style="margin-top:6px;font-size:13px;color:{lib.MUTED}">
            Clean rows: <b>{r.get('clean_rows',0):,}</b></div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.progress(min(comp, 1.0), text=f"Completeness {comp*100:.2f}%")
        m = st.columns(2)
        m[0].metric("Spikes removed", r.get("spikes_removed", 0))
        m[1].metric("Gaps imputed", r.get("gaps_imputed", 0))

st.markdown("")

# ---- raw vs clean funnel + completeness bar -----------------------------
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Rows: raw → cleaned grid")
    rows_df = pd.DataFrame([
        {"Dataset": labels.get(k, k), "Raw rows": v.get("raw_rows", 0),
         "Clean rows": v.get("clean_rows", 0)}
        for k, v in clean.items()
    ])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=rows_df["Dataset"], y=rows_df["Raw rows"], name="Raw",
                         marker_color=lib.LIGHT))
    fig.add_trace(go.Bar(x=rows_df["Dataset"], y=rows_df["Clean rows"], name="Cleaned",
                         marker_color=lib.DARK))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Row count")
    st.plotly_chart(lib.style_fig(fig), use_container_width=True)

with c2:
    st.markdown("#### Mean completeness")
    comp_df = pd.DataFrame([
        {"Dataset": labels.get(k, k), "Completeness": v.get("mean_completeness", 0) * 100}
        for k, v in clean.items()
    ])
    fig = go.Figure(go.Bar(x=comp_df["Completeness"], y=comp_df["Dataset"],
                           orientation="h", marker_color=lib.MID,
                           text=[f"{v:.2f}%" for v in comp_df["Completeness"]],
                           textposition="outside"))
    fig.update_xaxes(title="Completeness (%)", range=[95, 101])
    st.plotly_chart(lib.style_fig(fig, legend=False), use_container_width=True)

# ---- database inventory --------------------------------------------------
st.markdown("#### Database inventory")
tables = lib.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
inv = []
for t in tables["name"]:
    try:
        n = lib.query(f"SELECT COUNT(*) AS n FROM {t}")["n"].iloc[0]
        inv.append({"Table": t, "Rows": f"{int(n):,}"})
    except Exception:
        continue
st.dataframe(pd.DataFrame(inv), use_container_width=True, hide_index=True)

# ---- cleaning detail table ----------------------------------------------
st.markdown("#### Detailed cleaning report")
detail = pd.DataFrame([
    {"Dataset": labels.get(k, k), "Raw rows": v.get("raw_rows"),
     "Grid rows": v.get("grid_rows"), "Spikes removed": v.get("spikes_removed"),
     "Gaps imputed": v.get("gaps_imputed"), "Long gaps masked": v.get("long_gaps_masked"),
     "Clean rows": v.get("clean_rows"),
     "Completeness": f"{v.get('mean_completeness',0)*100:.2f}%"}
    for k, v in clean.items()
])
st.dataframe(detail, use_container_width=True, hide_index=True)
