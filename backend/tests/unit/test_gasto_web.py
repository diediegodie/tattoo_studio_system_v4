#!/usr/bin/env python3
"""
Test script to create a gasto via authenticated HTTP request
This is a manual integration test that requires a running server.
"""
from datetime import datetime
import os

import pytest
import requests

# Base URL for the app (configurable for Docker Compose)
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")


@pytest.mark.skip(reason="Manual integration test - requires running server")
def test_gasto_creation():
    # First, we need to login to get a session cookie
    # For this test, we'll assume there's a test user or we need to create one
    # Let's try to access the gastos page first to see what happens

    session = requests.Session()

    # Try to access the gastos page (this should redirect to login if not authenticated)
    response = session.get(f"{BASE_URL}/gastos")
    print(f"GET /gastos status: {response.status_code}")
    print(f"Response URL: {response.url}")

    if "login" in response.url:
        print("Redirected to login page - authentication required")
        print("To test gasto creation, you need to:")
        print("1. Log in through the web interface")
        print("2. Or modify this script to handle authentication")
        return

    # If we get here, we're authenticated
    # Now try to create a gasto
    gasto_data = {
        "data": "2024-01-15",
        "valor": "250.50",
        "descricao": "Teste de gasto autenticado",
        "forma_pagamento": "Pix",  # Agora com forma_pagamento preenchida!
    }

    response = session.post(f"{BASE_URL}/gastos/create", data=gasto_data)
    print(f"POST /gastos/create status: {response.status_code}")
    print(f"Response URL: {response.url}")

    if response.status_code == 200:
        print("Gasto created successfully!")
    elif response.status_code == 302:
        print("Redirected - check if gasto was created")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    test_gasto_creation()
