"""Create the 'extratos' table in the database.

This script imports the project's SQLAlchemy Base and engine and runs
Base.metadata.create_all(bind=engine) so the new `extratos` table is created
without using Alembic.

Usage:
    python backend/scripts/create_extrato_table.py

The script reads DATABASE_URL from the environment (same as the app).
"""

from app.db.session import engine, Base

# Import all models to register them with Base
import app.db.base


def main():
    print(
        "Creating tables (this will create any missing tables, including 'extratos')..."
    )
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created/updated.")


if __name__ == "__main__":
    main()
