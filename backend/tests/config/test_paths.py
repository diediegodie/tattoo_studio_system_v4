"""
Test path resolution and environment setup.

This module ensures that all domain modules are properly importable
during test execution by setting up the correct Python paths.
"""

import os
import sys
from pathlib import Path


class TestPathResolver:
    """Handles Python path setup for test execution."""

    @staticmethod
    def get_backend_app_path() -> str:
        """Get the absolute path to the backend app directory."""
        # Get the directory containing this file (tests/config/)
        current_dir = Path(__file__).parent

        # Navigate to backend/app/
        backend_app_path = current_dir.parent.parent / "app"

        return str(backend_app_path.resolve())

    @staticmethod
    def get_backend_root_path() -> str:
        """Get the absolute path to the backend root directory."""
        current_dir = Path(__file__).parent
        backend_root_path = current_dir.parent.parent
        return str(backend_root_path.resolve())

    @staticmethod
    def setup_app_imports():
        """Add backend app directory to Python path for domain imports."""
        app_path = TestPathResolver.get_backend_app_path()

        if app_path not in sys.path:
            sys.path.insert(0, app_path)
            print(f"Added to Python path: {app_path}")

    @staticmethod
    def setup_backend_imports():
        """Add backend root directory to Python path for test imports."""
        backend_path = TestPathResolver.get_backend_root_path()

        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
            print(f"Added to Python path: {backend_path}")

    @staticmethod
    def setup_all_paths():
        """Set up all necessary paths for test execution."""
        TestPathResolver.setup_backend_imports()
        TestPathResolver.setup_app_imports()

    @staticmethod
    def verify_imports():
        """Verify that critical modules can be imported."""
        import_results = {
            "controllers.appointment_controller": False,
            "services.user_service": False,
            "repositories.user_repo": False,
            "schemas.dtos": False,
            "core.security": False,
        }

        for module_name in import_results.keys():
            try:
                __import__(module_name)
                import_results[module_name] = True
            except (ImportError, KeyError):
                import_results[module_name] = False

        return import_results

    @staticmethod
    def print_python_path():
        """Print current Python path for debugging."""
        print("Current Python path:")
        for i, path in enumerate(sys.path):
            print(f"  {i}: {path}")


def setup_test_environment():
    """
    Main function to set up the test environment.

    This should be called at the beginning of conftest.py or
    any test module that needs domain imports.
    """
    print("Setting up test environment...")

    # Set up all necessary paths
    TestPathResolver.setup_all_paths()

    # Verify imports work
    import_results = TestPathResolver.verify_imports()

    # Report results
    successful_imports = sum(import_results.values())
    total_imports = len(import_results)

    print(
        f"Import verification: {successful_imports}/{total_imports} modules importable"
    )

    for module_name, success in import_results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {module_name}")

    if successful_imports < total_imports:
        print("\nWARNING: Some modules could not be imported. Tests may fail.")
        TestPathResolver.print_python_path()

    return import_results


# Convenience function for use in other modules
def ensure_domain_imports():
    """Ensure domain modules can be imported. Call this before importing domain modules."""
    TestPathResolver.setup_all_paths()


if __name__ == "__main__":
    # Allow running this module directly for testing
    print("Testing path resolution...")
    setup_test_environment()
