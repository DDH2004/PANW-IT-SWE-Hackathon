from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import sys
import importlib.util

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

# Graceful fallback: if URL is Postgres but driver not installed (e.g. CI without psycopg),
# downgrade to ephemeral sqlite so tests still run instead of failing import.
if RAW_DATABASE_URL.startswith("postgres"):
    if importlib.util.find_spec("psycopg") is not None:
        DATABASE_URL = RAW_DATABASE_URL
    else:
        print("[db] psycopg not installed; falling back to sqlite for tests", file=sys.stderr)
        DATABASE_URL = "sqlite:///./data/app.db"
else:
    DATABASE_URL = RAW_DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
