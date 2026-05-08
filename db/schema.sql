CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS earth_cells (
    h3_index TEXT PRIMARY KEY,
    resolution INTEGER NOT NULL CHECK (resolution BETWEEN 0 AND 15),
    center GEOGRAPHY(POINT, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cell_observations (
    observed_at TIMESTAMPTZ NOT NULL,
    h3_index TEXT NOT NULL REFERENCES earth_cells (h3_index) ON DELETE CASCADE,
    fidelity TEXT NOT NULL CHECK (
        fidelity IN (
            'illustrative',
            'interactive',
            'engineering',
            'research',
            'observed',
            'data-dependent',
            'progressive',
            'perceptual'
        )
    ),
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (h3_index, observed_at, fidelity)
);

SELECT create_hypertable(
    'cell_observations',
    'observed_at',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS earth_cells_center_gix
    ON earth_cells
    USING GIST (center);

CREATE INDEX IF NOT EXISTS cell_observations_properties_gin
    ON cell_observations
    USING GIN (properties);
