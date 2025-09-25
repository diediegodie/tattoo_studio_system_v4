"""
Script to add database indexes for improved query performance.

This script creates indexes on frequently queried columns including:
- Foreign keys used in JOINs
- Date fields used in filtering
- Payment method columns used in WHERE clauses

The script is idempotent and safe to run multiple times.
"""

import logging

from app.db.session import get_engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_index_if_not_exists(engine, index_name, table_name, column_name):
    """
    Create an index if it doesn't already exist.

    Args:
        engine: SQLAlchemy engine
        index_name: Name of the index to create
        table_name: Name of the table
        column_name: Name of the column to index
    """
    try:
        with engine.connect() as conn:
            # Check if index exists
            result = conn.execute(
                text(
                    """
                SELECT 1 FROM pg_indexes
                WHERE tablename = :table_name AND indexname = :index_name
            """
                ),
                {"table_name": table_name, "index_name": index_name},
            )

            if result.fetchone():
                logger.info(
                    f"Index '{index_name}' already exists on {table_name}.{column_name}"
                )
                return

            # Create the index
            create_sql = f"CREATE INDEX {index_name} ON {table_name} ({column_name})"
            logger.info(f"Creating index: {create_sql}")
            conn.execute(text(create_sql))
            conn.commit()
            logger.info(
                f"Successfully created index '{index_name}' on {table_name}.{column_name}"
            )

    except Exception as e:
        logger.error(
            f"Failed to create index '{index_name}' on {table_name}.{column_name}: {str(e)}"
        )


def add_indexes():
    """Add all required indexes to the database."""
    engine = get_engine()
    logger.info("Starting index creation process...")

    # Indexes for sessoes table
    create_index_if_not_exists(
        engine, "idx_sessoes_cliente_id", "sessoes", "cliente_id"
    )
    create_index_if_not_exists(
        engine, "idx_sessoes_artista_id", "sessoes", "artista_id"
    )
    create_index_if_not_exists(engine, "idx_sessoes_data", "sessoes", "data")
    create_index_if_not_exists(
        engine, "idx_sessoes_payment_id", "sessoes", "payment_id"
    )

    # Indexes for pagamentos table
    create_index_if_not_exists(engine, "idx_pagamentos_data", "pagamentos", "data")
    create_index_if_not_exists(
        engine, "idx_pagamentos_forma_pagamento", "pagamentos", "forma_pagamento"
    )
    create_index_if_not_exists(
        engine, "idx_pagamentos_cliente_id", "pagamentos", "cliente_id"
    )
    create_index_if_not_exists(
        engine, "idx_pagamentos_artista_id", "pagamentos", "artista_id"
    )
    create_index_if_not_exists(
        engine, "idx_pagamentos_sessao_id", "pagamentos", "sessao_id"
    )

    # Indexes for comissoes table
    create_index_if_not_exists(
        engine, "idx_comissoes_pagamento_id", "comissoes", "pagamento_id"
    )
    create_index_if_not_exists(
        engine, "idx_comissoes_artista_id", "comissoes", "artista_id"
    )

    # Indexes for extratos table
    create_index_if_not_exists(engine, "idx_extratos_mes", "extratos", "mes")
    create_index_if_not_exists(engine, "idx_extratos_ano", "extratos", "ano")

    # Indexes for extrato_run_logs table
    create_index_if_not_exists(
        engine, "idx_extrato_run_logs_mes", "extrato_run_logs", "mes"
    )
    create_index_if_not_exists(
        engine, "idx_extrato_run_logs_ano", "extrato_run_logs", "ano"
    )

    logger.info("Index creation process completed.")


if __name__ == "__main__":
    add_indexes()
