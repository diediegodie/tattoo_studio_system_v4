import importlib
import runpy
import sys
import types
from unittest.mock import MagicMock

import pytest


SCRIPT_PATH = "scripts/migrate_inventory_order.py"


def _make_engine_mock(dialect_name="postgresql"):
    engine = MagicMock()
    engine.dialect = types.SimpleNamespace(name=dialect_name)

    # context manager for connect()
    conn_cm = MagicMock()
    conn = MagicMock()
    conn_cm.__enter__.return_value = conn
    conn_cm.__exit__.return_value = False
    engine.connect.return_value = conn_cm

    # context manager for begin()
    begin_cm = MagicMock()
    begin_conn = MagicMock()
    begin_cm.__enter__.return_value = begin_conn
    begin_cm.__exit__.return_value = False
    engine.begin.return_value = begin_cm

    return engine, conn, begin_conn


def _install_mock_session_module(engine):
    mod = types.ModuleType("app.db.session")
    mod.engine = engine
    sys.modules["app.db.session"] = mod


def test_migration_successful_postgres(monkeypatch):
    engine, conn, _ = _make_engine_mock("postgresql")

    # inspector returns that inventory table exists and has 'order' column
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["inventory"]
    inspector.get_columns.return_value = [{"name": "id"}, {"name": "order"}]

    # patch sqlalchemy.inspect to return our inspector
    import sqlalchemy as sa

    monkeypatch.setattr(sa, "inspect", lambda eng: inspector)

    # provide mocked engine module
    _install_mock_session_module(engine)

    # Run the script
    # Use runpy so the module-level code executes against our mocked objects
    runpy.run_path(SCRIPT_PATH, run_name="__main__")

    # For postgres, ensure we entered a connect() context and executed SQL
    engine.connect.assert_called()
    entered_conn = engine.connect.return_value.__enter__.return_value
    assert entered_conn.execute.called


def test_migration_successful_sqlite(monkeypatch):
    engine, conn, begin_conn = _make_engine_mock("sqlite")

    # inspector shows table exists and has 'order'
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["inventory"]
    inspector.get_columns.return_value = [
        {"name": "id"},
        {"name": "order"},
    ]

    monkeypatch.setattr("sqlalchemy.inspect", lambda eng: inspector)

    # Make PRAGMA table_info return expected structure via begin_conn.execute
    # pragma result: list of tuples (cid, name, type, notnull, dflt_value, pk)
    pragma_rows = [
        (0, "id", "INTEGER", 1, None, 1),
        (1, "order", "INTEGER", 1, "0", 0),
    ]

    class Result:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    def begin_execute(sql):
        s = str(sql).lower()
        if "pragma table_info" in s:
            return Result(pragma_rows)
        return MagicMock()

    begin_conn.execute.side_effect = begin_execute

    _install_mock_session_module(engine)

    runpy.run_path(SCRIPT_PATH, run_name="__main__")

    # ensure begin() was used and execute was called (table recreation flow)
    engine.begin.assert_called()
    assert begin_conn.execute.called


def test_migration_already_applied(monkeypatch):
    # When 'order' is present, script should not attempt to add column
    engine, conn, _ = _make_engine_mock("sqlite")
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["inventory"]
    inspector.get_columns.return_value = [{"name": "id"}, {"name": "order"}]

    monkeypatch.setattr("sqlalchemy.inspect", lambda eng: inspector)
    _install_mock_session_module(engine)

    runpy.run_path(SCRIPT_PATH, run_name="__main__")

    # ensure ALTER TABLE ADD COLUMN was NOT called on the simple connect path
    calls = [str(c) for c in conn.execute.call_args_list]
    assert not any('ADD COLUMN "order"' in c for c in calls)


def test_migration_error_handling(monkeypatch):
    engine, conn, _ = _make_engine_mock("postgresql")
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["inventory"]
    inspector.get_columns.return_value = [{"name": "id"}, {"name": "order"}]

    monkeypatch.setattr("sqlalchemy.inspect", lambda eng: inspector)

    # make the connect.__enter__().execute raise
    conn.execute.side_effect = RuntimeError("boom")

    _install_mock_session_module(engine)

    with pytest.raises(Exception):
        runpy.run_path(SCRIPT_PATH, run_name="__main__")
