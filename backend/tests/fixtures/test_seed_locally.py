#!/usr/bin/env python3
"""
Simple test script to run the fake extrato data seeding locally.
This version can be run outside Docker for easier development.

Uso: python test_seed_locally.py
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from scripts.seed_fake_extrato_data import main

    if __name__ == "__main__":
        print("🧪 Running fake extrato data seed locally...")
        main()
        print("🎉 Local seed completed!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running this from the project root directory")
    print("💡 And that your virtual environment is activated")
except Exception as e:
    print(f"❌ Error: {e}")
