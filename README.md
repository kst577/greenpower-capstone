# GreenPower Utilities — Energy Consumption Analytics

Six-week data-engineering capstone (IIT Jodhpur, Group 5). An end-to-end pipeline
that turns raw public energy data into cleaned time series, a partitioned
time-series store, an engineered feature layer, demand-forecasting and
anomaly-detection models, and an operational dashboard.

## Quick start

```bash
pip install -r requirements.txt          # pandas, numpy, scikit-learn, matplotlib
python run_pipeline.py                    # runs the whole thing on sample data (~11s)
python dashboard/build_static.py          # builds dashboard/dashboard.html
open dashboard/dashboard.html             # view the dashboard
```

That's it — no database server or credentials required. The pipeline runs on a
portable SQLite store and calibrated sample data so it executes anywhere.

## Pipeline stages

```
acquire → clean → store → features → models → anomaly → figures
```

| Stage | Module | Output |
|-------|--------|--------|
| Acquire | `src/data_acquisition.py` | raw CSVs in `data/raw/` |
| Clean (Week 2) | `src/clean.py` | cleaned hourly series + `cleaning_report.json` |
| Store (Week 3) | `src/storage.py` | SQLite DB `data/greenpower.db` |
| Features (Week 4) | `src/features.py` | rollups, peaks, calendar, degree-hours |
| Models (Week 5) | `src/models.py` | `evaluation_summary.csv`, `forecasts.csv` |
| Anomaly (Week 5) | `src/anomaly.py` | `anomaly_flags.csv`, precision/recall |
| Figures | `src/viz.py` | `outputs/figures/*.png` |

## Real data

`python run_pipeline.py --source real` targets the genuine public datasets
(UCI household consumption, Kaggle SCADA wind, NOAA GSOD weather). See the stubs
in `src/data_acquisition.py` for sources and access. The default synthetic mode
is calibrated to the published Week 1–2 statistics so results match the reports.

## Production storage (TimescaleDB)

The runnable pipeline uses SQLite for portability. The **production** storage
design from the Week 3 deliverable — hypertables, one-month chunking, native
compression, continuous aggregates — is in `db/migrations/*.sql`, deployable with:

```bash
docker compose up -d
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
```

## Models

| Model | Role | Implementation |
|-------|------|----------------|
| Seasonal-naive | baseline | value 168 h earlier |
| Ridge regression | linear | scikit-learn |
| MLP neural net | non-linear (runnable) | scikit-learn |
| LSTM (Keras) | production deep model | `models.train_lstm_keras`, runs if TensorFlow installed |

Latest run: seasonal-naive 28.5% → Ridge 17.3% → **MLP 13.9% MAPE**
(55% lower RMSE than baseline). Anomaly detector: precision 0.97, recall 0.88.

## Repository layout

```
greenpower-capstone/
├── run_pipeline.py          # end-to-end driver
├── src/                     # pipeline modules (see table above)
├── db/migrations/           # production TimescaleDB schema
├── dashboard/               # static HTML + Streamlit app
├── notebooks/               # analysis walkthrough
├── outputs/                 # figures, metrics, screenshots
└── reports/                 # weekly PDF deliverables
```

## Team

Harshit Nirmal Jain (G25AI1021) · K R Devika (G25AI1022) · Kartik Dadhich (G25AI1023) ·
Kirtiman Sarangi (G25AI1024) · Kollipara Teja (G25AI1025)
