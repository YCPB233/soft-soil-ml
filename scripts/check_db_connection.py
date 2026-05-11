from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import test_connection


if __name__ == "__main__":
    info = test_connection()
    print("Database connection successful.")
    print(info)
