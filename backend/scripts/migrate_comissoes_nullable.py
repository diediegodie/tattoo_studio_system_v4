"""
Migration script to make pagamento_id nullable in comissoes table.

This allows payments and commissions to be independent entities.
Run this script to update the database schema.
"""

import os

from sqlalchemy import create_engine, text


def run_migration():
    """Update the comissoes table to allow NULL pagamento_id values."""

    # Get database URL from environment, with fallback for local development
    database_url = os.getenv(
        "DATABASE_URL", "[REDACTED_DATABASE_URL]"
    )

    print(f"Connecting to database: {database_url}")
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if we're using PostgreSQL or SQLite
            if "postgresql" in database_url:
                # PostgreSQL syntax
                print("Running PostgreSQL migration...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE comissoes
                    ALTER COLUMN pagamento_id DROP NOT NULL;
                """
                    )
                )
                conn.commit()
                print("Migration completed successfully for PostgreSQL.")
            else:
                # SQLite syntax (if needed)
                print("Running SQLite migration...")
                # For SQLite, we need to recreate the table
                conn.execute(
                    text(
                        """
                    CREATE TABLE comissoes_new (
                        id INTEGER PRIMARY KEY,
                        pagamento_id INTEGER,
                        artista_id INTEGER NOT NULL,
                        percentual NUMERIC(5,2) NOT NULL,
                        valor NUMERIC(10,2) NOT NULL,
                        observacoes VARCHAR(255),
                        created_at TIMESTAMP,
                        FOREIGN KEY (pagamento_id) REFERENCES pagamentos (id),
                        FOREIGN KEY (artista_id) REFERENCES users (id)
                    );
                """
                    )
                )

                conn.execute(
                    text(
                        """
                    INSERT INTO comissoes_new
                    SELECT id, pagamento_id, artista_id, percentual, valor, observacoes, created_at
                    FROM comissoes;
                """
                    )
                )

                conn.execute(text("DROP TABLE comissoes;"))
                conn.execute(text("ALTER TABLE comissoes_new RENAME TO comissoes;"))
                conn.commit()
                print("Migration completed successfully for SQLite.")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    run_migration()
