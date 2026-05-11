import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please check your .env file.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)


def get_engine():
    return engine


def test_connection():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_user;"))
        row = result.fetchone()
        return {
            "current_database": row[0],
            "current_user": row[1],
        }
