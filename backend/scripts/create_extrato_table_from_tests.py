"""Create the 'extratos' table in the database.

This script imports the project's SQLAlchemy Base and engine and runs
Base.metadata.create_all(bind=engine) so the new `extratos` table is created
without using Alembic.

Usage:
    python backend/scripts/create_extrato_table.py

The script reads DATABASE_URL from the environment (same as the app).
"""

# Import all models to register them with Base
import app.db.base
from app.core.logging_config import get_logger
from app.db.session import Base, engine

logger = get_logger(__name__)


def main():
    logger.info(
        "Creating tables",
        extra={
            "context": {
                "note": "This will create any missing tables, including 'extratos'"
            }
        },
    )
    Base.metadata.create_all(bind=engine)
    logger.info(
        "Tables created/updated",
        extra={"context": {"action": "create_all", "status": "done"}},
    )


if __name__ == "__main__":
    main()
