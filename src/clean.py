"""Week 2 — cleaning and preprocessing.

Reads the raw datasets, removes sensor spikes, imputes short gaps, aligns every
series to a consistent hourly UTC index, and records a per-hour `completeness`
column (fraction of the hour that survived cleaning). Writes cleaned CSVs and a
cleaning report. This mirrors the checkpointed cleaning pipeline of the Week 2
deliverable.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from . import config as C


def _despike(s: pd.Series, z: float = 6.0) -> pd.Series:
    """Replace values whose robust z-score exceeds `z` with NaN (sensor spikes)."""
    med = s.median()
    mad = (s - med).abs().median() or 1e-9
    robust_z = (s - med).abs() / (1.4826 * mad)
    out = s.copy()
    out[robust_z > z] = np.nan
    return out


def _clean_series(df: pd.DataFrame, value_cols, start, end) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop_duplicates("time").set_index("time").sort_index()

    full = pd.date_range(start, end + " 23:00", freq="h", tz="UTC")
    raw_rows = len(df)

    # spike removal on the primary measurement columns
    spikes = 0
    for c in value_cols:
        before = df[c].notna().sum()
        df[c] = _despike(df[c])
        spikes += before - df[c].notna().sum()

    df = df.reindex(full)                      # align to complete hourly grid
    missing_before = int(df[value_cols[0]].isna().sum())

    # short-gap imputation: interpolate gaps up to 3 hours, leave longer gaps masked
    completeness = df[value_cols[0]].notna().astype(float)
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].interpolate(limit=3, limit_area="inside")
    # completeness: 1.0 where original present, 0.5 where imputed, 0 where still NaN
    completeness = np.where(completeness == 1, 1.0,
                            np.where(df[value_cols[0]].notna(), 0.5, 0.0))
    df["completeness"] = completeness

    # static id columns forward-fill
    for c in ("source_id", "station_id", "source_station"):
        if c in df.columns:
            df[c] = df[c].ffill().bfill()

    # rows still fully missing after imputation are dropped (long masked gaps)
    long_gaps = int(df[value_cols[0]].isna().sum())
    df = df.dropna(subset=[value_cols[0]]).reset_index().rename(columns={"index": "time"})

    report = {
        "raw_rows": int(raw_rows),
        "grid_rows": int(len(full)),
        "spikes_removed": int(spikes),
        "gaps_imputed": int(missing_before - long_gaps),
        "long_gaps_masked": int(long_gaps),
        "clean_rows": int(len(df)),
        "mean_completeness": round(float(df["completeness"].mean()), 4),
    }
    return df, report


def clean_all() -> dict:
    reports = {}

    cons = pd.read_csv(C.RAW / "consumption_raw.csv")
    cons, reports["consumption"] = _clean_series(
        cons, ["active_power_kwh"], C.CONS_START, C.CONS_END)
    cons.to_csv(C.CLEANED / "uci_household_hourly.csv", index=False)

    gen = pd.read_csv(C.RAW / "generation_raw.csv")
    gen, reports["generation"] = _clean_series(
        gen, ["power_kw"], C.GEN_START, C.GEN_END)
    gen.to_csv(C.CLEANED / "scada_wind_hourly.csv", index=False)

    wx = pd.read_csv(C.RAW / "weather_raw.csv")
    wx, reports["weather"] = _clean_series(
        wx, ["tavg_c"], C.WX_START, C.WX_END)
    wx.to_csv(C.CLEANED / "noaa_weather_hourly.csv", index=False)

    (C.OUTPUTS / "cleaning_report.json").write_text(json.dumps(reports, indent=2))
    return reports


def main():
    print("[clean] cleaning raw datasets ...")
    reports = clean_all()
    for name, r in reports.items():
        print(f"[clean] {name:12} {r['clean_rows']:>7,} clean rows "
              f"(spikes removed {r['spikes_removed']}, gaps imputed {r['gaps_imputed']}, "
              f"completeness {r['mean_completeness']})")


if __name__ == "__main__":
    main()
