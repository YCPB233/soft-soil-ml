import pandas as pd

from src.db import get_engine

FEATURE_COLUMNS = [
    "current_value",
    "torque",
    "penetration_speed",
    "grouting_pressure",
    "drilling_depth",
]

TARGET_COLUMN = "risk_level"


def load_training_data():
    engine = get_engine()

    query = """
    SELECT
        current_value,
        torque,
        penetration_speed,
        grouting_pressure,
        drilling_depth,
        risk_level
    FROM machine_training_data
    WHERE risk_level IS NOT NULL;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise RuntimeError("No training data found in machine_training_data.")

    missing = [col for col in FEATURE_COLUMNS + [TARGET_COLUMN] if col not in df.columns]
    if missing:
        raise RuntimeError(f"Training data missing columns: {missing}")

    return df
