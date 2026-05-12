\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS soil_layers (
    id SERIAL PRIMARY KEY,
    stratum_order INTEGER UNIQUE NOT NULL,
    layer_id_raw VARCHAR(100) NOT NULL,
    layer_code VARCHAR(100) NOT NULL,
    layer_name VARCHAR(255) NOT NULL,
    top_depth_range_m VARCHAR(100),
    top_depth_max_m DOUBLE PRECISION,
    top_depth_min_m DOUBLE PRECISION,
    top_depth_representative_m DOUBLE PRECISION,
    top_elevation_range_m VARCHAR(100),
    top_elevation_max_m DOUBLE PRECISION,
    top_elevation_min_m DOUBLE PRECISION,
    thickness_range_m VARCHAR(100),
    thickness_max_m DOUBLE PRECISION,
    thickness_min_m DOUBLE PRECISION,
    thickness_representative_m DOUBLE PRECISION,
    bottom_depth_representative_m DOUBLE PRECISION,
    engineering_group VARCHAR(255),
    description_for_modeling TEXT,
    source_table TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TEMP TABLE soil_layers_import (
    stratum_order TEXT,
    layer_id TEXT,
    layer_name TEXT,
    top_depth_range_m TEXT,
    top_depth_max_m TEXT,
    top_depth_min_m TEXT,
    top_depth_representative_m TEXT,
    top_elevation_range_m TEXT,
    top_elevation_max_m TEXT,
    top_elevation_min_m TEXT,
    thickness_range_m TEXT,
    thickness_max_m TEXT,
    thickness_min_m TEXT,
    thickness_representative_m TEXT,
    bottom_depth_representative_m TEXT,
    engineering_group TEXT,
    description_for_modeling TEXT,
    source_table TEXT
);

\copy soil_layers_import FROM '/home/wyl/projects/soft-soil-ml/data/raw/stratigraphic_layer_table_from_geotech_report.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO soil_layers (
    stratum_order,
    layer_id_raw,
    layer_code,
    layer_name,
    top_depth_range_m,
    top_depth_max_m,
    top_depth_min_m,
    top_depth_representative_m,
    top_elevation_range_m,
    top_elevation_max_m,
    top_elevation_min_m,
    thickness_range_m,
    thickness_max_m,
    thickness_min_m,
    thickness_representative_m,
    bottom_depth_representative_m,
    engineering_group,
    description_for_modeling,
    source_table
)
SELECT
    NULLIF(stratum_order, '')::integer,
    NULLIF(layer_id, ''),
    CASE
        WHEN layer_id LIKE '%月%日' THEN replace(replace(layer_id, '月', '-'), '日', '')
        ELSE NULLIF(layer_id, '')
    END AS layer_code,
    NULLIF(layer_name, ''),
    NULLIF(top_depth_range_m, ''),
    NULLIF(top_depth_max_m, '')::double precision,
    NULLIF(top_depth_min_m, '')::double precision,
    NULLIF(top_depth_representative_m, '')::double precision,
    NULLIF(top_elevation_range_m, ''),
    NULLIF(top_elevation_max_m, '')::double precision,
    NULLIF(top_elevation_min_m, '')::double precision,
    NULLIF(thickness_range_m, ''),
    NULLIF(thickness_max_m, '')::double precision,
    NULLIF(thickness_min_m, '')::double precision,
    NULLIF(thickness_representative_m, '')::double precision,
    NULLIF(bottom_depth_representative_m, '')::double precision,
    NULLIF(engineering_group, ''),
    NULLIF(description_for_modeling, ''),
    NULLIF(source_table, '')
FROM soil_layers_import
ON CONFLICT (stratum_order) DO UPDATE SET
    layer_id_raw = EXCLUDED.layer_id_raw,
    layer_code = EXCLUDED.layer_code,
    layer_name = EXCLUDED.layer_name,
    top_depth_range_m = EXCLUDED.top_depth_range_m,
    top_depth_max_m = EXCLUDED.top_depth_max_m,
    top_depth_min_m = EXCLUDED.top_depth_min_m,
    top_depth_representative_m = EXCLUDED.top_depth_representative_m,
    top_elevation_range_m = EXCLUDED.top_elevation_range_m,
    top_elevation_max_m = EXCLUDED.top_elevation_max_m,
    top_elevation_min_m = EXCLUDED.top_elevation_min_m,
    thickness_range_m = EXCLUDED.thickness_range_m,
    thickness_max_m = EXCLUDED.thickness_max_m,
    thickness_min_m = EXCLUDED.thickness_min_m,
    thickness_representative_m = EXCLUDED.thickness_representative_m,
    bottom_depth_representative_m = EXCLUDED.bottom_depth_representative_m,
    engineering_group = EXCLUDED.engineering_group,
    description_for_modeling = EXCLUDED.description_for_modeling,
    source_table = EXCLUDED.source_table,
    imported_at = CURRENT_TIMESTAMP;
