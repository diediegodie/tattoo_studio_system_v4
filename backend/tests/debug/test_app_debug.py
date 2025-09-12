#!/usr/bin/env python3
"""
Debug script to test app creation for the API tests.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    print("1. Testing import of app.main...")
    from app.main import create_app

    print("   ✓ Successfully imported create_app")

    print("2. Testing app creation...")
    app = create_app()
    print(f"   ✓ App created: {type(app)}")

    print("3. Testing app config...")
    app.config["TESTING"] = True
    print(f"   ✓ App config: {app.config.get('TESTING')}")

    print("4. Testing test client...")
    with app.test_client() as client:
        print(f"   ✓ Test client created: {type(client)}")

        print("5. Testing route access...")
        response = client.get("/sessoes/api")
        print(f"   Response status: {response.status_code}")
        print(f"   Response data: {response.data[:100]}...")

except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback

    traceback.print_exc()
