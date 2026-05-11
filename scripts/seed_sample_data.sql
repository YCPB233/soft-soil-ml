INSERT INTO projects (project_code, project_name, location, description)
VALUES
    ('P001', '宁波大学西区学生公寓项目', '宁波市', '软土地基施工监测示范项目')
ON CONFLICT (project_code) DO NOTHING;

INSERT INTO machines (machine_code, machine_name, project_code, status, latitude, longitude)
VALUES
    ('M001', '钻机 1 号', 'P001', 'working', 29.818, 121.558),
    ('M002', '钻机 2 号', 'P001', 'idle', 29.819, 121.559)
ON CONFLICT (machine_code) DO NOTHING;

INSERT INTO machine_training_data (
    machine_code,
    project_code,
    current_value,
    torque,
    penetration_speed,
    grouting_pressure,
    drilling_depth,
    risk_level,
    quality_score
)
VALUES
    ('M001', 'P001', 90, 25, 0.5, 1.0, 5, 'low', 92),
    ('M001', 'P001', 110, 35, 0.8, 1.3, 8, 'low', 88),
    ('M001', 'P001', 135, 45, 1.1, 1.7, 12, 'medium', 78),
    ('M001', 'P001', 160, 55, 1.4, 2.1, 16, 'high', 65),
    ('M002', 'P001', 180, 65, 1.8, 2.5, 20, 'high', 58),
    ('M002', 'P001', 125, 40, 0.9, 1.5, 10, 'medium', 80),
    ('M002', 'P001', 100, 30, 0.6, 1.1, 7, 'low', 90);
