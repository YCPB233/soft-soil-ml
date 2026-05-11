from sqlalchemy import create_engine, text

from src.config import DATABASE_URL

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
