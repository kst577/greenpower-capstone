-- Continuous aggregates: daily + monthly rollups (Week 4 deliverable).
CREATE MATERIALIZED VIEW consumption_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS day, source_id,
       sum(active_power_kwh) AS total_kwh,
       avg(active_power_kwh) AS mean_kw,
       max(active_power_kwh) AS peak_kw,
       min(active_power_kwh) AS min_kw,
       sum(sub_kitchen_kwh)  AS kitchen_kwh,
       sum(sub_laundry_kwh)  AS laundry_kwh,
       sum(sub_climate_kwh)  AS climate_kwh,
       avg(completeness)     AS mean_completeness
FROM consumption GROUP BY day, source_id WITH NO DATA;

CREATE MATERIALIZED VIEW consumption_monthly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 month', day) AS month, source_id,
       sum(total_kwh) AS total_kwh, avg(mean_kw) AS mean_kw, max(peak_kw) AS peak_kw
FROM consumption_daily GROUP BY month, source_id WITH NO DATA;

CREATE MATERIALIZED VIEW generation_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS day, source_id,
       sum(power_kw) AS gen_kwh, avg(power_kw) AS mean_kw, max(power_kw) AS peak_kw,
       avg(power_kw)/3600.0 AS capacity_factor, avg(wind_speed_ms) AS mean_wind_ms
FROM generation GROUP BY day, source_id WITH NO DATA;

SELECT add_continuous_aggregate_policy('consumption_daily',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 day');
SELECT add_continuous_aggregate_policy('consumption_monthly',
    start_offset => INTERVAL '2 months', end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');
SELECT add_continuous_aggregate_policy('generation_daily',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 day');
