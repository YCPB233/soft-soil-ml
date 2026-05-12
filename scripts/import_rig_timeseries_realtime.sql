\set ON_ERROR_STOP on

CREATE TEMP TABLE rig_timeseries_import (
    timestamp_text TEXT,
    elapsed_s TEXT,
    machine_id TEXT,
    project_name TEXT,
    borehole_id TEXT,
    sample_hz TEXT,
    depth_m TEXT,
    layer_id TEXT,
    layer_name TEXT,
    drilling_phase TEXT,
    penetration_speed_m_min TEXT,
    current_a TEXT,
    torque_knm TEXT,
    grouting_pressure_mpa TEXT,
    rotation_rpm TEXT,
    mud_density_g_cm3 TEXT,
    pump_flow_l_min TEXT,
    latitude TEXT,
    longitude TEXT,
    verticality_deg TEXT,
    alarm_code TEXT,
    quality_flag TEXT
);

\copy rig_timeseries_import FROM '/home/wyl/projects/soft-soil-ml/data/raw/rig_timeseries_15h_1hz_stratified.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

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
    longitude
)
SELECT
    NULLIF(machine_id, '') AS machine_code,
    LEFT(NULLIF(project_name, ''), 50) AS project_code,
    NULLIF(timestamp_text, '')::timestamp AS timestamp,
    NULLIF(current_a, '')::double precision AS current_value,
    NULLIF(torque_knm, '')::double precision AS torque,
    NULLIF(penetration_speed_m_min, '')::double precision AS penetration_speed,
    NULLIF(grouting_pressure_mpa, '')::double precision AS grouting_pressure,
    NULLIF(depth_m, '')::double precision AS drilling_depth,
    NULLIF(latitude, '')::double precision AS latitude,
    NULLIF(longitude, '')::double precision AS longitude
FROM rig_timeseries_import imported
WHERE NULLIF(machine_id, '') IS NOT NULL
  AND NULLIF(timestamp_text, '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM machine_realtime_data existing
      WHERE existing.machine_code = imported.machine_id
        AND existing.timestamp = NULLIF(imported.timestamp_text, '')::timestamp
  );
