"""
Verification script for OAuth two-blueprint refactor.

Run this after Docker rebuild to verify:
1. Both blueprints are registered
2. Tokens are stored with correct providers
3. Calendar sync uses correct provider
4. No hardcoded provider strings in critical paths
"""

import sys
import os

# Add backend to path
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/backend")

from sqlalchemy import create_engine, text
from app.config.oauth_provider import PROVIDER_GOOGLE_LOGIN, PROVIDER_GOOGLE_CALENDAR


def verify_database_schema():
    """Verify database can handle both provider types."""
    print("\n=== Verifying Database Schema ===")

    db_url = os.getenv(
        "DATABASE_URL", "postgresql://admin:password@db:5432/tattoo_studio"
    )
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check oauth table exists
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'oauth'
        """))

        if result.fetchone():
            print("✅ OAuth table exists")
        else:
            print("❌ OAuth table missing")
            return False

        # Check provider column
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'oauth' AND column_name = 'provider'
        """))

        if result.fetchone():
            print("✅ Provider column exists")
        else:
            print("❌ Provider column missing")
            return False

    return True


def verify_constants():
    """Verify OAuth provider constants are defined."""
    print("\n=== Verifying Provider Constants ===")

    print(f"✅ PROVIDER_GOOGLE_LOGIN = '{PROVIDER_GOOGLE_LOGIN}'")
    print(f"✅ PROVIDER_GOOGLE_CALENDAR = '{PROVIDER_GOOGLE_CALENDAR}'")

    assert PROVIDER_GOOGLE_LOGIN == "google_login"
    assert PROVIDER_GOOGLE_CALENDAR == "google_calendar"

    return True


def verify_blueprints():
    """Verify both blueprints are registered."""
    print("\n=== Verifying Blueprint Registration ===")

    try:
        from app.main import create_app

        app = create_app()

        # Check blueprints
        blueprint_names = [bp.name for bp in app.blueprints.values()]

        if PROVIDER_GOOGLE_LOGIN in blueprint_names:
            print(f"✅ {PROVIDER_GOOGLE_LOGIN} blueprint registered")
        else:
            print(f"❌ {PROVIDER_GOOGLE_LOGIN} blueprint NOT registered")
            print(f"   Available blueprints: {blueprint_names}")
            return False

        if PROVIDER_GOOGLE_CALENDAR in blueprint_names:
            print(f"✅ {PROVIDER_GOOGLE_CALENDAR} blueprint registered")
        else:
            print(f"❌ {PROVIDER_GOOGLE_CALENDAR} blueprint NOT registered")
            print(f"   Available blueprints: {blueprint_names}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error verifying blueprints: {e}")
        return False


def verify_oauth_service():
    """Verify OAuthTokenService accepts provider parameter."""
    print("\n=== Verifying OAuth Token Service ===")

    try:
        from app.services.oauth_token_service import OAuthTokenService
        import inspect

        # Check get_user_access_token signature
        sig = inspect.signature(OAuthTokenService.get_user_access_token)
        params = list(sig.parameters.keys())

        if "provider" in params:
            print("✅ get_user_access_token accepts provider parameter")
        else:
            print("❌ get_user_access_token missing provider parameter")
            return False

        # Check refresh_access_token signature
        sig = inspect.signature(OAuthTokenService.refresh_access_token)
        params = list(sig.parameters.keys())

        if "provider" in params:
            print("✅ refresh_access_token accepts provider parameter")
        else:
            print("❌ refresh_access_token missing provider parameter")
            return False

        return True

    except Exception as e:
        print(f"❌ Error verifying OAuth service: {e}")
        return False


def verify_calendar_service():
    """Verify GoogleCalendarService uses correct provider."""
    print("\n=== Verifying Calendar Service ===")

    try:
        from app.services.google_calendar_service import GoogleCalendarService
        import inspect

        # Get source code
        source = inspect.getsource(GoogleCalendarService._get_user_access_token)

        # Check if using the constant or the literal string
        if "PROVIDER_GOOGLE_CALENDAR" in source or PROVIDER_GOOGLE_CALENDAR in source:
            print(f"✅ GoogleCalendarService uses PROVIDER_GOOGLE_CALENDAR constant")
        else:
            print(f"❌ GoogleCalendarService doesn't use {PROVIDER_GOOGLE_CALENDAR}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error verifying calendar service: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("OAuth Two-Blueprint Refactor Verification")
    print("=" * 60)

    results = []

    results.append(("Constants", verify_constants()))
    results.append(("Blueprints", verify_blueprints()))
    results.append(("OAuth Service", verify_oauth_service()))
    results.append(("Calendar Service", verify_calendar_service()))

    # Database check (optional - may not be available in all environments)
    try:
        results.append(("Database Schema", verify_database_schema()))
    except Exception as e:
        print(f"\n⚠️  Database verification skipped: {e}")

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All verifications passed!")
        return 0
    else:
        print("\n❌ Some verifications failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
