"""
Import path management for tests following Single Responsibility Principle.

This module handles all import path setup for tests, ensuring consistent
import behavior across the entire test suite.
"""

import sys
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

        # Get the app directory
        app_dir = backend_dir / "app"

        # Add paths to sys.path if not already present
        paths_to_add = [
            str(backend_dir),  # For importing from 'app' package
            str(app_dir),  # For direct imports from app modules
        ]

        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)

    @staticmethod
    def ensure_imports_available():
        """Ensure all required imports are available."""
        try:
            # Test critical imports
            import app.domain.entities
            import app.domain.interfaces
            import app.repositories.user_repo
            import app.services.user_service
            import app.schemas.dtos

            return True
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
