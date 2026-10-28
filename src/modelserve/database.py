"""Database engine configuration and session management."""

from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from modelserve.models import Base

logger = logging.getLogger("modelserve.database")


def get_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy Engine with pre-ping connection verification."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a thread-safe session factory bound to the provided engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_database_connection(engine: Engine) -> bool:
    """Execute a simple probe query to verify database availability."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database connection probe failed: %s", exc)
        return False


def init_db(engine: Engine) -> None:
    """Create all schema tables directly (used in tests or fresh database bootstrap)."""
    Base.metadata.create_all(bind=engine)

