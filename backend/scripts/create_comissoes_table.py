"""Simple migration script to ensure `comissoes` table exists.

This project does not use Alembic; we provide a small script that imports the models
and calls `Base.metadata.create_all()` to create any missing tables.
"""

from app.db.session import create_tables
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def run():
    logger.info(
        "Running migration",
        extra={"context": {"tables": ["comissoes"], "action": "create_missing"}},
    )
    create_tables()
    logger.info("Migration finished")


if __name__ == "__main__":
    run()
