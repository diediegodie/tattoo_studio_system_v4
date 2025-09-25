#!/usr/bin/env python3
"""
Direct test script to debug Google Calendar OAuth token storage and service functionality
This script bypasses web authentication and directly tests our fixes
"""
import os
import sys

# Add the backend directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import logging

from app.db.session import SessionLocal
from app.repositories.google_calendar_repo import GoogleCalendarRepository
from app.services.google_calendar_service import GoogleCalendarService
from app.services.oauth_token_service import OAuthTokenService

# Configure logging to see our debug messages
logging.basicConfig(level=logging.DEBUG)


def test_oauth_token_retrieval():
    """Test if we can retrieve the OAuth token for user 13"""
    print("=== Testing OAuth Token Retrieval ===")

    db_session = SessionLocal()
    try:
        oauth_service = OAuthTokenService(db_session)

        # Test retrieving token for user 13 who has Google OAuth
        token = oauth_service.get_user_oauth_token(13, "google")

        if token:
            print(f"✅ OAuth token found for user 13")
            print(f"   Provider: {token.provider}")
            print(f"   Provider User ID: {token.provider_user_id}")
            print(
                f"   Token expires at: {getattr(token, 'expires_at', 'No expiration info')}"
            )
            return True
        else:
            print("❌ No OAuth token found for user 13")
            return False
    finally:
        db_session.close()


def test_calendar_service():
    """Test the Google Calendar Service with our debug logging"""
    print("\n=== Testing Google Calendar Service ===")

    db_session = SessionLocal()
    try:
        # Initialize services
        oauth_service = OAuthTokenService(db_session)
        calendar_repo = GoogleCalendarRepository()
        calendar_service = GoogleCalendarService(calendar_repo, oauth_service)

        try:
            # Test getting events for user 13
            events = calendar_service.get_user_events(13, "2025-09-01", "2025-09-30")

            print(f"✅ Calendar service returned {len(events) if events else 0} events")
            if events:
                print("   Sample events:")
                for i, event in enumerate(events[:3]):  # Show first 3 events
                    print(
                        f"   {i+1}. {event.get('summary', 'No title')} - {event.get('start', {}).get('dateTime', 'No time')}"
                    )

            return True

        except Exception as e:
            print(f"❌ Calendar service failed: {str(e)}")
            return False
    finally:
        db_session.close()


if __name__ == "__main__":
    print("🔍 Debugging Google Calendar OAuth and Sync Issues")
    print("=" * 60)

    # Test 1: OAuth token retrieval
    token_works = test_oauth_token_retrieval()

    # Test 2: Calendar service (only if token works)
    if token_works:
        calendar_works = test_calendar_service()
    else:
        print("\n⚠️  Skipping calendar service test - no OAuth token")

    print("\n" + "=" * 60)
    print("🏁 Debug test completed")
