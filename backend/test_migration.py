#!/usr/bin/env python3
"""
Test the migration system with local SQLite database.
This simulates what will happen on Render when you deploy.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Force SQLite database
project_root = backend_dir.parent
sqlite_path = project_root / "tattoo_studio_dev.db"
os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path}"

print(f"🔍 Testing migration with: {os.environ['DATABASE_URL']}")
print()

# Import after setting DATABASE_URL
from app.db.migrations import ensure_migration_001_applied

print("=" * 60)
print("BEFORE MIGRATION:")
print("=" * 60)

import sqlite3

conn = sqlite3.connect(str(sqlite_path))
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(clients)")
columns = cursor.fetchall()
for col in columns:
    if col[1] == "jotform_submission_id":
        is_nullable = col[3] == 0
        print(f"Column: {col[1]}")
        print(f"Type: {col[2]}")
        print(f"NOT NULL: {col[3] == 1}")
        print(f"Nullable: {is_nullable}")
        print()
conn.close()

print("=" * 60)
print("APPLYING MIGRATION:")
print("=" * 60)
print()

# Apply migration
ensure_migration_001_applied()

print()
print("=" * 60)
print("AFTER MIGRATION:")
print("=" * 60)

conn = sqlite3.connect(str(sqlite_path))
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(clients)")
columns = cursor.fetchall()
for col in columns:
    if col[1] == "jotform_submission_id":
        is_nullable = col[3] == 0
        print(f"Column: {col[1]}")
        print(f"Type: {col[2]}")
        print(f"NOT NULL: {col[3] == 1}")
        print(f"Nullable: {is_nullable}")
        print()

# Test creating a client without jotform_submission_id
print("=" * 60)
print("TESTING MANUAL CLIENT CREATION:")
print("=" * 60)
try:
    cursor.execute(
        """
        INSERT INTO clients (name, jotform_submission_id, created_at)
        VALUES ('Test Manual Client', NULL, CURRENT_TIMESTAMP)
    """
    )
    conn.commit()
    print("✅ SUCCESS: Manual client created without jotform_submission_id")

    # Clean up test data
    cursor.execute("DELETE FROM clients WHERE name = 'Test Manual Client'")
    conn.commit()
except Exception as e:
    print(f"❌ FAILED: {e}")

conn.close()

print()
print("=" * 60)
print("MIGRATION TEST COMPLETE")
print("=" * 60)
