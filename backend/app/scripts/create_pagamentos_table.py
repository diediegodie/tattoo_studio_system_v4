"""
Script to force create the pagamentos table.
"""

from sqlalchemy import inspect

from db.session import engine, Base
from db.base import Pagamento  # Ensure the model is imported to be known by SQLAlchemy


def create_pagamentos_table():
    """Create pagamentos table if it doesn't exist."""
    inspector = inspect(engine)
    if not inspector.has_table("pagamentos"):
        print("Creating 'pagamentos' table...")
        # Create only the pagamentos table
        Base.metadata.tables["pagamentos"].create(engine)
        print("Table 'pagamentos' created successfully.")
    else:
        print("Table 'pagamentos' already exists.")


if __name__ == "__main__":
    create_pagamentos_table()
