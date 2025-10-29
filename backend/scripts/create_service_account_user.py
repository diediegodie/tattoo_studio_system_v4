#!/usr/bin/env python3
"""
Manually create the service account user in the production database.

Run this script after deploying the code with the seed function,
or if you need to ensure the user exists before the next deployment.

Usage:
    python scripts/create_service_account_user.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv

# Load environment variables
env_file = backend_root.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: {env_file}")
else:
    print(f"⚠️  No .env file found at: {env_file}")
    print("Using environment variables from shell")

# Import after environment is loaded
from app.db.seed import ensure_service_account_user

if __name__ == "__main__":
    print("=" * 80)
    print("Creating/updating service account user in database")
    print("=" * 80)
    print()

    try:
        ensure_service_account_user()
        print()
        print("=" * 80)
        print("✅ Service account user is now present and active")
        print("=" * 80)
        print()
        print("You can now use the JWT token with GitHub Actions workflows")
        print()
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ Error: {e}")
        print("=" * 80)
        sys.exit(1)
