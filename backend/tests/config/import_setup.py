"""
Import path management for tests following Single Responsibility Principle.

This module handles all import path setup for tests, ensuring consistent
import behavior across the entire test suite.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional


class TestImportManager:
    """Manages import paths for test execution."""

    _instance: Optional["TestImportManager"] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern to ensure single import setup."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize import manager."""
        if not self._initialized:
            self._setup_paths()
            self._initialized = True

    def _setup_paths(self):
        """Setup import paths for the application."""
        # Get the test directory (where this file is located)
        test_dir = Path(__file__).parent.parent

        # Get the backend directory
        backend_dir = test_dir.parent

        # Add backend directory to sys.path to allow `import app.xxx`.
        # Also add backend/app so top-level imports like `db` (which lives
        # under app/db) can be imported as `db.*`. The order matters: add
        # the backend root first so `app` resolves to the package directory
        # rather than a file that may live inside it.
        backend_app_dir = test_dir / "app"

        paths_to_add = [
            str(backend_dir),  # For importing from 'app' package
            str(backend_app_dir),  # For allowing top-level `db`, etc.
        ]

        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)

        # When running tests locally, prefer a SQLite file-based database so
        # test runs don't attempt to reach the production Postgres host.
        # Only set this if DATABASE_URL isn't already provided by CI/ENV.
        if "DATABASE_URL" not in os.environ:
            tmp_db = Path(tempfile.gettempdir()) / "tattoo_test.sqlite"
            os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db}"
            print(f"Added to Python path: {paths_to_add[0]}")

    @staticmethod
    def ensure_imports_available():
        """Ensure all required imports are available."""
        try:
            # Prefer importing modules using the application's real package layout
            # Try non-'app' package imports first (controllers, services, domain),
            # fall back to 'app.*' for compatibility with legacy tests.
            try:
                import app.repositories.user_repo as _
                import app.schemas.dtos as _
                import app.services.user_service as _
                import domain.entities as _
                import domain.interfaces as _

                return True
            except ImportError:
                # Fallback to legacy 'app' package imports - attempt but don't raise
                try:
                    import app.domain.entities as _
                    import app.domain.interfaces as _
                    import app.repositories.user_repo as _
                    import app.schemas.dtos as _
                    import app.services.user_service as _

                    return True
                except Exception:
                    # If even fallback fails, return False so tests can skip gracefully
                    return False
        except ImportError as e:
            print(f"Warning: Import setup failed: {e}")
            return False

    @classmethod
    def setup_for_testing(cls):
        """Main entry point for setting up imports in tests."""
        manager = cls()
        return manager.ensure_imports_available()


def setup_test_imports() -> bool:
    """
    Convenience function to setup imports for tests.

    Returns:
        bool: True if imports are successfully set up, False otherwise.
    """
    return TestImportManager.setup_for_testing()


def get_app_root() -> Path:
    """Get the root directory of the app package."""
    return Path(__file__).parent.parent.parent / "app"


def get_test_root() -> Path:
    """Get the root directory of the test package."""
    return Path(__file__).parent.parent


def get_backend_root() -> Path:
    """Get the root directory of the backend package."""
    return Path(__file__).parent.parent.parent


# Setup imports when this module is imported
setup_test_imports()
