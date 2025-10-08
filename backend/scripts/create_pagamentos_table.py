"""
Script to force create the pagamentos table.
"""

from app.db.base import (
    Pagamento,
)  # Ensure the model is imported to be known by SQLAlchemy
from app.db.session import Base, engine
from sqlalchemy import inspect
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def create_pagamentos_table():
    """Create pagamentos table if it doesn't exist."""
    inspector = inspect(engine)
    if inspector is None:
        logger.error(
            "Unable to create inspector",
            extra={"context": {"hint": "Check database engine configuration"}},
        )
        return
    if not inspector.has_table("pagamentos"):
        logger.info(
            "Creating table",
            extra={"context": {"table": "pagamentos", "action": "create"}},
        )
        # Create only the pagamentos table
        Base.metadata.tables["pagamentos"].create(engine)
        logger.info(
            "Table created successfully",
            extra={"context": {"table": "pagamentos", "action": "created"}},
        )
    else:
        logger.info(
            "Table already exists",
            extra={"context": {"table": "pagamentos", "action": "exists"}},
        )


if __name__ == "__main__":
    create_pagamentos_table()
