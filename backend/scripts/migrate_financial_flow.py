"""
Migration script to add financial flow relationships.
Run this once after deploying the schema changes.

This migration adds:
- status field to sessoes table
- payment_id field to sessoes table (FK to pagamentos)
- sessao_id field to pagamentos table (FK to sessoes)
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "app"))

from sqlalchemy import create_engine, text
from app.db.session import DATABASE_URL


def run_migration():
    """Add financial flow fields and relationships to existing database."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        try:
            # Add status column to sessoes table
            conn.execute(
                text(
                    """
                ALTER TABLE sessoes
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'
            """
                )
            )

            # Add payment_id column to sessoes table
            conn.execute(
                text(
                    """
                ALTER TABLE sessoes
                ADD COLUMN IF NOT EXISTS payment_id INTEGER REFERENCES pagamentos(id)
            """
                )
            )

            # Add sessao_id column to pagamentos table
            conn.execute(
                text(
                    """
                ALTER TABLE pagamentos
                ADD COLUMN IF NOT EXISTS sessao_id INTEGER REFERENCES sessoes(id)
            """
                )
            )

            # Update existing sessions to 'active' status if they don't have one
            conn.execute(
                text(
                    """
                UPDATE sessoes
                SET status = 'active'
                WHERE status IS NULL OR status = ''
            """
                )
            )

            conn.commit()
            print("✅ Migration completed successfully!")
            print("   - Added status field to sessoes table")
            print("   - Added payment_id field to sessoes table")
            print("   - Added sessao_id field to pagamentos table")
            print("   - Updated existing sessions to 'active' status")

        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            conn.rollback()
            raise


if __name__ == "__main__":
    run_migration()
    