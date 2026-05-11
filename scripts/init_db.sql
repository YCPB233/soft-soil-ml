CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) UNIQUE NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    machine_code VARCHAR(50) UNIQUE NOT NULL,
    machine_name VARCHAR(255),
    project_code VARCHAR(50),
    status VARCHAR(50),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS machine_realtime_data (
    id SERIAL PRIMARY KEY,
    machine_code VARCHAR(50) NOT NULL,
    project_code VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_value DOUBLE PRECISION,
    torque DOUBLE PRECISION,
    penetration_speed DOUBLE PRECISION,
    grouting_pressure DOUBLE PRECISION,
    drilling_depth DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS machine_training_data (
    id SERIAL PRIMARY KEY,
    machine_code VARCHAR(50),
    project_code VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_value DOUBLE PRECISION NOT NULL,
    torque DOUBLE PRECISION NOT NULL,
    penetration_speed DOUBLE PRECISION NOT NULL,
    grouting_pressure DOUBLE PRECISION NOT NULL,
    drilling_depth DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    quality_score DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS model_predictions (
    id SERIAL PRIMARY KEY,
    machine_code VARCHAR(50),
    project_code VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_value DOUBLE PRECISION,
    torque DOUBLE PRECISION,
    penetration_speed DOUBLE PRECISION,
    grouting_pressure DOUBLE PRECISION,
    drilling_depth DOUBLE PRECISION,
    risk_level VARCHAR(50),
    quality_score DOUBLE PRECISION,
    prediction_result JSONB
);
