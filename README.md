# GreenPower Utilities — Energy Consumption Analytics

An end-to-end data-engineering capstone that converts raw public energy and weather datasets into a cleaned hourly time-series layer, a portable analytics store, engineered demand features, forecasting models, anomaly detection outputs, and an operational dashboard.

**Capstone:** Six-week Data Engineering Capstone — IIT Jodhpur  
**Team:** Harshit Nirmal Jain (G25AI1021), K R Devika (G25AI1022), Kartik Dadhich (G25AI1023), Kirtiman Sarangi (G25AI1024), Kollipara Teja (G25AI1025)  
**Programme:** M.Tech Data Engineering, IIT Jodhpur  
**Theme:** Energy consumption analytics, demand forecasting, anomaly detection, and dashboarding

---

## Table of Contents

- [The Problem](#the-problem)
- [What We Do](#what-we-do)
- [Research Questions](#research-questions)
- [Pipeline Overview](#pipeline-overview)
- [Data Sources](#data-sources)
- [Cleaning and Preprocessing](#cleaning-and-preprocessing)
- [Storage Layer](#storage-layer)
- [Feature Engineering](#feature-engineering)
- [Forecasting Models](#forecasting-models)
- [Anomaly Detection](#anomaly-detection)
- [Dashboard](#dashboard)
- [Results](#results)
- [Quick Start](#quick-start)
- [Repository Structure](#repository-structure)
- [Progress](#progress)
- [Reproducibility](#reproducibility)
- [Team](#team)

---

## The Problem

Energy utilities need reliable visibility into consumption patterns, renewable generation behavior, demand peaks, and abnormal readings. Raw public energy datasets are useful, but they are usually not ready for analytics because they contain missing timestamps, sensor spikes, inconsistent resolutions, and limited operational context.

For a utility-style analytics workflow, the raw data must be transformed into a reliable time-series foundation before modelling can be trusted.

**We build that foundation and analytics layer for GreenPower Utilities.**

---

## What We Do

This repository implements a complete, runnable energy analytics pipeline. It takes calibrated sample data or real public data stubs, cleans and aligns the time series, stores the results, engineers demand and weather features, trains forecasting models, detects anomalies, and generates dashboard-ready outputs.

The runnable mode is intentionally portable: it uses SQLite and synthetic calibrated data so the entire project can run locally without database servers, cloud credentials, or private datasets. The production design is represented through TimescaleDB migrations for hypertables, compression, continuous aggregates, and feature views.

---

## Research Questions

| # | Question | Pipeline Component |
|---|---|---|
| RQ1 | Can raw energy and weather data be cleaned into a consistent hourly time-series layer? | Acquisition + cleaning |
| RQ2 | Can a storage design support both local reproducibility and production-grade time-series analytics? | SQLite + TimescaleDB schema |
| RQ3 | Which engineered features explain demand behavior and peak consumption patterns? | Calendar, lag, rolling, weather, degree-hour features |
| RQ4 | How accurately can next-hour consumption be forecast using traditional and neural models? | Seasonal-naive, Ridge, MLP, optional LSTM |
| RQ5 | Can abnormal consumption behavior be detected with an interpretable method? | Robust z-score anomaly detector |

---

## Pipeline Overview

The pipeline executes the full dependency chain in order:

```text
acquire -> clean -> store -> features -> models -> anomaly -> figures
```

| Stage | Module | Main Output |
|---|---|---|
| Acquire | `src/data_acquisition.py` | Raw consumption, generation, and weather files in `data/raw/` |
| Clean | `src/clean.py` | Hourly cleaned datasets and `cleaning_report.json` |
| Store | `src/storage.py` | SQLite database at `data/greenpower.db` |
| Features | `src/features.py` | Feature tables, rollups, peaks, degree-hours, CSV exports |
| Models | `src/models.py` | Forecasts, model metrics, `model_stats.json` |
| Anomaly | `src/anomaly.py` | `anomaly_flags.csv`, precision/recall summary |
| Figures | `src/viz.py` | Dashboard figures in `outputs/figures/` |
| Dashboard | `dashboard/build_static.py` | Self-contained `dashboard/dashboard.html` |

---

## Data Sources

The project supports two modes:

| Mode | Purpose | Notes |
|---|---|---|
| `synthetic` | Default runnable mode | Generates calibrated sample datasets matching the project schema, units, seasonality, and report statistics |
| `real` | Public-data mode | Stubs are provided for UCI household consumption, Kaggle SCADA wind, and NOAA GSOD weather |

Dataset periods used by the pipeline:

| Dataset | Period | Role |
|---|---|---|
| UCI-style household consumption | 2006-12-16 to 2010-11-26 | Demand analytics and forecasting target |
| SCADA wind generation | 2018-01-01 to 2020-06-30 | Renewable generation analytics |
| NOAA-style weather | 2006-12-16 to 2020-12-31 | Weather join, heating degree-hours, cooling degree-hours |

The default synthetic mode makes the repository easy to evaluate because it runs anywhere without external downloads or credentials.

---

## Cleaning and Preprocessing

The cleaning layer converts raw readings into reliable hourly UTC series.

| Cleaning Step | Method |
|---|---|
| Timestamp normalization | Convert all timestamps to UTC and sort by time |
| Duplicate handling | Drop duplicate timestamps |
| Spike removal | Robust median absolute deviation based despiking |
| Hourly alignment | Reindex to complete hourly grids |
| Short-gap imputation | Interpolate gaps up to 3 hours |
| Completeness tracking | Record whether each hour is original, imputed, or masked |
| Long-gap handling | Preserve data quality by dropping rows still missing after imputation |

The cleaning report is written to:

```text
outputs/cleaning_report.json
```

---

## Storage Layer

The runnable pipeline uses SQLite so the project can be executed locally with zero infrastructure setup.

| Storage Mode | Location | Purpose |
|---|---|---|
| SQLite | `data/greenpower.db` | Portable local execution and evaluation |
| TimescaleDB | `db/migrations/*.sql` | Production storage design for time-series workloads |

The production design includes:

- Hypertable-oriented schema for consumption, generation, and weather facts
- Composite indexes for time-series lookups
- One-month chunking strategy
- Native compression strategy
- Continuous aggregates and feature views
- Load audit tracking

To deploy the production schema:

```bash
docker compose up -d
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
```

---

## Feature Engineering

The feature layer creates analytical tables for modelling, reporting, and dashboarding.

| Feature Group | Examples |
|---|---|
| Calendar features | Hour, day of week, month, weekend flag, season |
| Cyclical encodings | `hour_sin`, `hour_cos`, `doy_sin`, `doy_cos` |
| Lag features | 1-hour, 24-hour, and 168-hour demand lags |
| Rolling features | 24-hour rolling mean and standard deviation |
| Weather features | Temperature, wind speed, precipitation |
| Degree-hours | Heating degree-hours and cooling degree-hours |
| Daily rollups | Daily total, mean, peak, minimum, peak hour |
| Load metrics | Peak-to-average ratio and load factor |
| Generation metrics | Daily wind generation and capacity factor |

Feature tables are written back to the database and exported as CSV files under `data/cleaned/`.

---

## Forecasting Models

The modelling layer predicts next-hour household active power on a chronological 60-day hold-out set.

| Model | Role | Implementation |
|---|---|---|
| Seasonal-naive | Baseline | Uses value from 168 hours earlier |
| Ridge regression | Linear ML model | scikit-learn |
| MLP neural network | Runnable non-linear model | scikit-learn |
| LSTM | Production deep-learning option | Keras, used only if TensorFlow is installed |

The pipeline automatically uses the MLP neural network as the runnable neural model when TensorFlow is unavailable. Model outputs are saved to:

```text
outputs/evaluation_summary.csv
outputs/forecasts.csv
outputs/model_stats.json
```

---

## Anomaly Detection

The anomaly detector is designed to be interpretable and operationally useful.

Each reading is compared against the expected value for its hour-of-day and month group. The residual is scaled using median absolute deviation so naturally variable evening hours are not over-flagged.

The detector flags:

- Sustained deviations lasting at least two consecutive hours
- Single hard spikes with high robust z-score and large absolute deviation

For evaluation, synthetic outages and spikes are injected into a copy of the clean series. The detector reports precision, recall, and flagged hours.

Outputs:

```text
outputs/anomaly_flags.csv
outputs/anomaly_stats.json
```

---

## Dashboard

The dashboard builder creates a self-contained HTML file that opens in any browser without a server.

```bash
python dashboard/build_static.py
open dashboard/dashboard.html
```

Dashboard panels include:

| Panel | Purpose |
|---|---|
| Daily Load Profile & Evening Peak | Shows recurring consumption shape and peak behavior |
| Forecast vs Actual | Compares model predictions against the final test week |
| Model Error Comparison | Summarizes MAE, RMSE, and MAPE |
| Anomaly Monitor | Visualizes flagged abnormal readings |
| Consumption vs Temperature | Shows weather-demand relationship |
| Wind Capacity Factor by Month | Summarizes renewable generation performance |

---

## Results

Latest documented run:

| Metric | Result |
|---|---|
| Best runnable forecast model | MLP neural net |
| Seasonal-naive MAPE | 28.5% |
| Ridge regression MAPE | 17.3% |
| MLP neural net MAPE | 13.9% |
| RMSE improvement vs baseline | 55% lower than seasonal-naive |
| Anomaly precision | 0.97 |
| Anomaly recall | 0.88 |

**Key findings:**

- Weather-aware and calendar-aware features improve demand forecasting over the weekly seasonal-naive baseline.
- The MLP model provides the best runnable forecast performance while keeping the environment lightweight.
- Robust anomaly detection gives high precision and recall on injected outage/spike scenarios.
- SQLite makes the project easy to run locally, while TimescaleDB migrations preserve a production-ready storage design.

---

## Quick Start

Install dependencies and run the full pipeline:

```bash
pip install -r requirements.txt
python run_pipeline.py
```

Build and open the dashboard:

```bash
python dashboard/build_static.py
open dashboard/dashboard.html
```

Run with real public-data mode after preparing the required source files and credentials:

```bash
python run_pipeline.py --source real
```

---

## Repository Structure

```text
greenpower-capstone/
├── README.md                  # Project overview and execution guide
├── run_pipeline.py            # End-to-end pipeline driver
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Production storage support
│
├── src/                       # Core pipeline modules
│   ├── config.py              # Paths, date ranges, constants, seed
│   ├── data_acquisition.py    # Synthetic and real-data acquisition modes
│   ├── clean.py               # Cleaning, despiking, hourly alignment
│   ├── storage.py             # SQLite load and audit tables
│   ├── features.py            # Rollups, lag features, weather joins
│   ├── models.py              # Forecasting models and evaluation
│   ├── anomaly.py             # Robust anomaly detector
│   └── viz.py                 # Figure generation
│
├── db/
│   └── migrations/            # TimescaleDB production schema and views
│
├── dashboard/
│   ├── build_static.py        # Static dashboard generator
│   ├── dashboard.html         # Generated browser dashboard
│   └── app.py                 # Streamlit dashboard option
│
├── data/                      # Raw, cleaned, and local database files
├── outputs/                   # Metrics, forecasts, anomaly flags, figures
├── notebooks/                 # Analysis walkthroughs
└── reports/                   # Weekly capstone deliverables
```

---

## Progress

- [x] **Week 1:** Data acquisition strategy and source identification
- [x] **Week 2:** Cleaning, preprocessing, spike removal, gap handling, hourly alignment
- [x] **Week 3:** Storage layer with local SQLite runtime and TimescaleDB production schema
- [x] **Week 4:** Feature engineering, rollups, calendar/weather joins, demand analytics
- [x] **Week 5:** Forecasting models and anomaly detection
- [x] **Week 6:** Dashboard, figures, final integration, reproducible run script

---

## Reproducibility

The full project can be reproduced locally with the default synthetic mode:

```bash
git clone https://github.com/Kirtiman-sarangi/greenpower-capstone.git
cd greenpower-capstone
pip install -r requirements.txt
python run_pipeline.py
python dashboard/build_static.py
open dashboard/dashboard.html
```

Expected generated artifacts:

```text
data/raw/
data/cleaned/
data/greenpower.db
outputs/cleaning_report.json
outputs/feature_stats.json
outputs/evaluation_summary.csv
outputs/model_stats.json
outputs/anomaly_stats.json
outputs/figures/
dashboard/dashboard.html
```

---

## Team

- Harshit Nirmal Jain (G25AI1021)
- K R Devika (G25AI1022)
- Kartik Dadhich (G25AI1023)
- Kirtiman Sarangi (G25AI1024)
- Kollipara Teja (G25AI1025)
