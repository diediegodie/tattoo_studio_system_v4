#!/usr/bin/env python3
"""
Simple Google Calendar Integration Test
"""

import sys
import os

sys.path.insert(0, "app")

# Load environment variables
from dotenv import load_dotenv

load_dotenv("../.env")


def test_basic_integration():
    """Basic integration test."""
    print("🧪 Basic Calendar Integration Test")
    print("=" * 40)

    # Test 1: Environment Configuration
    print("\n1. Testing environment...")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_[REDACTED_SECRET]"GOOGLE_CLIENT_SECRET")

    if client_id and client_[REDACTED_SECRET]"✅ Google OAuth credentials found")
        print(f"   Client ID: {client_id[:20]}...")
    else:
        print("❌ Missing Google OAuth credentials")
        return False

    # Test 2: Import Check
    print("\n2. Testing imports...")
    try:
        from app.domain.entities import CalendarEvent
        from app.domain.interfaces import ICalendarService
        from app.services.google_calendar_service import GoogleCalendarService
        from app.controllers.calendar_controller import calendar_bp

        print("✅ All calendar modules import successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

    # Test 3: Service Creation
    print("\n3. Testing service creation...")
    try:
        from app.services.google_calendar_service import GoogleCalendarService

        calendar_service = GoogleCalendarService()
        print("✅ Calendar service created successfully")
    except Exception as e:
        print(f"❌ Service creation error: {e}")
        return False

    # Test 4: Domain Entity
    print("\n4. Testing domain entity...")
    try:
        from datetime import datetime

        event = CalendarEvent(
            id="test_123",
            title="Test Event",
            start_time=datetime.now(),
            end_time=datetime.now(),
            user_id=1,
        )
        print("✅ CalendarEvent entity created successfully")
        print(f"   Event duration: {event.duration_minutes} minutes")
    except Exception as e:
        print(f"❌ Domain entity error: {e}")
        return False

    print("\n✅ Basic integration test passed!")
    print("\n🎯 Next: Test with Flask app running")
    return True

    # ...existing code...
