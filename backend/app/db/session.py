import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Robust import for register_query_timing to support both 'app.db' and 'db' import paths in tests
try:  # Prefer absolute import when app package context is available
    from app.core.db import register_query_timing  # type: ignore
except Exception:
    try:
        # Fallback when imported as top-level 'db.session' in tests
        from core.db import register_query_timing  # type: ignore
    except Exception:
        # Last resort: define a no-op to avoid import-time failures during test discovery
        def register_query_timing(_engine):  # type: ignore
            return None


# Create Base class for models
Base = declarative_base()

# Internal lazy globals
_engine = None
_SessionLocal = None
_database_url = None


def get_engine():
    """Return a cached SQLAlchemy engine, creating it from DATABASE_URL on
    first call. This allows tests to set DATABASE_URL before the engine is
    constructed."""
    global _engine
    global _database_url
    database_url = os.getenv(
        "DATABASE_URL", "[REDACTED_DATABASE_URL]"
    )
    # If engine not created yet or DATABASE_URL changed, (re)create engine
    if _engine is None or _database_url != database_url:
        # Dispose previous engine if present
        if _engine is not None:
            try:
                _engine.dispose()
            except Exception:
                pass
        _engine = create_engine(database_url)
        register_query_timing(_engine)
        _database_url = database_url
    return _engine


def get_sessionmaker():
    """Return a cached sessionmaker bound to the lazy engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


def SessionLocal():
    """Compatibility wrapper: calling SessionLocal() returns a new Session
    instance. Modules that do `from db.session import SessionLocal` and then
    call `SessionLocal()` will continue to work."""
    return get_sessionmaker()()


# Backwards-compatible public symbols. Some modules import `engine` or
# `SessionLocal` at module level; expose names that resolve to the lazy
# implementations above.


class _EngineProxy:
    def __getattr__(self, item):
        return getattr(get_engine(), item)


# Provide a module-level 'engine' object that proxies to the real engine.
engine = _EngineProxy()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in database using the lazy engine."""
    Base.metadata.create_all(bind=get_engine())
