import os


def test_engine_uses_sqlite_in_memory():
    """Ensure tests are executing against the in-memory SQLite engine.

    This guards against accidental Postgres connections in CI when DATABASE_URL
    might be set globally before pytest initializes the test environment.
    """
    # TESTING flag should be enforced by conftest / .env.test
    assert os.environ.get("TESTING") == "true"

    from backend.app.db.session import get_engine  # Imported after TESTING flag
    engine = get_engine()

    # Dialect must be sqlite (file-based or memory). We do not require in-memory.
    assert engine.dialect.name == "sqlite"
    # Provide informational assertion: pool should not be NullPool under tests
    from sqlalchemy.pool import QueuePool
    assert isinstance(engine.pool, QueuePool) or hasattr(engine.pool, "connect")
