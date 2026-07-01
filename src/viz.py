"""Generate the analytical figures from the real pipeline outputs.

Reads the feature tables, forecasts and anomaly flags produced by the pipeline
and writes report-styled PNGs into outputs/figures/. These are the charts shown
in the dashboard and the deliverables.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from . import config as C
from .storage import connect

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": "#444", "axes.linewidth": 0.8, "axes.grid": True,
    "grid.color": C.GRID, "grid.linewidth": 0.6, "axes.titlesize": 12,
    "axes.titleweight": "bold", "figure.dpi": 150, "savefig.dpi": 150,
    "savefig.bbox": "tight"})


def _con():
    return connect()


def fig_load_profile():
    con = _con()
    df = pd.read_sql("SELECT time, active_power_kwh FROM consumption", con); con.close()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["hour"] = df["time"].dt.hour
    df["we"] = (df["time"].dt.dayofweek >= 5)
    prof = df.groupby(["hour", "we"])["active_power_kwh"].mean().unstack()
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.plot(prof.index, prof[False], color=C.DARK, lw=2.2, marker="o", ms=3, label="Weekday")
    ax.plot(prof.index, prof[True], color=C.ORANGE, lw=2.0, marker="s", ms=3, label="Weekend")
    ax.fill_between(prof.index, prof[False], color=C.DARK, alpha=0.07)
    ax.set_xlabel("Hour of day (UTC)"); ax.set_ylabel("Mean active power (kW)")
    ax.set_title("Average Hourly Load Profile"); ax.set_xticks(range(0, 24, 3)); ax.legend(frameon=False)
    fig.savefig(C.FIGS / "load_profile.png"); plt.close(fig)


def fig_forecast():
    fc = pd.read_csv(C.OUTPUTS / "forecasts.csv", parse_dates=["time"]).tail(168)
    fig, ax = plt.subplots(figsize=(7.4, 3.3))
    ax.plot(fc["time"], fc["actual"], color="#222", lw=1.8, label="Actual")
    if "Ridge regression" in fc:
        ax.plot(fc["time"], fc["Ridge regression"], color=C.ORANGE, lw=1.1, ls="--", label="Ridge")
    neural = "MLP neural net" if "MLP neural net" in fc else fc.columns[-1]
    ax.plot(fc["time"], fc[neural], color=C.DARK, lw=1.5, label=neural)
    ax.set_ylabel("Active power (kW)"); ax.set_title("Forecast vs Actual — Final Test Week")
    ax.legend(frameon=False, ncol=3, loc="upper center"); fig.autofmt_xdate()
    fig.savefig(C.FIGS / "forecast.png"); plt.close(fig)


def fig_metrics():
    s = pd.read_csv(C.OUTPUTS / "evaluation_summary.csv")
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = np.arange(len(s)); w = 0.38
    ax.bar(x - w / 2, s["MAE_kW"], w, color=C.DARK, label="MAE (kW)")
    ax.bar(x + w / 2, s["RMSE_kW"], w, color=C.LIGHT, label="RMSE (kW)")
    for i, r in s.iterrows():
        ax.text(i - w / 2, r["MAE_kW"] + 0.004, f"{r['MAE_kW']:.2f}", ha="center", fontsize=8)
        ax.text(i + w / 2, r["RMSE_kW"] + 0.004, f"{r['RMSE_kW']:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(s["model"], rotation=12, ha="right")
    ax.set_ylabel("Error (kW)"); ax.set_title("Model Error Comparison (60-day hold-out)"); ax.legend(frameon=False)
    fig.savefig(C.FIGS / "model_metrics.png"); plt.close(fig)


def fig_anomaly():
    a = pd.read_csv(C.OUTPUTS / "anomaly_flags.csv", parse_dates=["time"])
    fl = np.where(a["is_anomaly"].values)[0]
    center = fl[len(fl) // 3] if len(fl) else len(a) // 2
    seg = a.iloc[max(0, center - 360): center + 360]
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.plot(seg["time"], seg["value"], color=C.DARK, lw=0.9)
    an = seg[seg["is_anomaly"]]
    ax.scatter(an["time"], an["value"], color=C.RED, s=26, zorder=5, label="Flagged anomaly")
    ax.set_ylabel("Active power (kW)"); ax.set_title("Anomaly Detection — Robust z-score + Persistence")
    ax.legend(frameon=False); fig.autofmt_xdate()
    fig.savefig(C.FIGS / "anomaly.png"); plt.close(fig)


def fig_load_temp():
    con = _con(); d = pd.read_sql("SELECT * FROM consumption_daily", con); con.close()
    d = d.dropna(subset=["temp_c"])
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.scatter(d["temp_c"], d["total_kwh"], s=8, color=C.MID, alpha=0.35, edgecolor="none")
    b = np.polyfit(d["temp_c"], d["total_kwh"], 1)
    xs = np.linspace(d["temp_c"].min(), d["temp_c"].max(), 100)
    ax.plot(xs, np.polyval(b, xs), color=C.DARK, lw=2.2)
    r = d[["temp_c", "total_kwh"]].corr().iloc[0, 1]
    ax.set_xlabel("Daily mean temperature (°C)"); ax.set_ylabel("Daily consumption (kWh)")
    ax.set_title(f"Daily Consumption vs Temperature  (r = {r:.2f})")
    fig.savefig(C.FIGS / "load_temp.png"); plt.close(fig)


def fig_capacity_factor():
    con = _con(); g = pd.read_sql("SELECT * FROM generation_daily", con); con.close()
    g["day"] = pd.to_datetime(g["day"], utc=True)
    cf = g.groupby(g["day"].dt.month)["capacity_factor"].mean() * 100
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.bar(cf.index, cf.values, color=C.DARK, edgecolor="white", width=0.7)
    ax.set_xlabel("Month"); ax.set_ylabel("Mean capacity factor (%)")
    ax.set_title("Wind Capacity Factor by Month"); ax.set_xticks(range(1, 13))
    fig.savefig(C.FIGS / "capacity_factor.png"); plt.close(fig)


def build_all():
    fig_load_profile(); fig_forecast(); fig_metrics()
    fig_anomaly(); fig_load_temp(); fig_capacity_factor()


def main():
    print("[viz] rendering figures ...")
    build_all()
    print(f"[viz] figures written to {C.FIGS.relative_to(C.ROOT)}/")


if __name__ == "__main__":
    main()
