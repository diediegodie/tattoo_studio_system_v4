import os
import sqlite3
import tempfile
import subprocess
import sys
from pathlib import Path

import pytest


def _create_old_schema(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            quantidade INTEGER,
            "order" INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    # Insert a row
    cur.execute(
        'INSERT INTO inventory (nome, quantidade, "order") VALUES (?, ?, ?)',
        ("old", 1, 0),
    )
    conn.commit()
    conn.close()


def test_migration_integration_sqlite(tmp_path):
    db_file = tmp_path / "test_migrate.db"
    _create_old_schema(str(db_file))

    # Run the migration script with DATABASE_URL pointing to this sqlite file
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file}"

    # Run the migration as a separate Python process so it uses its own SQLAlchemy engine
    # Ensure PYTHONPATH includes the 'backend' package directory so 'app' is importable
    env["PYTHONPATH"] = str(Path.cwd() / "backend")
    cmd = [sys.executable, "backend/scripts/migrate_inventory_order.py"]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, f"Migration failed: {proc.stdout}\n{proc.stderr}"

    # Verify schema: 'order' column should be nullable now
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('inventory');")
    rows = cur.fetchall()
    order_col = next(r for r in rows if r[1] == "order")
    # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
    assert order_col[3] == 0  # notnull == 0 means nullable

    # Verify data preserved
    cur.execute('SELECT nome, quantidade, "order" FROM inventory')
    data = cur.fetchall()
    assert data[0][0] == "old"
    conn.close()
