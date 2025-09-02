"""Simple migration script to ensure `comissoes` table exists.

This project does not use Alembic; we provide a small script that imports the models
and calls `Base.metadata.create_all()` to create any missing tables.
"""

from app.db.session import create_tables


def run():
    print("Running migration: create comissoes table and any missing tables...")
    create_tables()
    print("Migration finished.")


if __name__ == "__main__":
    run()
