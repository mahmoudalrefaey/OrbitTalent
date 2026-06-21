"""Database engine, session, and base class."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    # check_same_thread is a SQLite-only flag (single-file dev DB).
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
else:
    # Production (Postgres): real connection pool with liveness checks so a
    # recycled/stale connection doesn't surface as an error to a request.
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. Idempotent.

    No longer seeds a default tenant: with per-user tenants each user creates
    their own on signup. Seeding an explicit id=1 row also desynced the
    Postgres SERIAL sequence (the sequence isn't advanced by explicit-id
    inserts), causing duplicate-key errors on the first real registration.
    """
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
