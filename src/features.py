"""Week 4 — feature engineering.

Builds the analytical feature tables on top of the storage layer: daily/monthly
rollups, peak-load statistics, calendar + cyclical encodings, lag/rolling
predictors, and the weather-joined degree-hour features. Feature tables are
written back into the database and exported to CSV. Correlation statistics are
saved for the report.

The equivalent TimescaleDB continuous-aggregate / view definitions are in
db/migrations/004_continuous_aggregates.sql and 005_feature_views.sql.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from . import config as C
from .storage import connect


def _read(con, table) -> pd.DataFrame:
    df = pd.read_sql(f"SELECT * FROM {table}", con)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time")


def build_features() -> dict:
    con = connect()
    cons = _read(con, "consumption")
    gen = _read(con, "generation")
    wx = _read(con, "weather")

    # ---------- calendar + cyclical + lag/rolling (hourly) ----------
    f = cons.copy()
    f["hour"] = f.index.hour
    f["dow"] = f.index.dayofweek
    f["month"] = f.index.month
    f["is_weekend"] = (f["dow"] >= 5).astype(int)
    seasons = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring",
               5: "spring", 6: "summer", 7: "summer", 8: "summer",
               9: "autumn", 10: "autumn", 11: "autumn"}
    f["season"] = f["month"].map(seasons)
    f["hour_sin"] = np.sin(2 * np.pi * f["hour"] / 24)
    f["hour_cos"] = np.cos(2 * np.pi * f["hour"] / 24)
    f["doy_sin"] = np.sin(2 * np.pi * f.index.dayofyear / 365)
    f["doy_cos"] = np.cos(2 * np.pi * f.index.dayofyear / 365)
    for lag in C.LAGS:
        f[f"lag_{lag}h"] = f["active_power_kwh"].shift(lag)
    f["roll_24h_mean"] = f["active_power_kwh"].rolling(C.ROLL_WINDOW).mean()
    f["roll_24h_std"] = f["active_power_kwh"].rolling(C.ROLL_WINDOW).std()

    # ---------- weather join + degree-hours ----------
    wxj = wx[wx["station_id"] == 1][["tavg_c", "tmax_c", "tmin_c", "wind_speed_ms", "precip_mm"]]
    f = f.join(wxj, how="left")
    f["hdh"] = np.clip(C.HDD_BASE_C - f["tavg_c"], 0, None)
    f["cdh"] = np.clip(f["tavg_c"] - C.CDD_BASE_C, 0, None)

    # ---------- daily rollup ----------
    daily = cons["active_power_kwh"].resample("D").agg(
        total_kwh="sum", mean_kw="mean", peak_kw="max", min_kw="min")
    daily["peak_hour"] = cons["active_power_kwh"].resample("D").apply(
        lambda s: int(s.idxmax().hour) if len(s) else np.nan)
    daily["par"] = daily["peak_kw"] / daily["mean_kw"]
    daily["load_factor"] = daily["mean_kw"] / daily["peak_kw"]
    daily["temp_c"] = f["tavg_c"].resample("D").mean()
    daily["hdh"] = f["hdh"].resample("D").sum()
    for c in ("sub_kitchen_kwh", "sub_laundry_kwh", "sub_climate_kwh"):
        daily[c] = cons[c].resample("D").sum()

    # ---------- monthly rollup ----------
    monthly = cons["active_power_kwh"].resample("MS").agg(
        total_kwh="sum", mean_kw="mean", peak_kw="max")

    # ---------- generation rollup ----------
    gdaily = gen["power_kw"].resample("D").agg(gen_kwh="sum", mean_kw="mean", peak_kw="max")
    gdaily["capacity_factor"] = gdaily["mean_kw"] / C.RATED_KW

    # ---------- persist ----------
    def write(df, name, index_label="time"):
        out = df.reset_index().rename(columns={df.index.name or "index": index_label})
        out.to_sql(name, con, if_exists="replace", index=False)
        out.to_csv(C.CLEANED / f"{name}.csv", index=False)

    write(f, "consumption_features_hourly")
    write(daily, "consumption_daily", "day")
    write(monthly, "consumption_monthly", "month")
    write(gdaily, "generation_daily", "day")
    con.commit()
    con.close()

    # ---------- correlation statistics ----------
    d = daily.dropna(subset=["temp_c"])
    stats = {
        "cons_hourly_rows": int(len(f)),
        "cons_daily_rows": int(len(daily)),
        "cons_monthly_rows": int(len(monthly)),
        "gen_daily_rows": int(len(gdaily)),
        "par_mean": round(float(daily["par"].mean()), 2),
        "load_factor_mean": round(float(daily["load_factor"].mean()), 3),
        "median_peak_hour": int(daily["peak_hour"].median()),
        "evening_peak_share": round(float(daily["peak_hour"].between(17, 21).mean()) * 100, 1),
        "daily_total_mean_kwh": round(float(daily["total_kwh"].mean()), 1),
        "r_load_temp_hourly": round(float(f[["active_power_kwh", "tavg_c"]].dropna().corr().iloc[0, 1]), 3),
        "r_load_temp_daily": round(float(d[["mean_kw", "temp_c"]].corr().iloc[0, 1]), 3),
        "r_load_hdh_daily": round(float(d[["total_kwh", "hdh"]].corr().iloc[0, 1]), 3),
        "wind_cf_mean": round(float(gdaily["capacity_factor"].mean()) * 100, 1),
    }
    (C.OUTPUTS / "feature_stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main():
    print("[features] building feature tables ...")
    s = build_features()
    print(f"[features] hourly {s['cons_hourly_rows']:,} | daily {s['cons_daily_rows']:,} | "
          f"monthly {s['cons_monthly_rows']} | gen-daily {s['gen_daily_rows']:,}")
    print(f"[features] PAR mean {s['par_mean']} | evening-peak share {s['evening_peak_share']}% | "
          f"r(load,HDH)={s['r_load_hdh_daily']} | wind CF {s['wind_cf_mean']}%")


if __name__ == "__main__":
    main()
