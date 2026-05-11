import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

MODEL_DIR = Path(os.getenv("MODEL_DIR", "src/ml/saved_models"))
RISK_MODEL_PATH = Path(os.getenv("RISK_MODEL_PATH", "src/ml/saved_models/risk_model.pkl"))
MODEL_METADATA_PATH = Path(
    os.getenv("MODEL_METADATA_PATH", "src/ml/saved_models/model_metadata.json")
)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please check your .env file.")
