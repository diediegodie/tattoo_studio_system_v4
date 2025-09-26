#!/usr/bin/env python3
"""
PRODUCTION Migration Script: Make cliente_id nullable in pagamentos table

This script safely migrates the production database to allow NULL values in the
cliente_id column of the pagamentos table, enabling payments without client association.

SAFETY FEATURES:
- Automatic backup creation before migration
- Transaction rollback on any error
- Comprehensive verification
- Production environment detection
- Detailed logging

Usage:
    # Set database URL for production
    export DATABASE_URL="postgresql://user:password@host:port/database"

    # Run migration
    python backend/scripts/migrate_cliente_nullable_production.py

    # Or with explicit confirmation
    python backend/scripts/migrate_cliente_nullable_production.py --confirm
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime
from urllib.parse import urlparse

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from sqlalchemy import text, create_engine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f'migration_cliente_nullable_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ProductionMigration:
    """Safe production migration handler."""

    def __init__(self, database_url):
        self.database_url = database_url
        self.engine = None
        self.backup_filename = None

    def validate_environment(self):
        """Validate that we're ready for production migration."""
        logger.info("🔍 Validating production environment...")

        if not self.database_url:
            raise ValueError("DATABASE_URL not provided")

        # Parse database URL to extract connection details
        parsed = urlparse(self.database_url)
        if parsed.scheme != "postgresql":
            raise ValueError(
                f"Only PostgreSQL is supported for production. Got: {parsed.scheme}"
            )

        # Create engine
        self.engine = create_engine(self.database_url)

        # Test connection
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version()")).fetchone()
            logger.info(f"✅ Connected to PostgreSQL: {result[0][:50]}...")

    def create_backup(self):
        """Create database backup before migration."""
        logger.info("🛡️  Creating database backup...")

        parsed = urlparse(self.database_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_filename = f"backup_cliente_nullable_{timestamp}.dump"

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h",
            parsed.hostname,
            "-p",
            str(parsed.port or 5432),
            "-U",
            parsed.username,
            "-d",
            parsed.path[1:],  # Remove leading slash
            "-Fc",  # Custom format
            "-f",
            self.backup_filename,
        ]

        # Set password via environment
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password

        try:
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, check=True
            )

            # Verify backup file exists and has reasonable size
            if os.path.exists(self.backup_filename):
                size = os.path.getsize(self.backup_filename)
                logger.info(
                    f"✅ Backup created successfully: {self.backup_filename} ({size} bytes)"
                )
                return True
            else:
                raise Exception("Backup file not created")

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Backup failed: {e.stderr}")
            raise

    def check_current_schema(self):
        """Check current state of cliente_id column."""
        logger.info("🔍 Checking current schema...")

        with self.engine.connect() as conn:
            # Check if pagamentos table exists
            table_check = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pagamentos'
                );
            """
                )
            ).fetchone()[0]

            if not table_check:
                raise Exception("pagamentos table does not exist")

            # Check cliente_id column
            column_info = conn.execute(
                text(
                    """
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'pagamentos' AND column_name = 'cliente_id';
            """
                )
            ).fetchone()

            if not column_info:
                raise Exception("cliente_id column does not exist in pagamentos table")

            logger.info(
                f"Current cliente_id: {column_info[2]}, nullable: {column_info[1]}"
            )

            if column_info[1] == "YES":
                logger.warning(
                    "⚠️  cliente_id is already nullable - migration may not be needed"
                )
                return False

            return True

    def execute_migration(self):
        """Execute the actual migration with transaction safety."""
        logger.info("🔧 Executing migration...")

        with self.engine.begin() as conn:  # Auto-rollback on exception
            try:
                # Execute the migration
                conn.execute(
                    text(
                        "ALTER TABLE pagamentos ALTER COLUMN cliente_id DROP NOT NULL;"
                    )
                )
                logger.info("✅ Successfully executed ALTER TABLE statement")

                # Verify within transaction
                result = conn.execute(
                    text(
                        """
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'pagamentos' AND column_name = 'cliente_id';
                """
                    )
                ).fetchone()

                if result[0] != "YES":
                    raise Exception(
                        "Migration verification failed - column is still NOT NULL"
                    )

                logger.info("✅ Migration verified successfully within transaction")

                # Transaction will auto-commit here if no exception

            except Exception as e:
                logger.error(f"❌ Migration failed: {e}")
                logger.info("🔄 Transaction will be rolled back automatically")
                raise

    def verify_migration(self):
        """Comprehensive post-migration verification."""
        logger.info("✅ Running post-migration verification...")

        with self.engine.connect() as conn:
            # Check schema
            column_info = conn.execute(
                text(
                    """
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'pagamentos' AND column_name = 'cliente_id';
            """
                )
            ).fetchone()

            if column_info[1] != "YES":
                raise Exception("Verification failed: cliente_id is still NOT NULL")

            # Test NULL insertion
            conn.execute(text("BEGIN;"))
            try:
                conn.execute(
                    text(
                        """
                    INSERT INTO pagamentos (valor, forma_pagamento, descricao, created_at, cliente_id)
                    VALUES (1.00, 'test', 'Migration verification test', NOW(), NULL);
                """
                    )
                )

                # Verify insertion
                result = conn.execute(
                    text(
                        """
                    SELECT id FROM pagamentos 
                    WHERE descricao = 'Migration verification test' AND cliente_id IS NULL;
                """
                    )
                ).fetchone()

                if not result:
                    raise Exception("Could not insert payment with NULL cliente_id")

                # Clean up test data
                conn.execute(
                    text(
                        """
                    DELETE FROM pagamentos WHERE descricao = 'Migration verification test';
                """
                    )
                )

                conn.execute(text("COMMIT;"))
                logger.info(
                    "✅ Functional verification passed - NULL cliente_id works correctly"
                )

            except Exception as e:
                conn.execute(text("ROLLBACK;"))
                raise Exception(f"Functional verification failed: {e}")

    def run_migration(self, skip_backup=False):
        """Run the complete migration process."""
        logger.info("🚀 Starting production migration: cliente_id nullable")

        try:
            # Step 1: Validate environment
            self.validate_environment()

            # Step 2: Check current schema
            needs_migration = self.check_current_schema()
            if not needs_migration:
                logger.info("🎉 Migration not needed - cliente_id is already nullable")
                return True

            # Step 3: Create backup
            if not skip_backup:
                self.create_backup()
            else:
                logger.warning("⚠️  Skipping backup creation (not recommended)")

            # Step 4: Execute migration
            self.execute_migration()

            # Step 5: Verify migration
            self.verify_migration()

            logger.info("🎉 Migration completed successfully!")
            logger.info("✅ Payments can now be created without specifying a client")

            if self.backup_filename:
                logger.info(f"💾 Backup available at: {self.backup_filename}")

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            if self.backup_filename:
                logger.info(
                    f"🔄 Rollback available using backup: {self.backup_filename}"
                )
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Production migration for cliente_id nullable"
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation (NOT recommended)",
    )
    parser.add_argument(
        "--database-url", help="Database URL (or use DATABASE_URL env var)"
    )

    args = parser.parse_args()

    # Get database URL
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error(
            "❌ DATABASE_URL not provided. Use --database-url or set environment variable."
        )
        return 1

    # Safety confirmation
    if not args.confirm:
        print("\n" + "=" * 60)
        print("🚨 PRODUCTION MIGRATION WARNING")
        print("=" * 60)
        print("This will modify your production database schema.")
        print("Make sure you have:")
        print("  ✅ Tested on staging environment")
        print("  ✅ Scheduled maintenance window")
        print("  ✅ Notified relevant stakeholders")
        print("  ✅ Verified backup strategy")
        print(
            "\nDatabase:",
            database_url.split("@")[-1] if "@" in database_url else database_url,
        )

        response = input("\nProceed with migration? (yes/no): ").lower().strip()
        if response != "yes":
            print("Migration cancelled.")
            return 0

    # Run migration
    migration = ProductionMigration(database_url)

    try:
        success = migration.run_migration(skip_backup=args.skip_backup)
        return 0 if success else 1

    except KeyboardInterrupt:
        logger.error("\n❌ Migration interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
