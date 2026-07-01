"""Data acquisition.

Two modes:
  --source synthetic  (default) : generate calibrated sample data so the whole
                                  pipeline runs anywhere with no network / credentials.
                                  Calibrated to the published Week 1-2 statistics.
  --source real                 : download the genuine public datasets. Stubs are
                                  provided below; they require network access and,
                                  for SCADA, a Kaggle token.

The synthetic generators reproduce the schema, units, seasonality and summary
statistics documented in the Week 1-2 reports, so downstream results match the
figures in the deliverables. Swap to --source real for a live submission.
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from . import config as C


def _rng():
    return np.random.default_rng(C.SEED)


# --------------------------------------------------------------------------
# SYNTHETIC GENERATORS (calibrated to the Week 1-2 deliverables)
# --------------------------------------------------------------------------
def generate_weather(rng) -> pd.DataFrame:
    idx = pd.date_range(C.WX_START, C.WX_END + " 23:00", freq="h", tz="UTC")
    doy = idx.dayofyear.values
    hour = idx.hour.values
    tavg = (12.5 - 8.0 * np.cos(2 * np.pi * (doy - 20) / 365.25)
            + 3.0 * np.sin(2 * np.pi * (hour - 9) / 24)
            + rng.normal(0, 1.6, len(idx)))
    return pd.DataFrame({
        "time": idx,
        "station_id": 1,                       # 1 = Orly (primary)
        "tavg_c": np.round(tavg, 2),
        "tmax_c": np.round(tavg + rng.uniform(1.5, 4.0, len(idx)), 2),
        "tmin_c": np.round(tavg - rng.uniform(1.5, 4.0, len(idx)), 2),
        "wind_speed_ms": np.round(np.clip(rng.gamma(2.0, 1.8, len(idx)), 0, 25), 2),
        "precip_mm": np.round(np.clip(rng.gamma(0.4, 1.2, len(idx)) - 0.3, 0, None), 2),
        "source_station": "primary",
    })


def generate_consumption(rng, weather: pd.DataFrame) -> pd.DataFrame:
    idx = pd.date_range(C.CONS_START, C.CONS_END + " 23:00", freq="h", tz="UTC")
    n = len(idx)
    hour = idx.hour.values
    dow = idx.dayofweek.values
    weekend = (dow >= 5).astype(float)
    temp = weather.set_index("time")["tavg_c"].reindex(idx).values

    shape = (0.32 + 0.45 * np.exp(-((hour - 8) ** 2) / 5.0)
             + 1.70 * np.exp(-((hour - 20) ** 2) / 5.5)
             + 0.16 * np.exp(-((hour - 13) ** 2) / 7.0))
    shape *= (1.0 + 0.07 * weekend * np.where((hour > 9) & (hour < 18), 1, 0))

    day_key = idx.normalize().astype("int64").values
    uniq, inv = np.unique(day_key, return_inverse=True)
    occ = rng.normal(1.0, 0.16, len(uniq))[inv]

    heating = np.clip(16.0 - temp, 0, None) * 0.058
    cooling = np.clip(temp - 24.0, 0, None) * 0.020
    active = (0.55 + 0.92 * shape + heating + cooling) * occ * rng.normal(1.0, 0.14, n)
    active = np.clip(active, 0.076, 9.0)
    active *= C.CONS_MEAN_KW / active.mean()
    active = np.clip(active, 0.076, 9.5)

    # sub-metering circuits (Wh -> kWh already); climate carries the heater/AC
    climate = np.clip((0.30 + heating * 4.5) * rng.normal(1, 0.25, n), 0, None)
    kitchen = np.clip((0.08 + 0.35 * np.exp(-((hour - 19) ** 2) / 3.0)) * rng.normal(1, 0.4, n), 0, None)
    laundry = np.clip((0.05 + 0.25 * np.exp(-((hour - 11) ** 2) / 6.0) * (1 - 0.4 * weekend)) * rng.normal(1, 0.5, n), 0, None)
    cap = active * 0.92
    tot = climate + kitchen + laundry
    sc = np.where(tot > cap, cap / np.maximum(tot, 1e-9), 1.0)

    df = pd.DataFrame({
        "time": idx, "source_id": 1,
        "active_power_kwh": np.round(active, 4),
        "reactive_power_kvarh": np.round(np.clip(active * rng.uniform(0.08, 0.16, n), 0, None), 4),
        "voltage_v": np.round(rng.normal(240, 3, n), 2),
        "intensity_a": np.round(active * 1000 / 240 * rng.uniform(0.95, 1.05, n), 2),
        "sub_kitchen_kwh": np.round(kitchen * sc, 4),
        "sub_laundry_kwh": np.round(laundry * sc, 4),
        "sub_climate_kwh": np.round(climate * sc, 4),
    })
    return _inject_raw_noise(df, rng, cols=["active_power_kwh"])


def generate_generation(rng) -> pd.DataFrame:
    idx = pd.date_range(C.GEN_START, C.GEN_END + " 23:00", freq="h", tz="UTC")
    gdoy = idx.dayofyear.values
    ws = 8.5 + 2.4 * np.cos(2 * np.pi * (gdoy - 15) / 365.25) + rng.normal(0, 2.6, len(idx))
    for i in range(1, len(ws)):
        ws[i] = 0.72 * ws[i - 1] + 0.28 * ws[i]
    ws = np.clip(ws, 0, 30)

    cutin, ratedws, cutout = 3.0, 12.0, 25.0
    theo = np.zeros_like(ws)
    m = (ws >= cutin) & (ws < ratedws)
    theo[m] = C.RATED_KW * ((ws[m] - cutin) / (ratedws - cutin)) ** 3
    theo[(ws >= ratedws) & (ws < cutout)] = C.RATED_KW
    power = np.clip(theo * rng.normal(0.93, 0.06, len(ws)), 0, C.RATED_KW)

    df = pd.DataFrame({
        "time": idx, "source_id": 2,
        "power_kw": np.round(power, 2),
        "theoretical_power_kw": np.round(theo, 2),
        "wind_speed_ms": np.round(ws, 2),
        "wind_dir_deg": np.round(rng.uniform(0, 360, len(ws)), 1),
    })
    return _inject_raw_noise(df, rng, cols=["power_kw"])


def _inject_raw_noise(df: pd.DataFrame, rng, cols) -> pd.DataFrame:
    """Add realistic raw-data defects for the Week 2 cleaning stage to remove:
    a few missing timestamps, some NaNs, and a handful of sensor spikes."""
    df = df.copy()
    n = len(df)
    # random missing values (~0.4%)
    for c in cols:
        miss = rng.choice(n, int(n * 0.004), replace=False)
        df.loc[df.index[miss], c] = np.nan
    # sensor spikes (~0.05%) on the primary column
    spikes = rng.choice(n, max(3, int(n * 0.0005)), replace=False)
    df.loc[df.index[spikes], cols[0]] = df[cols[0]].max() * rng.uniform(3, 6, len(spikes))
    # drop a few rows to create missing timestamps
    drop = rng.choice(n, int(n * 0.003), replace=False)
    df = df.drop(df.index[drop]).reset_index(drop=True)
    return df


# --------------------------------------------------------------------------
# REAL DATA STUBS (require network / credentials)
# --------------------------------------------------------------------------
def download_real():  # pragma: no cover - needs network
    raise NotImplementedError(
        "Real-data mode requires network access.\n"
        "  Consumption : UCI 'Individual household electric power consumption'\n"
        "                https://archive.ics.uci.edu/dataset/235\n"
        "  Generation  : Kaggle SCADA wind turbine data (needs kaggle.json token)\n"
        "  Weather     : NOAA GSOD station 07149 (Orly), 07150 (Le Bourget)\n"
        "Place the raw files under data/raw/ and adapt clean.py column maps."
    )


def main():
    ap = argparse.ArgumentParser(description="Acquire GreenPower datasets")
    ap.add_argument("--source", choices=["synthetic", "real"], default="synthetic")
    args = ap.parse_args()
    if args.source == "real":
        download_real()
        return
    rng = _rng()
    print("[acquire] generating calibrated synthetic datasets ...")
    wx = generate_weather(rng)
    cons = generate_consumption(rng, wx)
    gen = generate_generation(rng)
    wx.to_parquet(C.RAW / "weather_raw.parquet") if _has_parquet() else wx.to_csv(C.RAW / "weather_raw.csv", index=False)
    cons.to_csv(C.RAW / "consumption_raw.csv", index=False)
    gen.to_csv(C.RAW / "generation_raw.csv", index=False)
    wx.to_csv(C.RAW / "weather_raw.csv", index=False)
    print(f"[acquire] consumption raw : {len(cons):>7,} rows -> data/raw/consumption_raw.csv")
    print(f"[acquire] generation  raw : {len(gen):>7,} rows -> data/raw/generation_raw.csv")
    print(f"[acquire] weather     raw : {len(wx):>7,} rows -> data/raw/weather_raw.csv")


def _has_parquet():
    try:
        import pyarrow  # noqa
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
