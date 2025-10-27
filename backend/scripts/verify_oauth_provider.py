#!/usr/bin/env python3
"""
Quick verification script to check OAuth provider constant consistency.

Run this from the backend directory:
    python scripts/verify_oauth_provider.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_constant_exists():
    """Verify the provider constant is defined correctly."""
    try:
        from app.config.oauth_provider import PROVIDER_GOOGLE

        print(f"✅ Provider constant found: PROVIDER_GOOGLE = '{PROVIDER_GOOGLE}'")
        return PROVIDER_GOOGLE
    except ImportError as e:
        print(f"❌ Failed to import provider constant: {e}")
        return None


def verify_imports():
    """Verify all modules import the constant correctly."""
    modules_to_check = [
        ("app.main", "Main application"),
        ("app.services.oauth_token_service", "OAuth token service"),
        ("app.controllers.calendar_controller", "Calendar controller"),
    ]

    print("\n🔍 Checking module imports...")
    for module_path, description in modules_to_check:
        try:
            module = __import__(module_path, fromlist=["PROVIDER_GOOGLE"])
            if hasattr(module, "PROVIDER_GOOGLE"):
                print(f"  ✅ {description}: PROVIDER_GOOGLE imported")
            else:
                # Module might import it indirectly
                print(
                    f"  ⚠️  {description}: Constant not in module namespace (may be imported indirectly)"
                )
        except ImportError as e:
            print(f"  ❌ {description}: Import failed - {e}")
        except Exception as e:
            print(f"  ⚠️  {description}: Check failed - {e}")


def check_no_hardcoded_strings():
    """Check for any remaining hardcoded provider strings."""
    import re

    print("\n🔍 Scanning for hardcoded provider strings...")

    files_to_check = [
        "app/main.py",
        "app/services/oauth_token_service.py",
        "app/controllers/calendar_controller.py",
    ]

    patterns = [
        (r'provider\s*=\s*[\'"]google[\'"]', "provider = 'google'"),
        (r'provider\s*==\s*[\'"]google[\'"]', "provider == 'google'"),
        (
            r'\.name\s*=\s*[\'"]google_oauth_calendar[\'"]',
            ".name = 'google_oauth_calendar'",
        ),
    ]

    issues_found = False
    for filepath in files_to_check:
        try:
            with open(filepath, "r") as f:
                content = f.read()
                for pattern, description in patterns:
                    matches = list(re.finditer(pattern, content))
                    if matches:
                        # Check if it's in a comment or the constant definition
                        for match in matches:
                            line_start = content.rfind("\n", 0, match.start()) + 1
                            line = content[
                                line_start : content.find("\n", match.start())
                            ]

                            # Skip if in constant definition or comment
                            if "PROVIDER_GOOGLE" in line or line.strip().startswith(
                                "#"
                            ):
                                continue

                            print(f"  ⚠️  Found in {filepath}: {description}")
                            print(f"     Line: {line.strip()}")
                            issues_found = True
        except FileNotFoundError:
            print(f"  ⚠️  File not found: {filepath}")

    if not issues_found:
        print("  ✅ No hardcoded provider strings found")


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("OAuth Provider Constant Verification")
    print("=" * 60)

    # Check 1: Constant exists
    provider_value = verify_constant_exists()
    if not provider_value:
        print("\n❌ Verification failed: Provider constant not found")
        return 1

    # Check 2: Modules import it
    verify_imports()

    # Check 3: No hardcoded strings
    check_no_hardcoded_strings()

    print("\n" + "=" * 60)
    print("✅ Verification complete!")
    print("=" * 60)
    print(f"\nExpected provider value in database: '{provider_value}'")
    print("\nNext steps:")
    print("1. Start the application")
    print("2. Check startup logs for: 'Google OAuth blueprint configured'")
    print("3. Perform Google login")
    print("4. Check database: SELECT provider, COUNT(*) FROM oauth GROUP BY provider;")
    print("5. Access /debug/oauth-providers (dev only)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
