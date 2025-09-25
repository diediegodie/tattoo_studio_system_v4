#!/usr/bin/env python3
"""
Test script to debug Google Calendar sync with proper authentication
"""
import json
from datetime import datetime

import requests

# App URL
BASE_URL = "http://127.0.0.1:5000"


def test_calendar_sync():
    print("=== Google Calendar Sync Debug Test ===")

    # First, let's try to authenticate with a simple login
    session = requests.Session()

    # Try to access the calendar sync endpoint
    print("\n1. Testing calendar sync endpoint...")
    response = session.get(f"{BASE_URL}/calendar/sync")
    print(f"Status: {response.status_code}")
    print(f"URL after redirect: {response.url}")

    # Check if we can get the events API directly
    print("\n2. Testing calendar API events endpoint...")
    response = session.get(f"{BASE_URL}/calendar/api/events")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}...")

    # Try to trigger sync
    print("\n3. Testing calendar sync POST endpoint...")
    response = session.post(f"{BASE_URL}/calendar/api/sync")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}...")


if __name__ == "__main__":
    test_calendar_sync()
