"""Week 3 — storage layer (runnable engine).

Loads the cleaned datasets into a local SQLite database with the same logical
schema as the TimescaleDB design documented in the Week 3 deliverable. SQLite is
used here so the pipeline runs anywhere with zero setup; the production
TimescaleDB schema (hypertables, continuous aggregates, compression) lives in
db/migrations/*.sql and docker-compose.yml.

The load is idempotent: re-running replaces the tables cleanly.
"""
from __future__ import annotations
import sqlite3
import pandas as pd
from . import config as C

REFERENCE = {
    "data_source": pd.DataFrame([
        {"source_id": 1, "name": "uci_household", "domain": "consumption",
         "provider": "UCI", "native_resolution": "1 min"},
        {"source_id": 2, "name": "scada_wind", "domain": "generation",
         "provider": "Kaggle SCADA", "native_resolution": "10 min"},
    ]),
    "station": pd.DataFrame([
        {"station_id": 1, "name": "Orly", "lat": 48.73, "lon": 2.40, "role": "primary"},
        {"station_id": 2, "name": "Le Bourget", "lat": 48.97, "lon": 2.44, "role": "fallback"},
    ]),
}


def connect() -> sqlite3.Connection:
    return sqlite3.connect(C.DB_PATH)


def load_all() -> dict:
    con = connect()
    counts = {}
    # reference tables
    for name, df in REFERENCE.items():
        df.to_sql(name, con, if_exists="replace", index=False)

    # fact tables from cleaned CSVs
    fact_files = {
        "consumption": "uci_household_hourly.csv",
        "generation": "scada_wind_hourly.csv",
        "weather": "noaa_weather_hourly.csv",
    }
    for table, fname in fact_files.items():
        df = pd.read_csv(C.CLEANED / fname)
        df.to_sql(table, con, if_exists="replace", index=False)
        counts[table] = len(df)

    # indexes matching the Week 3 composite indexes
    cur = con.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cons ON consumption(source_id, time)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_gen  ON generation(source_id, time)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_wx   ON weather(station_id, time)")
    con.commit()

    # load-audit table (one row per fact load)
    audit = pd.DataFrame([
        {"table": t, "rows_loaded": n, "status": "success"} for t, n in counts.items()
    ])
    audit.to_sql("load_audit", con, if_exists="replace", index=False)
    con.close()
    return counts


def main():
    print("[storage] loading cleaned data into SQLite ...")
    counts = load_all()
    for t, n in counts.items():
        print(f"[storage] {t:12} {n:>7,} rows loaded")
    print(f"[storage] database at {C.DB_PATH.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
