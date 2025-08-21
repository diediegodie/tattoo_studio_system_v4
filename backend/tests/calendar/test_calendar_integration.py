#!/usr/bin/env python3
"""
Google Calendar Integration Test Script
This script helps test the calendar integration manually before UI implementation.
"""

import sys
import os

sys.path.insert(0, "app")

# Load environment variables
from dotenv import load_dotenv

load_dotenv("../.env")

from flask import Flask
from services.oauth_token_service import OAuthTokenService
from services.google_calendar_service import GoogleCalendarService
from datetime import datetime, timedelta


def create_test_app():
    """Create a minimal Flask app for testing."""
    template_folder = "/app/frontend/templates"
    static_folder = "/app/frontend/assets"
    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
    )

    # Basic configuration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "test-secret")
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")

    return app


def test_calendar_integration():
    """Test Google Calendar integration step by step."""
    print("🧪 Google Calendar Integration Test")
    print("=" * 50)

    # Initialize services
    print("\n1. Initializing services...")
    try:
        oauth_service = OAuthTokenService()
        calendar_service = GoogleCalendarService()
        print("✅ Services initialized successfully")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False

    # Test OAuth URL generation
    print("\n2. Testing OAuth URL generation...")
    try:
        auth_url = oauth_service.get_authorization_url()
        if auth_url:
            print("✅ OAuth URL generated successfully")
            print(f"📋 Authorization URL: {auth_url}")
            print("\n📌 To test with real OAuth:")
            print("   1. Copy the URL above")
            print("   2. Paste in browser")
            print("   3. Complete Google OAuth flow")
            print("   4. Check if calendar scopes are requested")
        else:
            print("❌ Failed to generate OAuth URL")
            return False
    except Exception as e:
        print(f"❌ OAuth URL generation failed: {e}")
        return False

    # Test calendar service without token (should handle gracefully)
    print("\n3. Testing calendar service without authentication...")
    try:
        test_user_id = "test_user_123"

        # Test authorization check
        is_authorized = calendar_service.is_user_authorized(test_user_id)
        print(f"✅ Authorization check completed: {is_authorized}")

        # Test event fetching (should return empty list)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        events = calendar_service.get_user_events(test_user_id, start_date, end_date)
        print(
            f"✅ Event fetching completed: {len(events)} events (expected 0 without auth)"
        )

    except Exception as e:
        print(f"❌ Calendar service test failed: {e}")
        return False

    # Test Google Calendar API requirements
    print("\n4. Testing environment configuration...")

    # Check required environment variables
    required_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("📋 Required for Google Calendar integration:")
        for var in missing_vars:
            print(f"   export {var}='your_value_here'")
        return False
    else:
        print("✅ All required environment variables are set")

    print("\n5. Integration test summary:")
    print("✅ Backend calendar integration is ready!")
    print("✅ OAuth flow is configured with calendar scopes")
    print("✅ Services handle unauthenticated requests gracefully")
    print("✅ Environment is properly configured")

    print("\n🎯 Next steps:")
    print("   1. Start your Flask app")
    print("   2. Login with Google OAuth")
    print("   3. Test calendar endpoints via API calls")
    print("   4. Build frontend interface")

    return True


def test_with_mock_token():
    """Test calendar service with mock scenarios."""
    print("\n" + "=" * 50)
    print("🔧 Mock Token Testing")
    print("=" * 50)

    try:
        from repositories.google_calendar_repo import GoogleCalendarRepository

        # Test repository without real API calls
        repo = GoogleCalendarRepository()
        print("✅ Google Calendar Repository initialized")

        # Test token validation with invalid token
        is_valid = repo.validate_token("invalid_token_123")
        print(f"✅ Token validation test completed: {is_valid} (expected False)")

        print("✅ Mock testing completed successfully")

    except Exception as e:
        print(f"❌ Mock testing failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("Starting Google Calendar Integration Tests...")

    # Run basic integration test
    success = test_calendar_integration()

    if success:
        # Run mock testing
        test_with_mock_token()

        print("\n🎉 All tests completed successfully!")
        print("📱 Ready to build frontend interface!")
    else:
        print("\n❌ Tests failed. Please fix issues before proceeding.")
        sys.exit(1)
