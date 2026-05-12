\set ON_ERROR_STOP on

ALTER TABLE machine_realtime_data
ADD COLUMN IF NOT EXISTS borehole_code VARCHAR(100),
ADD COLUMN IF NOT EXISTS rotation_speed_rpm DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS mud_density_g_cm3 DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS pump_flow_l_min DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS verticality_deg DOUBLE PRECISION;

CREATE TEMP TABLE rig001_v2_import (
    timestamp_text TEXT,
    machine_code TEXT,
    project_code TEXT,
    borehole_code TEXT,
    current_value TEXT,
    torque TEXT,
    penetration_speed TEXT,
    grouting_pressure TEXT,
    drilling_depth TEXT,
    rotation_speed_rpm TEXT,
    mud_density_g_cm3 TEXT,
    pump_flow_l_min TEXT,
    verticality_deg TEXT,
    latitude TEXT,
    longitude TEXT
);

\copy rig001_v2_import FROM '/home/wyl/projects/soft-soil-ml/data/raw/nbu_west-test/rig001_synthetic_15h_1hz_drilling_only_v2.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO machine_realtime_data (
    machine_code,
    project_code,
    timestamp,
    current_value,
    torque,
    penetration_speed,
    grouting_pressure,
    drilling_depth,
    latitude,
    longitude,
    borehole_code,
    rotation_speed_rpm,
    mud_density_g_cm3,
    pump_flow_l_min,
    verticality_deg
)
SELECT
    NULLIF(machine_code, ''),
    NULLIF(project_code, ''),
    NULLIF(timestamp_text, '')::timestamp,
    NULLIF(current_value, '')::double precision,
    NULLIF(torque, '')::double precision,
    NULLIF(penetration_speed, '')::double precision,
    NULLIF(grouting_pressure, '')::double precision,
    NULLIF(drilling_depth, '')::double precision,
    NULLIF(latitude, '')::double precision,
    NULLIF(longitude, '')::double precision,
    NULLIF(borehole_code, ''),
    NULLIF(rotation_speed_rpm, '')::double precision,
    NULLIF(mud_density_g_cm3, '')::double precision,
    NULLIF(pump_flow_l_min, '')::double precision,
    NULLIF(verticality_deg, '')::double precision
FROM rig001_v2_import imported
WHERE NULLIF(machine_code, '') IS NOT NULL
  AND NULLIF(project_code, '') IS NOT NULL
  AND NULLIF(timestamp_text, '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM machine_realtime_data existing
      WHERE existing.machine_code = imported.machine_code
        AND existing.project_code = imported.project_code
        AND existing.timestamp = NULLIF(imported.timestamp_text, '')::timestamp
  );
