"""
Script to create the 'gastos' table (and any missing tables) without Alembic.
This project manages schema via simple scripts calling Base.metadata.create_all().

Usage:
    python backend/scripts/create_gastos_table.py

It will import models to register them and then create the required table(s).
"""

# Import models so SQLAlchemy is aware of them
import app.db.base  # noqa: F401
from app.core.logging_config import get_logger
from app.db.session import Base, get_engine
from sqlalchemy import inspect

logger = get_logger(__name__)


def create_gastos_table():
    engine = get_engine()
    inspector = inspect(engine)
    if inspector is None:
        logger.error(
            "Unable to create inspector",
            extra={
                "context": {
                    "hint": "Ensure the database engine is properly configured and connected."
                }
            },
        )
        return
    if not inspector.has_table("gastos"):
        logger.info(
            "Creating table",
            extra={"context": {"table": "gastos", "action": "create"}},
        )
        Base.metadata.tables["gastos"].create(engine)
        logger.info(
            "Table created successfully",
            extra={"context": {"table": "gastos", "action": "created"}},
        )
    else:
        logger.info(
            "Table already exists",
            extra={"context": {"table": "gastos", "action": "exists"}},
        )


if __name__ == "__main__":
    create_gastos_table()
