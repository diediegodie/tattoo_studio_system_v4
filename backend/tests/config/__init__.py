"""
Test configuration package initialization.

Exports main configuration classes and setup functions for easy import
across the test suite.
"""

from .import_setup import TestImportManager, setup_test_imports
from .test_config import TestConfig, TestData, TestMarkers

# Ensure imports are set up when this package is imported
setup_test_imports()

__all__ = [
    "TestConfig",
    "TestData",
    "TestMarkers",
    "setup_test_imports",
    "TestImportManager",
]
