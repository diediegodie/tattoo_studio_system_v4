"""
Script to create the 'gastos' table (and any missing tables) without Alembic.
This project manages schema via simple scripts calling Base.metadata.create_all().

Usage:
    python backend/scripts/create_gastos_table.py

It will import models to register them and then create the required table(s).
"""

from sqlalchemy import inspect

from app.db.session import get_engine, Base

# Import models so SQLAlchemy is aware of them
import app.db.base  # noqa: F401


def create_gastos_table():
    engine = get_engine()
    inspector = inspect(engine)
    if inspector is None:
        print(
            "Error: Unable to create inspector. Ensure the database engine is properly configured and connected."
        )
        return
    if not inspector.has_table("gastos"):
        print("Creating 'gastos' table...")
        Base.metadata.tables["gastos"].create(engine)
        print("Table 'gastos' created successfully.")
    else:
        print("Table 'gastos' already exists.")


if __name__ == "__main__":
    create_gastos_table()
