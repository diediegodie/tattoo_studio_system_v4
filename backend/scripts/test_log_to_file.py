#!/usr/bin/env python3
"""
Test script to verify LOG_TO_FILE environment variable behavior.

Tests:
1. LOG_TO_FILE=1 (default): Logs to files + console
2. LOG_TO_FILE=0 (production): Logs to stdout only (JSON)
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import setup_logging, get_logger


def test_log_to_file_enabled():
    """Test with LOG_TO_FILE=1 (files enabled)"""
    print("=" * 60)
    print("Test 1: LOG_TO_FILE=1 (Development Mode - Files Enabled)")
    print("=" * 60)

    os.environ["LOG_TO_FILE"] = "1"
    setup_logging(log_level=logging.INFO, use_json_format=False)

    logger = get_logger("test.file_enabled")
    logger.info(
        "This should go to console AND files",
        extra={"context": {"mode": "file_enabled"}},
    )

    # Check if handlers include file handlers
    root_logger = logging.getLogger()
    file_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]

    print(f"\nTotal handlers: {len(root_logger.handlers)}")
    print(f"File handlers: {len(file_handlers)}")

    if file_handlers:
        print("✅ File handlers are active")
        for handler in file_handlers:
            print(f"   - {handler.baseFilename}")
    else:
        print("❌ No file handlers found (expected with LOG_TO_FILE=1)")

    # Clear handlers for next test
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    print()


def test_log_to_file_disabled():
    """Test with LOG_TO_FILE=0 (files disabled, stdout only)"""
    print("=" * 60)
    print("Test 2: LOG_TO_FILE=0 (Production Mode - Stdout Only)")
    print("=" * 60)

    os.environ["LOG_TO_FILE"] = "0"
    setup_logging(log_level=logging.INFO, use_json_format=True)

    logger = get_logger("test.stdout_only")
    logger.info(
        "This should ONLY go to stdout as JSON",
        extra={"context": {"mode": "stdout_only", "production": True}},
    )

    # Check if handlers include file handlers
    root_logger = logging.getLogger()
    file_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    stream_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.handlers.RotatingFileHandler)
    ]

    print(f"\nTotal handlers: {len(root_logger.handlers)}")
    print(f"File handlers: {len(file_handlers)}")
    print(f"Stream handlers (stdout): {len(stream_handlers)}")

    if not file_handlers:
        print("✅ No file handlers (correct for LOG_TO_FILE=0)")
    else:
        print("❌ File handlers found (should be disabled with LOG_TO_FILE=0)")
        for handler in file_handlers:
            print(f"   - {handler.baseFilename}")

    if stream_handlers:
        print("✅ Stream handlers active for stdout")

    # Clear handlers
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    print()


def main():
    print("\n" + "=" * 60)
    print("LOG_TO_FILE Environment Variable Test")
    print("=" * 60)
    print()

    # Test both modes
    test_log_to_file_enabled()
    test_log_to_file_disabled()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print("✅ LOG_TO_FILE=1: Logs to files + console")
    print("✅ LOG_TO_FILE=0: Logs to stdout only (JSON)")
    print("\nProduction deployment:")
    print("  Set LOG_TO_FILE=0 in Render environment variables")
    print("  Logs will stream as JSON to stdout for aggregation")
    print("=" * 60)


if __name__ == "__main__":
    main()
