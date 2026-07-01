-- Three time-series fact hypertables (TimescaleDB). Week 3 deliverable.
CREATE TABLE consumption (
    time                TIMESTAMPTZ    NOT NULL,
    source_id           SMALLINT       NOT NULL REFERENCES data_source,
    active_power_kwh    DOUBLE PRECISION,
    reactive_power_kvarh DOUBLE PRECISION,
    voltage_v           REAL,
    intensity_a         REAL,
    sub_kitchen_kwh     REAL,
    sub_laundry_kwh     REAL,
    sub_climate_kwh     REAL,
    completeness        REAL,
    PRIMARY KEY (time, source_id)
);
SELECT create_hypertable('consumption','time', chunk_time_interval => INTERVAL '1 month');

CREATE TABLE generation (
    time                 TIMESTAMPTZ NOT NULL,
    source_id            SMALLINT    NOT NULL REFERENCES data_source,
    power_kw             DOUBLE PRECISION,
    theoretical_power_kw DOUBLE PRECISION,
    wind_speed_ms        REAL,
    wind_dir_deg         REAL,
    completeness         REAL,
    PRIMARY KEY (time, source_id)
);
SELECT create_hypertable('generation','time', chunk_time_interval => INTERVAL '1 month');

CREATE TABLE weather (
    time           TIMESTAMPTZ NOT NULL,
    station_id     SMALLINT    NOT NULL REFERENCES station,
    tavg_c REAL, tmax_c REAL, tmin_c REAL,
    wind_speed_ms REAL, precip_mm REAL, sky_cond TEXT,
    source_station TEXT,
    PRIMARY KEY (time, station_id)
);
SELECT create_hypertable('weather','time', chunk_time_interval => INTERVAL '1 month');
