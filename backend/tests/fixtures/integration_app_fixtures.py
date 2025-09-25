"""
Flask application fixtures for integration testing.

This module provides Flask app setup, test client, and test runner fixtures
for integration tests.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    # Quick availability check for Flask and SQLAlchemy. Do NOT import
    # application modules that may create engines at module import time.
    from datetime import datetime, timedelta, timezone

    import flask  # type: ignore
    import jwt
    from sqlalchemy import text  # type: ignore

    FLASK_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Flask integration dependencies not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False


@pytest.fixture(scope="function")
def app(test_database):
    """Create a Flask application configured for testing."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Configure environment for testing so create_app() and db.session pick up the
    # test database and secrets. Some versions of create_app accepted a config
    # dict; newer versions take no args, so we set env vars and call create_app().
    os.environ["DATABASE_URL"] = test_database
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    # After setting DATABASE_URL, reload db.session so its engine/SessionLocal
    # are created against the test database URL (important because db.session
    # may have been imported earlier during test collection).
    import importlib

    # Ensure DATABASE_URL is set before importing application modules so
    # any lazy engine creation or imports in app.main/db.session pick up the
    # test database. Reload db.session after setting env var below.
    try:
        # Import create_app lazily after env is set
        from importlib import import_module

        import_module("app.app")
        import_module("app.app")
    except Exception:
        # ignore for environments where app package isn't importable
        pass

    # Reload session module so it reads the test DATABASE_URL when later used
    try:
        import app.db.session as db_session_mod

        importlib.reload(db_session_mod)
    except Exception:
        pass

    # Now import the app factory
    from app.app import create_app

    app = create_app()

    # Fix template/static paths for test environment: create_app() uses
    # absolute Docker paths (/app/frontend/...), which are not present during
    # local pytest runs. Point Flask to the repo's frontend folders so
    # Jinja can find templates and static assets.
    from pathlib import Path

    repo_root = Path(__file__).parent.parent.parent.parent.resolve()
    templates_path = repo_root / "frontend" / "templates"
    static_path = repo_root / "frontend" / "assets"

    if templates_path.exists():
        app.template_folder = str(templates_path)
        # Ensure the jinja loader search path includes the repo templates
        try:
            loader = getattr(app, "jinja_loader", None)
            # Guard against None loader and ensure searchpath exists and is handled safely
            if loader is not None and hasattr(loader, "searchpath"):
                sp = loader.searchpath
                if sp is None:
                    # If searchpath is None, set a new list with our templates path
                    try:
                        loader.searchpath = [str(templates_path)]
                    except Exception:
                        # Non-fatal for custom loaders that don't allow assignment
                        pass
                else:
                    try:
                        # Prefer to insert into a mutable sequence
                        sp.insert(0, str(templates_path))
                    except Exception:
                        # Fallback: replace with a new list combining paths
                        try:
                            loader.searchpath = [str(templates_path)] + list(sp)
                        except Exception:
                            # Non-fatal for environments with custom loaders
                            pass
        except Exception:
            # Non-fatal for environments with custom loaders
            pass

    if static_path.exists():
        app.static_folder = str(static_path)

    # During tests surface internal exceptions to make debugging easier
    app.config["PROPAGATE_EXCEPTIONS"] = True

    # Explicit test config applied to the Flask app object
    app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Create application context and ensure the db tables exist on the
    # SessionLocal/engine that the application code uses.
    with app.app_context():
        # Import the session module lazily (should now honor DATABASE_URL)
        from app.db import session as db_session_mod
        from app.db.base import Base

        # Use the engine from db.session (reloaded above) so tests and
        # application share the same database connection. Prefer calling
        # get_engine() when available so we get a real SQLAlchemy Engine
        # (the session module may expose a proxy for compatibility).
        if hasattr(db_session_mod, "get_engine"):
            test_engine = db_session_mod.get_engine()
        else:
            test_engine = getattr(db_session_mod, "engine", None)

        if test_engine is None:
            # Fallback: create a direct engine to the test DB
            from sqlalchemy import create_engine

            test_engine = create_engine(test_database)

        # Defensive: also create a direct engine from the same URL and
        # create tables there too. This helps when there are subtle
        # differences between proxied engines and direct ones.
        try:
            from sqlalchemy import create_engine

            direct_engine = create_engine(test_database)
        except Exception:
            direct_engine = test_engine

        # Log engine URLs for debugging
        try:
            print(
                f"[DEBUG] session engine URL: {getattr(test_engine, 'url', test_engine)}"
            )
            print(
                f"[DEBUG] direct engine URL: {getattr(direct_engine, 'url', direct_engine)}"
            )
        except Exception:
            pass

        Base.metadata.create_all(test_engine)
        if direct_engine is not test_engine:
            Base.metadata.create_all(direct_engine)

        # Defensive: If other modules already imported their own db.session
        # (likely during test collection), create tables on those engines too.
        import sys

        for mod_name, mod in list(sys.modules.items()):
            if mod_name.endswith(".db.session") or mod_name == "db.session":
                try:
                    eng = getattr(mod, "get_engine", None)
                    if callable(eng):
                        eng = eng()
                    else:
                        eng = getattr(mod, "engine", None)
                    if eng is not None:
                        try:
                            Base.metadata.create_all(eng)
                            print(
                                f"[DEBUG] Created tables on engine from module {mod_name}"
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

        yield app

        # Cleanup tables
        Base.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the Flask application."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create a test runner for the Flask application."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    return app.test_cli_runner()
