from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings


def _build_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        # SQLite: file-based or in-memory; pool_size/max_overflow not supported
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    # PostgreSQL / other — use connection pool.
    # connect_timeout bounds how long a probe or request waits on an unreachable
    # database: without it a credential/network failure makes /health/ready and
    # every DB-backed request hang instead of failing fast with 503/500.
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
