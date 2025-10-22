import os
import sys
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _is_test_mode():
    """Check if we're running in test mode (pytest/CI)."""
    # Check TESTING env var (set in conftest.py and CI)
    testing_val = os.getenv("TESTING", "").lower().strip()
    if testing_val in ("true", "1", "yes"):
        return True
    # Check if pytest is running
    if "pytest" in sys.modules:
        return True
    # Check PYTEST_CURRENT_TEST (set by pytest during execution)
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    return False


# Global Limiter instance to be imported by controllers
# Note: We use default enabled=True here, and the app's init_app call will
# respect RATE_LIMIT_ENABLED setting for test mode
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=os.getenv("LIMITER_STORAGE_URI", "memory://"),
    enabled=True,  # Will be overridden in main.py based on test mode
)
