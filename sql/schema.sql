-- One row per (station, parameter, timestamp) measurement.
-- The composite primary key makes re-running the pipeline idempotent:
-- re-inserting the same measurement is a no-op (or an update) rather than a duplicate row.
CREATE TABLE IF NOT EXISTS observations (
    station_id   INTEGER NOT NULL,
    station_name TEXT NOT NULL,
    parameter_id INTEGER NOT NULL,
    metric       TEXT NOT NULL,
    unit         TEXT NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    quality      TEXT,
    PRIMARY KEY (station_id, parameter_id, timestamp)
);
