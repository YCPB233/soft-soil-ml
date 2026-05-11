CREATE TABLE IF NOT EXISTS machine_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    machine_id VARCHAR(50) NOT NULL,
    project_id VARCHAR(100),
    pile_id VARCHAR(100),
    depth DOUBLE PRECISION,
    current_value DOUBLE PRECISION,
    torque DOUBLE PRECISION,
    penetration_speed DOUBLE PRECISION,
    grout_pressure DOUBLE PRECISION,
    drilling_speed DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_predictions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    machine_id VARCHAR(50),
    project_id VARCHAR(100),
    pile_id VARCHAR(100),
    depth DOUBLE PRECISION,
    true_status VARCHAR(50),
    predicted_status VARCHAR(50),
    confidence DOUBLE PRECISION,
    model_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_runs (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    dataset_name VARCHAR(100),
    feature_cols TEXT,
    target_col VARCHAR(100),
    accuracy DOUBLE PRECISION,
    f1_score DOUBLE PRECISION,
    model_path TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
