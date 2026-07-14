"""Database engine and session factory. Swappable between SQLite and Postgres."""

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/engagement.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db(config: Optional[object] = None):
    """
    Create all tables. Safe to call multiple times.

    If config is provided and has a database_url, uses that instead of the
    module-level DATABASE_URL.
    """
    global engine, SessionLocal, DATABASE_URL

    db_url = DATABASE_URL
    if config and hasattr(config, "database_url") and config.database_url:
        db_url = config.database_url

    if db_url != DATABASE_URL:
        # Re-create engine if URL changed
        engine = create_engine(db_url, echo=False)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        DATABASE_URL = db_url

    Base.metadata.create_all(bind=engine)


def init_db_from_config(config: object):
    """Convenience wrapper — calls init_db with config."""
    init_db(config=config)


def get_session():
    """Yield a session context. Works as a context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()