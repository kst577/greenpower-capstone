-- Hourly feature view + weather join + peak stats (Week 4 deliverable).
CREATE MATERIALIZED VIEW consumption_features_hourly AS
SELECT time, source_id, active_power_kwh,
       sub_kitchen_kwh, sub_laundry_kwh, sub_climate_kwh, completeness,
       extract(hour  FROM time)::int AS hour,
       extract(dow   FROM time)::int AS dow,
       extract(month FROM time)::int AS month,
       (extract(dow FROM time) IN (0,6)) AS is_weekend,
       CASE WHEN extract(month FROM time) IN (12,1,2) THEN 'winter'
            WHEN extract(month FROM time) IN (3,4,5)  THEN 'spring'
            WHEN extract(month FROM time) IN (6,7,8)  THEN 'summer'
            ELSE 'autumn' END AS season,
       sin(2*pi()*extract(hour FROM time)/24) AS hour_sin,
       cos(2*pi()*extract(hour FROM time)/24) AS hour_cos,
       sin(2*pi()*extract(doy  FROM time)/365) AS doy_sin,
       cos(2*pi()*extract(doy  FROM time)/365) AS doy_cos,
       lag(active_power_kwh, 1)   OVER w AS lag_1h,
       lag(active_power_kwh, 24)  OVER w AS lag_24h,
       lag(active_power_kwh, 168) OVER w AS lag_168h,
       avg(active_power_kwh) OVER (w ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS roll_24h_mean,
       stddev_samp(active_power_kwh) OVER (w ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS roll_24h_std
FROM consumption
WINDOW w AS (PARTITION BY source_id ORDER BY time);

CREATE MATERIALIZED VIEW consumption_weather_hourly AS
SELECT c.time, c.source_id, c.active_power_kwh,
       w.tavg_c, w.tmax_c, w.tmin_c, w.wind_speed_ms, w.precip_mm,
       greatest(18.0 - w.tavg_c, 0) AS hdh,
       greatest(w.tavg_c - 24.0, 0) AS cdh
FROM consumption c JOIN weather w ON w.time = c.time AND w.station_id = 1;
