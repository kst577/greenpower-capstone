"""Shared helpers for the GreenPower Streamlit dashboard.

Central place for the theme, cached data loaders, KPI helpers and Plotly
styling so every page has a consistent look and reads the same pipeline
outputs (SQLite database + JSON/CSV stat files).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "greenpower.db"
OUTPUTS = ROOT / "outputs"
FIGS = OUTPUTS / "figures"

# --------------------------------------------------------------------------
# Brand palette (matches the pipeline reports / src/config.py)
# --------------------------------------------------------------------------
DARK = "#1f7045"      # primary dark green
MID = "#3f9b6e"       # mid green
LIGHT = "#a9cdb6"     # light green
ORANGE = "#d9744f"    # accent orange
RED = "#c0392b"       # anomaly red
GRID = "#e3e8e4"
INK = "#1a2b22"
MUTED = "#5a6b60"

MODEL_COLORS = {
    "actual": "#111827",
    "Actual": "#111827",
    "Seasonal-naive": "#b9c4bd",
    "Ridge regression": ORANGE,
    "MLP neural net": DARK,
    "LSTM (Keras)": "#2563eb",
}

TEAM = [
    ("Harshit Nirmal Jain", "G25AI1021"),
    ("K R Devika", "G25AI1022"),
    ("Kartik Dadhich", "G25AI1023"),
    ("Kirtiman Sarangi", "G25AI1024"),
    ("Kollipara Teja", "G25AI1025"),
]


# --------------------------------------------------------------------------
# Page setup + global CSS
# --------------------------------------------------------------------------
def setup_page(title: str, icon: str = "⚡") -> None:
    st.set_page_config(
        page_title=f"GreenPower · {title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        f"""
        <style>
          .stApp {{ background: #f4f7f5; }}
          section[data-testid="stSidebar"] {{ background: #14392a; }}
          section[data-testid="stSidebar"] * {{ color: #dcece3 !important; }}
          /* GreenPower brand heading pinned to the very top, above page nav */
          div[data-testid="stSidebarNav"]::before {{
              content: "GreenPower \\26A1";
              display: block; font-size: 23px; font-weight: 800;
              color: #ffffff; letter-spacing: .3px;
              padding: 14px 16px 8px 16px;
          }}
          section[data-testid="stSidebar"] .gp-member {{
              font-size: 13px; margin: 3px 0; color: #eaf4ee !important;
          }}
          section[data-testid="stSidebar"] .gp-roll {{
              color: {LIGHT} !important; font-weight: 600; margin-left: 6px;
          }}
          section[data-testid="stSidebar"] .gp-copy {{
              font-size: 11px; line-height: 1.5; color: #7fa792 !important;
              margin-top: 10px;
          }}
          /* keep code-styled roll numbers readable if any remain */
          section[data-testid="stSidebar"] code {{
              background: rgba(169,205,182,.15); color: {LIGHT} !important;
          }}
          .block-container {{ padding-top: 2.2rem; max-width: 1500px; }}
          h1, h2, h3, h4 {{ color: {INK}; }}
          .gp-hero {{
              background: linear-gradient(115deg, {DARK} 0%, #2c8c59 55%, {MID} 100%);
              color: #fff; padding: 26px 30px; border-radius: 16px;
              box-shadow: 0 8px 24px rgba(31,112,69,.22); margin-bottom: 6px;
          }}
          .gp-hero h1 {{ color:#fff; margin:0; font-size: 30px; font-weight: 800; }}
          .gp-hero p {{ color:#d9efe4; margin: 6px 0 0; font-size: 14px; opacity:.92; }}
          .gp-kpi {{
              background:#fff; border:1px solid {GRID}; border-radius:14px;
              padding:16px 18px; height:100%;
              box-shadow:0 2px 6px rgba(20,57,42,.05);
          }}
          .gp-kpi .l {{ font-size:12px; color:{MUTED}; font-weight:600;
              text-transform:uppercase; letter-spacing:.4px; }}
          .gp-kpi .v {{ font-size:28px; font-weight:800; color:{DARK}; line-height:1.15; margin-top:4px; }}
          .gp-kpi .d {{ font-size:12px; color:{MID}; margin-top:2px; font-weight:600; }}
          .gp-tag {{ display:inline-block; background:{LIGHT}; color:{DARK};
              padding:2px 10px; border-radius:20px; font-size:12px; font-weight:700; }}
          .gp-card {{ background:#fff; border:1px solid {GRID}; border-radius:14px;
              padding:18px 20px; box-shadow:0 2px 6px rgba(20,57,42,.05); }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> None:
    with st.sidebar:
        st.caption("Energy Consumption Analytics")
        st.markdown("---")
        st.markdown("**Capstone · Group 5**")
        st.markdown("IIT Jodhpur")
        run_time = _pipeline_run_time()
        if run_time:
            st.caption(f"Pipeline run: {run_time}")
        st.markdown("---")
        with st.expander("Team"):
            for name, roll in TEAM:
                st.markdown(
                    f'<div class="gp-member">{name}'
                    f'<span class="gp-roll">{roll}</span></div>',
                    unsafe_allow_html=True,
                )
        st.markdown("---")
        st.caption("Data: UCI household · Kaggle SCADA wind · NOAA weather")
        st.markdown(
            '<div class="gp-copy">© 2026 GreenPower Utilities<br>'
            'Group 5 · IIT Jodhpur · All rights reserved.</div>',
            unsafe_allow_html=True,
        )


def _pipeline_run_time() -> str | None:
    p = OUTPUTS / "model_stats.json"
    if p.exists():
        ts = datetime.fromtimestamp(p.stat().st_mtime)
        return ts.strftime("%d %b %Y, %H:%M")
    return None


# --------------------------------------------------------------------------
# Cached data loaders
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    con = sqlite3.connect(DB)
    try:
        df = pd.read_sql(sql, con)
    finally:
        con.close()
    return df


@st.cache_data(show_spinner=False)
def stat(name: str) -> dict:
    p = OUTPUTS / name
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data(show_spinner=False)
def csv(name: str) -> pd.DataFrame:
    p = OUTPUTS / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def db_exists() -> bool:
    return DB.exists()


def require_data() -> bool:
    """Guard used at the top of every page."""
    if not db_exists():
        st.error(
            "No pipeline outputs found. Run the pipeline first:\n\n"
            "```bash\nuv run python run_pipeline.py\n```"
        )
        return False
    return True


# --------------------------------------------------------------------------
# UI helpers
# --------------------------------------------------------------------------
def kpi(col, label: str, value: str, delta: str | None = None) -> None:
    delta_html = f'<div class="d">{delta}</div>' if delta else ""
    col.markdown(
        f'<div class="gp-kpi"><div class="l">{label}</div>'
        f'<div class="v">{value}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="gp-hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif", size=12, color=INK),
        title=dict(font=dict(size=15, color=INK)),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
        )
        if legend
        else dict(),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig
