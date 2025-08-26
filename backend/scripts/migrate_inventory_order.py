"""
Robust migration script to ensure `inventory."order"` column is nullable and default NULL.

Supports PostgreSQL and SQLite.

Usage: run in the app environment:
  python backend/scripts/migrate_inventory_order.py

This script will:
 - detect DB dialect
 - if PostgreSQL: ALTER COLUMN to DROP NOT NULL and SET DEFAULT NULL
 - if SQLite: recreate the table with `order` column nullable and copy data

This is intended for development / test environments. Review SQL before running in production.
"""

from sqlalchemy import inspect, text
from app.db.session import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inspector = inspect(engine)

if "inventory" not in inspector.get_table_names():
    logger.info("No inventory table present; nothing to migrate.")
    exit(0)

dialect = engine.dialect.name
logger.info(f"Detected dialect: {dialect}")

cols = [c["name"] for c in inspector.get_columns("inventory")]

if "order" not in cols:
    # Column is missing: add nullable column
    with engine.connect() as conn:
        try:
            # Adding column is fine; it will be nullable by default in SQLite and many DBs
            conn.execute(text('ALTER TABLE inventory ADD COLUMN "order" INTEGER'))
            logger.info("Added column `order` to inventory table.")
        except Exception as e:
            logger.error("Failed to add column `order`: %s", e)
            raise
else:
    logger.info("Column `order` exists; ensuring nullable/default is correct.")

try:
    if dialect in ("postgresql", "postgres"):
        # PostgreSQL: alter column to drop NOT NULL and set default NULL
        with engine.connect() as conn:
            logger.info("Running PostgreSQL ALTER statements...")
            conn.execute(
                text('ALTER TABLE inventory ALTER COLUMN "order" DROP NOT NULL;')
            )
            conn.execute(
                text('ALTER TABLE inventory ALTER COLUMN "order" SET DEFAULT NULL;')
            )
        logger.info("PostgreSQL migration complete.")

    elif dialect == "sqlite":
        # SQLite: need to recreate table to change nullability safely
        logger.info("Performing SQLite table-recreate migration...")
        with engine.begin() as conn:
            pragma = conn.execute(text("PRAGMA table_info('inventory');")).fetchall()
            cols_info = pragma
            col_defs = []
            col_names = []
            for col in cols_info:
                # pragma returns: cid, name, type, notnull, dflt_value, pk
                name = col[1]
                ctype = col[2] or ""
                notnull = col[3]
                dflt = col[4]
                pk = col[5]
                col_names.append(name)
                # Make `order` column nullable explicitly
                if name == "order":
                    nullable = ""
                else:
                    nullable = " NOT NULL" if notnull else ""
                default = f" DEFAULT {dflt}" if dflt is not None else ""
                pk_sql = " PRIMARY KEY" if pk else ""
                col_defs.append(f'"{name}" {ctype}{nullable}{default}{pk_sql}')
            col_defs_sql = ", ".join(col_defs)
            conn.execute(text(f"CREATE TABLE inventory_new ({col_defs_sql});"))
            cols_csv = ", ".join([f'"{n}"' for n in col_names])
            conn.execute(
                text(
                    f"INSERT INTO inventory_new ({cols_csv}) SELECT {cols_csv} FROM inventory;"
                )
            )
            conn.execute(text("DROP TABLE inventory;"))
            conn.execute(text("ALTER TABLE inventory_new RENAME TO inventory;"))
        logger.info("SQLite migration complete.")

    else:
        logger.warning(
            "Dialect %s not specially handled; attempting generic ALTER", dialect
        )
        with engine.connect() as conn:
            conn.execute(
                text('ALTER TABLE inventory ALTER COLUMN "order" DROP NOT NULL')
            )
            conn.execute(
                text('ALTER TABLE inventory ALTER COLUMN "order" SET DEFAULT NULL')
            )
        logger.info("Generic migration attempted.")

    logger.info("Migration finished successfully.")

except Exception as exc:
    logger.exception("Migration failed: %s", exc)
    raise
