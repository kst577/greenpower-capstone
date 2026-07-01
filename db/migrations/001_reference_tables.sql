-- Reference / bookkeeping tables (plain PostgreSQL). Week 3 deliverable.
CREATE TABLE IF NOT EXISTS data_source (
    source_id        SMALLINT PRIMARY KEY,
    name             TEXT NOT NULL,
    domain           TEXT NOT NULL,
    provider         TEXT,
    license          TEXT,
    native_resolution TEXT
);
CREATE TABLE IF NOT EXISTS station (
    station_id SMALLINT PRIMARY KEY,
    name TEXT NOT NULL, lat REAL, lon REAL, country TEXT, role TEXT
);
CREATE TABLE IF NOT EXISTS ingest_watermark (
    source TEXT PRIMARY KEY, last_loaded_ts TIMESTAMPTZ, updated_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS load_audit (
    run_id TEXT, job TEXT, source TEXT,
    rows_read INT, rows_inserted INT, rows_updated INT, rows_rejected INT,
    status TEXT, started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ
);
