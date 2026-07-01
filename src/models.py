"""Week 5 — forecasting models and evaluation.

Predicts the household's next-hour active power on a 60-day chronological
hold-out and compares three models of increasing sophistication:

    1. Seasonal-naive   (value 168 h earlier)          - baseline
    2. Ridge regression (linear, on lag/calendar/weather features)
    3. MLP neural net   (scikit-learn, non-linear)     - best runnable model

A Keras LSTM implementation (`train_lstm_keras`) is included for environments
where TensorFlow is installed; it is the production model referenced in the
Week 5 deliverable. When TensorFlow is unavailable the pipeline uses the MLP,
which fills the same "neural, non-linear" role and runs with scikit-learn only.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from . import config as C
from .storage import connect

FEATURES = ["lag_1h", "lag_24h", "lag_168h", "roll_24h_mean", "roll_24h_std",
            "hour_sin", "hour_cos", "doy_sin", "doy_cos", "is_weekend", "hdh", "cdh"]
TARGET = "active_power_kwh"


def _metrics(a, p):
    a, p = np.asarray(a, float), np.asarray(p, float)
    m = ~np.isnan(p)
    a, p = a[m], p[m]
    e = p - a
    mae = float(np.mean(np.abs(e)))
    rmse = float(np.sqrt(np.mean(e ** 2)))
    mape = float(np.mean(np.abs(e) / np.clip(np.abs(a), 0.3, None)) * 100)
    return round(mae, 3), round(rmse, 3), round(mape, 1)


def load_supervised():
    con = connect()
    df = pd.read_sql(f"SELECT * FROM consumption_features_hourly", con)
    con.close()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").dropna(subset=FEATURES + [TARGET])
    split = df.index.max() - pd.Timedelta(days=C.TEST_DAYS)
    train, test = df[df.index <= split], df[df.index > split]
    return train, test, split


def train_lstm_keras(train, test):  # pragma: no cover - needs tensorflow
    """Production LSTM (Week 5). Runs only if TensorFlow is installed."""
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    look = 168
    sc = StandardScaler().fit(train[FEATURES])
    def seq(d):
        X = sc.transform(d[FEATURES]); y = d[TARGET].values
        xs = [X[i - look:i] for i in range(look, len(X))]
        return np.array(xs), y[look:]
    Xtr, ytr = seq(train); Xte, yte = seq(test)
    model = Sequential([LSTM(64, input_shape=(look, len(FEATURES))),
                        Dropout(0.2), Dense(32, activation="relu"), Dense(1)])
    model.compile(optimizer="adam", loss="mse")
    model.fit(Xtr, ytr, validation_split=0.15, epochs=30, batch_size=64,
              callbacks=[EarlyStopping(patience=5)], verbose=0)
    return yte, model.predict(Xte).ravel()


def run():
    train, test, split = load_supervised()
    y = test[TARGET].values
    results, preds = {}, {}

    # 1) seasonal-naive baseline
    preds["Seasonal-naive"] = test["lag_168h"].values
    # 2) ridge regression
    ridge = Ridge(alpha=1.0).fit(train[FEATURES], train[TARGET])
    preds["Ridge regression"] = ridge.predict(test[FEATURES])
    # 3) MLP neural network (runnable "deep" model)
    sc = StandardScaler().fit(train[FEATURES])
    mlp = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=400,
                       early_stopping=True, random_state=C.SEED)
    mlp.fit(sc.transform(train[FEATURES]), train[TARGET])
    preds["MLP neural net"] = mlp.predict(sc.transform(test[FEATURES]))

    # optional Keras LSTM if available
    model_used_neural = "MLP neural net"
    try:
        import tensorflow  # noqa
        yte, p = train_lstm_keras(train, test)
        results["LSTM (Keras)"] = _metrics(yte, p)
        model_used_neural = "LSTM (Keras)"
    except Exception:
        pass

    for name, p in preds.items():
        results[name] = _metrics(y, p)

    # save forecasts + summary
    fc = pd.DataFrame({"time": test.index, "actual": y, **{k: v for k, v in preds.items()}})
    fc.to_csv(C.OUTPUTS / "forecasts.csv", index=False)
    summary = pd.DataFrame(
        [{"model": k, "MAE_kW": v[0], "RMSE_kW": v[1], "MAPE_pct": v[2]} for k, v in results.items()])
    summary.to_csv(C.OUTPUTS / "evaluation_summary.csv", index=False)

    best = min(results.items(), key=lambda kv: kv[1][1])
    base = results["Seasonal-naive"]
    stats = {
        "test_days": C.TEST_DAYS, "test_hours": int(len(test)), "train_hours": int(len(train)),
        "split_date": str(split.date()),
        "models": {k: {"MAE": v[0], "RMSE": v[1], "MAPE": v[2]} for k, v in results.items()},
        "best_model": best[0], "best_mape": best[1][2], "best_rmse": best[1][1],
        "improve_vs_baseline_pct": round((1 - best[1][1] / base[1]) * 100, 0),
        "neural_model_used": model_used_neural,
    }
    (C.OUTPUTS / "model_stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main():
    print("[models] training forecasting models (60-day hold-out) ...")
    s = run()
    for name, m in s["models"].items():
        print(f"[models] {name:20} MAE {m['MAE']:.3f}  RMSE {m['RMSE']:.3f}  MAPE {m['MAPE']:.1f}%")
    print(f"[models] best: {s['best_model']} (MAPE {s['best_mape']}%, "
          f"{s['improve_vs_baseline_pct']:.0f}% better RMSE than baseline)")


if __name__ == "__main__":
    main()
