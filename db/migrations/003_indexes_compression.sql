-- Composite indexes + native columnar compression (Week 3 deliverable).
CREATE INDEX ON consumption (source_id, time DESC);
CREATE INDEX ON generation  (source_id, time DESC);
CREATE INDEX ON weather     (station_id, time DESC);

ALTER TABLE consumption SET (timescaledb.compress,
    timescaledb.compress_segmentby='source_id', timescaledb.compress_orderby='time DESC');
ALTER TABLE generation  SET (timescaledb.compress,
    timescaledb.compress_segmentby='source_id', timescaledb.compress_orderby='time DESC');
ALTER TABLE weather     SET (timescaledb.compress,
    timescaledb.compress_segmentby='station_id', timescaledb.compress_orderby='time DESC');
SELECT add_compression_policy('consumption', INTERVAL '90 days');
SELECT add_compression_policy('generation',  INTERVAL '90 days');
SELECT add_compression_policy('weather',     INTERVAL '90 days');
