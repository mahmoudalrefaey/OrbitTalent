"""Database engine, session, and base class."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# PostgreSQL connection pool with liveness checks so a recycled or stale
# connection never surfaces as an error to a request.
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
    """Create any missing tables. No tenant seeding — each user creates their
    own tenant on signup (seeding id=1 desynced the Postgres serial sequence)."""
    from app import models  # noqa: F401  -- register tables on Base.metadata

    Base.metadata.create_all(bind=engine)
