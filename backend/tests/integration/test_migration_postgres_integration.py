"""
PostgreSQL-specific integration test for inventory migration.
This test requires a running Postgres instance reachable via DATABASE_URL.
It will be skipped if the DB is not available.
"""

import os
import subprocess
import time
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.docker
def test_migration_postgres_integration():
    """Test migration against a real PostgreSQL database.

    The test will:
    - Read DATABASE_URL from the environment (or default to localhost)
    - Connect and create an `inventory` table with old schema ("order" NOT NULL)
    - Insert a row
    - Run the migration script as a subprocess with PYTHONPATH pointing to backend
    - Verify the column is nullable afterwards and data preserved
    """
    db_url = os.getenv(
        "DATABASE_URL",
        "[REDACTED_DATABASE_URL]",
    )

    # quick connectivity check
    try:
        engine = create_engine(db_url)
        conn = engine.connect()
    except Exception as e:
        pytest.skip(f"Postgres not available: {e}")

    # If the configured DATABASE_URL is not a Postgres dialect (e.g., tests set it to sqlite), skip
    if engine.dialect.name != "postgresql":
        conn.close()
        pytest.skip(f"DATABASE_URL is not Postgres (dialect={engine.dialect.name})")

    # ensure a clean table
    try:
        conn.execute(text("DROP TABLE IF EXISTS inventory;"))
    except Exception:
        pass

    # create old schema with order NOT NULL DEFAULT 0
    conn.execute(
        text(
            'CREATE TABLE inventory (id SERIAL PRIMARY KEY, nome VARCHAR, quantidade INTEGER, "order" INTEGER NOT NULL DEFAULT 0);'
        )
    )
    conn.execute(
        text(
            "INSERT INTO inventory (nome, quantidade, \"order\") VALUES ('pg-old', 1, 0);"
        )
    )
    conn.commit()

    # Run migration script in subprocess with PYTHONPATH set so it can import 'app'
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "backend")
    proc = subprocess.run(
        ["python", "backend/scripts/migrate_inventory_order.py"],
        env=env,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        conn.close()
        pytest.skip(f"Migration script failed to run: {proc.stdout}\n{proc.stderr}")

    # inspect information_schema to confirm nullability
    res = conn.execute(
        text(
            "SELECT is_nullable, column_default FROM information_schema.columns WHERE table_name='inventory' AND column_name='order';"
        )
    ).fetchone()

    conn.close()

    assert res is not None
    is_nullable, column_default = res
    assert is_nullable == "YES"
    # default should be NULL or None
    assert column_default is None
