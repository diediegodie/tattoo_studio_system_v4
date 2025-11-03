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
    database_url = os.getenv("DATABASE_URL", "[REDACTED_DATABASE_URL]")
    # If engine not created yet or DATABASE_URL changed, (re)create engine
    if _engine is None or _database_url != database_url:
        # Dispose previous engine if present
        if _engine is not None:
            try:
                _engine.dispose()
            except Exception:
                pass
        # Configure engine with production-ready pooling for PostgreSQL.
        # For non-Postgres URLs (e.g., SQLite in tests), fall back to a minimal config.
        try:
            from sqlalchemy.engine.url import make_url

            url = make_url(database_url)
            is_postgres = url.drivername.startswith(
                "postgresql"
            ) or url.drivername.startswith("postgres")
        except Exception:
            # If URL parsing fails, assume non-Postgres to avoid passing incompatible connect_args
            is_postgres = False

        if is_postgres:
            # Optimized engine configuration for production PostgreSQL
            _engine = create_engine(
                database_url,
                pool_size=20,  # Handles ~4 Gunicorn workers × 5 connections
                max_overflow=40,  # Allows burst capacity
                pool_pre_ping=True,  # Detects and refreshes stale connections
                pool_recycle=3600,  # Recycle connections every hour to avoid idle timeouts
                connect_args={
                    "application_name": "tattoo_studio",  # Visible in pg_stat_activity
                    "connect_timeout": 10,  # Fail fast on connection issues
                },
                echo=False,  # Controlled by logging config; keep SQL echo off by default
            )
        else:
            # Default safe engine for other backends (e.g., SQLite during tests)
            try:
                from sqlalchemy.pool import StaticPool

                db_url_str = str(database_url)
                is_sqlite_memory = db_url_str.startswith("sqlite") and (
                    ":memory:" in db_url_str
                )
                if is_sqlite_memory:
                    # Use a single shared in-memory database across the process
                    # so DDL persists across connections (important for tests
                    # that create tables and then open new sessions).
                    _engine = create_engine(
                        database_url,
                        echo=False,
                        connect_args={"check_same_thread": False},
                        poolclass=StaticPool,
                    )
                else:
                    _engine = create_engine(database_url, echo=False)
            except Exception:
                _engine = create_engine(database_url, echo=False)
        register_query_timing(_engine)
        try:
            # Emit explicit debug about the constructed engine target and dialect
            print(">>> DEBUG: SQLAlchemy engine URL:", str(getattr(_engine, "url", "")))
            print(
                ">>> DEBUG: SQLAlchemy dialect:",
                getattr(getattr(_engine, "dialect", None), "name", "unknown"),
            )
        except Exception:
            # Printing should never break engine creation
            pass
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
    try:
        session = get_sessionmaker()()
        # In test runs, defensively ensure tables exist. Some integration
        # fixtures drop all tables between tests; tests that use SessionLocal
        # directly (without the app/db fixtures) may otherwise see missing
        # tables. Creating tables is idempotent on SQLite and cheap.
        if os.getenv("TESTING", "").lower() in ("1", "true", "yes"):
            try:
                # Ensure models are imported so Base.metadata is populated
                try:
                    import importlib

                    importlib.import_module("app.db.base")
                except Exception:
                    pass
                create_tables()
            except Exception:
                # Never fail session creation due to table creation attempts
                pass
        print(">>> DEBUG: DB session created successfully")
        return session
    except Exception as e:
        print(">>> DEBUG: Failed to create DB session:", e)
        raise


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
    eng = get_engine()
    # Create tables using this module's Base (may be empty if models were bound to a
    # different Base due to import/reload order in tests)
    try:
        Base.metadata.create_all(bind=eng)
    except Exception:
        pass
    # Also attempt with the Base from app.db.base where models are defined to cover
    # cases where model Base != session.Base due to reloads in fixtures.
    try:
        from app.db.base import Base as ModelsBase

        ModelsBase.metadata.create_all(bind=eng)
    except Exception:
        pass
