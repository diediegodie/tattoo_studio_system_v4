#!/usr/bin/env python3
"""
Direct test script to debug Google Calendar OAuth token storage and service functionality
This script bypasses web authentication and directly tests our fixes
"""
import os
import sys

# Add the backend directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.logging_config import get_logger

from datetime import datetime
from app.repositories.google_calendar_repo import GoogleCalendarRepository
from app.services.google_calendar_service import GoogleCalendarService
from app.services.oauth_token_service import OAuthTokenService

logger = get_logger(__name__)


def test_oauth_token_retrieval():
    """Test if we can retrieve the OAuth token for user 13"""
    logger.info("Testing OAuth Token Retrieval")

    oauth_service = OAuthTokenService()

    # Test retrieving token for user 13 who has Google OAuth
    [REDACTED_ACCESS_TOKEN]"13")

    if [REDACTED_ACCESS_TOKEN]
            "OAuth access token available",
            extra={
                "context": {
                    "user_id": 13,
                    "token_preview": (
                        access_token[:12] + "..."
                        if len(access_token) > 12
                        else access_token
                    ),
                }
            },
        )
        return True
    else:
        logger.error("No OAuth token found", extra={"context": {"user_id": 13}})
        return False


def test_calendar_service():
    """Test the Google Calendar Service with our debug logging"""
    logger.info("Testing Google Calendar Service")

    try:
        # Initialize services
        calendar_repo = GoogleCalendarRepository()
        calendar_service = GoogleCalendarService(calendar_repo)

        try:
            # Test getting events for user 13
            events = calendar_service.get_user_events(
                "13",
                datetime(2025, 9, 1),
                datetime(2025, 9, 30),
            )

            logger.info(
                "Calendar service returned events",
                extra={"context": {"count": len(events) if events else 0}},
            )
            if events:
                for i, event in enumerate(events[:3]):
                    start_dt = getattr(event, "start_time", None)
                    start_str = start_dt.isoformat() if start_dt is not None else None
                    logger.info(
                        "Sample event",
                        extra={
                            "context": {
                                "index": i + 1,
                                "summary": getattr(event, "title", None),
                                "start": start_str,
                            }
                        },
                    )

            return True

        except Exception as e:
            logger.error(
                "Calendar service failed",
                extra={"context": {"error": str(e)}},
                exc_info=True,
            )
            return False
    finally:
        pass


if __name__ == "__main__":
    logger.info(
        "Debugging Google Calendar OAuth and Sync Issues",
        extra={"context": {"delimiter": "=" * 60}},
    )

    # Test 1: OAuth token retrieval
    token_works = test_oauth_token_retrieval()

    # Test 2: Calendar service (only if token works)
    if token_works:
        calendar_works = test_calendar_service()
    else:
        logger.warning("Skipping calendar service test - no OAuth token")

    logger.info("Debug test completed")
