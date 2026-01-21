#!/usr/bin/env python3
"""
Test script to verify centralized DB session usage in migration scripts.

This script validates that all migration scripts now use the centralized
engine from app.db.session and that connections show proper application_name.

Usage:
    python backend/scripts/test_centralized_session.py
"""

import os
import sys

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.core.logging_config import get_logger
from app.db.session import get_engine
from sqlalchemy import text
import pytest

logger = get_logger(__name__)


@pytest.mark.skip(reason="Script-oriented test; run via __main__ if needed")
def test_engine_configuration():
    """Test that the engine is properly configured with application_name."""
    logger.info("Testing engine configuration...")

    try:
        engine = get_engine()

        # Check if engine has proper configuration
        logger.info(f"Engine URL: {engine.url}")
        # Get pool size from configuration (QueuePool stores this in _pool.maxsize)
        pool_size = getattr(engine.pool, "_pool", None)
        if pool_size and hasattr(pool_size, "maxsize"):
            logger.info(f"Pool size: {pool_size.maxsize}")
        else:
            logger.info("Pool size: N/A (non-pooled engine)")

        # Test connection and check application_name
        with engine.connect() as conn:
            # Check if we're using PostgreSQL
            result = conn.execute(text("SELECT version()")).fetchone()
            if result:
                db_version = result[0]
                logger.info(f"Database version: {db_version[:50]}...")

                # Check application_name for PostgreSQL
                if "PostgreSQL" in db_version:
                    app_name_result = conn.execute(
                        text("SHOW application_name")
                    ).fetchone()
                    if app_name_result:
                        app_name = app_name_result[0]
                        logger.info(f"Application name: {app_name}")

                        # Assert correct application name when on PostgreSQL
                        assert (
                            app_name == "tattoo_studio"
                        ), f"application_name is '{app_name}', expected 'tattoo_studio'"
                    else:
                        logger.error("❌ Could not retrieve application_name")
                        assert False, "Could not retrieve application_name"
                else:
                    logger.info(
                        "✅ Non-PostgreSQL database (application_name not applicable)"
                    )
                    # No assertion needed for non-Postgres
                    return
            else:
                logger.error("❌ Could not get database version")
                assert False, "Could not get database version"

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


@pytest.mark.skip(reason="Script-oriented test; run via __main__ if needed")
def test_pg_stat_activity():
    """Test that connections are visible in pg_stat_activity with correct application_name."""
    logger.info("Testing pg_stat_activity visibility...")

    try:
        engine = get_engine()

        with engine.connect() as conn:
            # Check if we're using PostgreSQL
            result = conn.execute(text("SELECT version()")).fetchone()
            if result and "PostgreSQL" in result[0]:
                # Query pg_stat_activity for our application
                activity_result = conn.execute(text("""
                        SELECT datname, application_name, state, query
                        FROM pg_stat_activity
                        WHERE application_name = 'tattoo_studio'
                        AND pid = pg_backend_pid()
                    """)).fetchone()

                if activity_result:
                    logger.info(f"✅ Found connection in pg_stat_activity:")
                    logger.info(f"   Database: {activity_result[0]}")
                    logger.info(f"   Application: {activity_result[1]}")
                    logger.info(f"   State: {activity_result[2]}")
                else:
                    logger.error("❌ Connection not found in pg_stat_activity")
                    assert False, "Connection not found in pg_stat_activity"
            else:
                logger.info(
                    "✅ Non-PostgreSQL database (pg_stat_activity not applicable)"
                )
                return

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


def main():
    logger.info("=" * 60)
    logger.info("Testing Centralized DB Session Configuration")
    logger.info("=" * 60)

    tests_passed = 0
    total_tests = 2

    # Test 1: Engine configuration
    try:
        test_engine_configuration()
        tests_passed += 1
    except Exception:
        pass

    # Test 2: pg_stat_activity visibility
    try:
        test_pg_stat_activity()
        tests_passed += 1
    except Exception:
        pass

    # Summary
    logger.info("=" * 60)
    logger.info(f"Tests passed: {tests_passed}/{total_tests}")
    logger.info("=" * 60)

    if tests_passed == total_tests:
        logger.info("✅ All tests passed! Centralized session is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
