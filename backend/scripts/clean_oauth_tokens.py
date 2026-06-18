#!/usr/bin/env python3
"""
Clean up OAuth tokens that may have been stored as strings.

This script converts any string tokens to dict format for compatibility
with the updated OAuth model that requires JSONB dicts.

Usage:
    python scripts/clean_oauth_tokens.py [--dry-run]

Options:
    --dry-run    Show what would be changed without making changes
"""

import argparse
import json
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import SessionLocal
from app.db.base import OAuth


def clean_oauth_tokens(dry_run=False):
    """
    Clean up OAuth tokens that are stored as strings.

    Args:
        dry_run: If True, only show what would be changed without making changes
    """
    db = SessionLocal()
    fixed_count = 0
    error_count = 0
    total_count = 0

    try:
        oauth_records = db.query(OAuth).all()
        total_count = len(oauth_records)

        print(f"Found {total_count} OAuth records to check")
        print("-" * 60)

        for record in oauth_records:
            token = record.token

            # Check if token is a string (should be dict)
            if isinstance(token, str):
                print(f"\n❌ User {record.user_id} (Provider: {record.provider})")
                token_str = str(token)
                print(f"   Token is string: {token_str[:50]}...")

                try:
                    # Try to parse as JSON
                    parsed = json.loads(token_str)

                    if isinstance(parsed, dict):
                        print(
                            f"   ✅ Successfully parsed to dict with {len(parsed)} keys"
                        )

                        if not dry_run:
                            record.token = parsed
                            fixed_count += 1
                            print(f"   💾 Updated in database")
                        else:
                            print(f"   🔍 Would update (dry-run mode)")
                    else:
                        print(f"   ⚠️  Parsed but not a dict: {type(parsed)}")
                        error_count += 1

                except json.JSONDecodeError as e:
                    print(f"   ❌ JSONDecodeError: {e}")
                    print(f"   ⚠️  Wrapping as access_token")

                    if not dry_run:
                        record.token = {"access_token": token_str}
                        fixed_count += 1
                        print(f"   💾 Updated in database")
                    else:
                        print(f"   🔍 Would update (dry-run mode)")

            elif isinstance(token, dict):
                print(
                    f"✅ User {record.user_id} (Provider: {record.provider}) - Already dict"
                )
            else:
                print(
                    f"⚠️  User {record.user_id} (Provider: {record.provider}) - Unknown type: {type(token)}"
                )
                error_count += 1

        if not dry_run and fixed_count > 0:
            db.commit()
            print(f"\n{'=' * 60}")
            print(f"✅ Successfully updated {fixed_count} records")
        elif dry_run and fixed_count > 0:
            print(f"\n{'=' * 60}")
            print(f"🔍 Would update {fixed_count} records (dry-run mode)")
        else:
            print(f"\n{'=' * 60}")
            print(f"ℹ️  No changes needed")

        print(f"📊 Summary:")
        print(f"   Total records: {total_count}")
        print(f"   Fixed: {fixed_count}")
        print(f"   Errors: {error_count}")
        print(f"   Already correct: {total_count - fixed_count - error_count}")

        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during cleanup: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Clean up OAuth tokens stored as strings"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()

    print("OAuth Token Cleanup Script")
    print("=" * 60)

    if args.dry_run:
        print("🔍 Running in DRY-RUN mode (no changes will be made)")
    else:
        print("⚠️  Running in LIVE mode (changes will be committed)")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted")
            return

    print("=" * 60)
    print()

    success = clean_oauth_tokens(dry_run=args.dry_run)

    if success:
        print("\n✅ Cleanup completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Cleanup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
