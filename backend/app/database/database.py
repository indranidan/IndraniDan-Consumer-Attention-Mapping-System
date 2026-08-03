"""
Database Engine & Session Management
=====================================
Creates the SQLAlchemy engine, session factory, and declarative Base.
Provides get_db() as a FastAPI dependency for request-scoped sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────
# pool_pre_ping ensures stale connections are recycled automatically.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set True for SQL query logging during development
)

# ── Session Factory ───────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ─────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ── Dependency ────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.
    The session is automatically closed after the request completes.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
