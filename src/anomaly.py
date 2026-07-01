"""Week 5 — anomaly detection.

Robust, interpretable outage/fault detector. Each reading is compared to the
expected value for its hour-of-day x month group, and the deviation is scaled by
a per-group median absolute deviation (so naturally variable evening hours are
not over-flagged). A two-part rule fires on either a sustained deviation
(>= 2 consecutive hours, characteristic of an outage) or a single hard spike.

For evaluation a labelled set of synthetic outages/spikes is injected into a
copy of the clean series, and precision / recall are reported. In production the
same detector runs on the live feed with no labels.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from . import config as C
from .storage import connect


def detect(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    idx = series.index
    grp = pd.Series(list(zip(idx.hour, idx.month)), index=idx)
    med = series.groupby(grp).transform("median")
    resid = series - med
    mad = resid.abs().groupby(grp).transform("median").replace(0, np.nan)
    z = (resid / (1.4826 * mad)).fillna(0).values
    base = pd.Series((np.abs(z) > 3.5) & (resid.abs().values > 0.30), index=idx)
    sustained = (base & (base.shift(1, fill_value=False) | base.shift(-1, fill_value=False))).values
    hard_spike = (np.abs(z) > 6.0) & (resid.abs().values > 0.6)
    return sustained | hard_spike, z


def run():
    con = connect()
    df = pd.read_sql("SELECT time, active_power_kwh FROM consumption", con)
    con.close()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    s = df.set_index("time")["active_power_kwh"].copy()

    rng = np.random.default_rng(C.SEED)
    truth = np.zeros(len(s), bool)
    a = s.values.copy()
    for st in rng.choice(np.arange(1000, len(s) - 1000), 8, replace=False):
        L = int(rng.integers(3, 7)); a[st:st + L] *= rng.uniform(0.02, 0.07); truth[st:st + L] = True
    for st in rng.choice(np.arange(1000, len(s) - 1000), 5, replace=False):
        a[st] *= rng.uniform(3.2, 4.5); truth[st] = True
    s_inj = pd.Series(a, index=s.index)

    flag, _ = detect(s_inj)
    tp = int((flag & truth).sum()); fp = int((flag & ~truth).sum()); fn = int((truth & ~flag).sum())
    stats = {
        "injected_anomaly_hours": int(truth.sum()),
        "flagged_hours": int(flag.sum()),
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": round(tp / max(tp + fp, 1), 2),
        "recall": round(tp / max(tp + fn, 1), 2),
    }
    (C.OUTPUTS / "anomaly_stats.json").write_text(json.dumps(stats, indent=2))
    # persist flags for the dashboard
    out = pd.DataFrame({"time": s.index, "value": s_inj.values, "is_anomaly": flag})
    out.to_csv(C.OUTPUTS / "anomaly_flags.csv", index=False)
    return stats


def main():
    print("[anomaly] running robust z-score detector ...")
    s = run()
    print(f"[anomaly] flagged {s['flagged_hours']} hours | precision {s['precision']} | recall {s['recall']}")


if __name__ == "__main__":
    main()
