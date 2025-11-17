"""make_jotform_submission_id_nullable

Revision ID: 001makejotformnullable
Revises: 999addserviceaccount
Create Date: 2025-11-17

Allow jotform_submission_id to be NULL to support manually created clients.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001makejotformnullable"
down_revision = "999addserviceaccount"
branch_labels = None
depends_on = None


def upgrade():
    """Make jotform_submission_id nullable to allow manual client creation."""
    # SQLite doesn't support ALTER COLUMN directly, so we need to:
    # 1. Create new table with nullable column
    # 2. Copy data
    # 3. Drop old table
    # 4. Rename new table

    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.alter_column(
            "jotform_submission_id", existing_type=sa.String(length=100), nullable=True
        )


def downgrade():
    """Revert jotform_submission_id to NOT NULL (may fail if NULL values exist)."""
    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.alter_column(
            "jotform_submission_id", existing_type=sa.String(length=100), nullable=False
        )
