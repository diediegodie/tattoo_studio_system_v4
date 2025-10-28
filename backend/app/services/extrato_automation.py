"""
Extrato Automation Service - Monthly automation and background processing.

This module contains the automation logic for monthly extrato generation,
background processing, and scheduling.
"""

import importlib
import logging
import os
import threading
from datetime import datetime

from app.db.base import ExtratoRunLog
from app.db.session import SessionLocal
from app.services.extrato_core import _log_extrato_run

# Configure logging
logger = logging.getLogger(__name__)


def should_run_monthly_extrato():
    """Check if we should run the monthly extrato generation using database tracking.

    This should only run once per month, after the 1st of the month.
    Uses database table instead of file-based tracking for better reliability.
    """
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    # Only run if today is on or after the 1st of the month
    if today.day < 1:  # Should not happen, but safety check
        return False

    # Check database for existing successful run this month
    db = SessionLocal()
    try:
        existing_run = (
            db.query(ExtratoRunLog)
            .filter(
                ExtratoRunLog.mes == current_month,
                ExtratoRunLog.ano == current_year,
                ExtratoRunLog.status == "success",
            )
            .first()
        )

        if existing_run:
            return False  # Already ran successfully this month

        return True

    except Exception as e:
        # If there's any error reading the database, log it but allow the run
        logger.warning(
            "Could not check extrato run history",
            extra={"context": {"error": str(e)}},
        )
        return True
    finally:
        db.close()


def run_extrato_in_background():
    """Run extrato generation in background thread with error handling.

    This is a shared utility function to avoid code duplication between
    main.py and historico_controller.py.
    """
    # Check if background processing is disabled (for testing or CI)
    disable_background = os.getenv(
        "DISABLE_EXTRATO_BACKGROUND", "false"
    ).lower() == "true" or os.getenv("TESTING", "0") in ("1", "true", "True")
    # Try to detect Flask's app.config['TESTING'] if available
    try:
        from flask import current_app

        if getattr(current_app, "config", None) and current_app.config.get("TESTING"):
            disable_background = True
    except Exception:
        pass

    if disable_background:
        logger.info(
            "Extrato background job muted due to TESTING or DISABLE_EXTRATO_BACKGROUND."
        )
        return

    # Run in background thread
    def run_extrato_generation():
        try:
            # Resolve the function at call time so tests that patch app.services.extrato_generation.check_and_generate_extrato are effective
            extrato_gen = importlib.import_module("app.services.extrato_generation")
            # add structured context before starting (tests assert presence of 'monthly_extrato')
            logger.info(
                "Starting scheduled extrato generation",
                extra={"context": {"job": "monthly_extrato"}},
            )
            extrato_gen.check_and_generate_extrato()
        except Exception as e:
            # Use the exact message the unit test asserts and include structured context
            logger.error(
                "Error in scheduled extrato generation",
                extra={"context": {"job": "monthly_extrato", "error": str(e)}},
                exc_info=True,
            )

    # Start background thread
    thread = threading.Thread(target=run_extrato_generation, daemon=True)
    thread.start()
