"""add_service_account_user

Revision ID: 999addserviceaccount
Revises: None
Create Date: 2025-10-29

Ensures the GitHub Actions service account user (id=999) exists and is active/admin.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '999addserviceaccount'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Insert or update the service account user (id=999)
    op.execute("""
    INSERT INTO users (id, email, name, role, active_flag, password_hash)
    VALUES (
        999,
        'github-actions@tattoo-studio.local',
        'GitHub Actions Bot',
        'admin',
        TRUE,
        '!'
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        name = EXCLUDED.name,
        role = 'admin',
        active_flag = TRUE,
        password_hash = '!'
    ;
    """)

def downgrade():
    # Remove the service account user (id=999) for reversibility
    op.execute("DELETE FROM users WHERE id=999;")
