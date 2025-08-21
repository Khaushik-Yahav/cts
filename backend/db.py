from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Build URL from split env vars
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "chatbotdb")


DATABASE_URL = (
f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


engine = create_engine(
DATABASE_URL,
future=True,
pool_pre_ping=True,
)


SessionLocal = sessionmaker(bind=engine, future=True, autocommit=False, autoflush=False)


@contextmanager
def db_session():
session = SessionLocal()
try:
yield session
session.commit()
except Exception:
session.rollback()
raise
finally:
session.close()