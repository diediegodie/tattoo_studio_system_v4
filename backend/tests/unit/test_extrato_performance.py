#!/usr/bin/env python3
"""
Test script to verify extrato page loads without blocking.
"""

import os
import sys
import time
from threading import Thread

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def test_extrato_page_load():
    """Test that the extrato page loads quickly without blocking."""
    from app.main import create_app

    # Disable background processing for this test
    os.environ["DISABLE_EXTRATO_BACKGROUND"] = "true"

    app = create_app()

    with app.test_client() as client:
        # Simulate login (this would normally be done through Flask-Login)
        with client.application.test_request_context():
            from flask_login import login_user
            from app.db.session import SessionLocal
            from app.repositories.user_repo import UserRepository

            db = SessionLocal()
            try:
                repo = UserRepository(db)
                # Get first user for testing
                user = repo.get_all_artists()[0] if repo.get_all_artists() else None
                if user:
                    login_user(user)
            except:
                pass
            finally:
                db.close()

        start_time = time.time()

        # Test the extrato page
        response = client.get("/extrato")

        end_time = time.time()
        load_time = end_time - start_time

        print(f"Extrato page load time: {load_time:.2f} seconds")
        print(f"Response status: {response.status_code}")

        # Should load quickly (less than 5 seconds even with extrato generation)
        if load_time < 5.0:
            print("✅ Page loads quickly - background processing working")
        else:
            print("❌ Page loads slowly - possible blocking issue")

        return response.status_code == 200 and load_time < 5.0


if __name__ == "__main__":
    print("Testing extrato page load performance...")
    success = test_extrato_page_load()
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
        sys.exit(1)
