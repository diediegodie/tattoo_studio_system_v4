"""
Script to validate that database indexes have been successfully applied.

This script checks the PostgreSQL system catalogs to verify the presence
and correctness of indexes created by add_indexes.py. It performs read-only
operations and generates a validation report.
"""

from app.core.logging_config import get_logger
import os
from datetime import datetime

from app.db.session import get_engine
from sqlalchemy import text

logger = get_logger(__name__)

# Expected indexes from add_indexes.py
EXPECTED_INDEXES = {
    "sessoes": [
        ("idx_sessoes_cliente_id", "cliente_id"),
        ("idx_sessoes_artista_id", "artista_id"),
        ("idx_sessoes_data", "data"),
        ("idx_sessoes_payment_id", "payment_id"),
    ],
    "pagamentos": [
        ("idx_pagamentos_data", "data"),
        ("idx_pagamentos_forma_pagamento", "forma_pagamento"),
        ("idx_pagamentos_cliente_id", "cliente_id"),
        ("idx_pagamentos_artista_id", "artista_id"),
        ("idx_pagamentos_sessao_id", "sessao_id"),
    ],
    "comissoes": [
        ("idx_comissoes_pagamento_id", "pagamento_id"),
        ("idx_comissoes_artista_id", "artista_id"),
    ],
    "extratos": [
        ("idx_extratos_mes", "mes"),
        ("idx_extratos_ano", "ano"),
    ],
    "extrato_run_logs": [
        ("idx_extrato_run_logs_mes", "mes"),
        ("idx_extrato_run_logs_ano", "ano"),
    ],
}


def get_existing_indexes(engine, table_names):
    """
    Query PostgreSQL system catalogs to get all indexes for specified tables.

    Args:
        engine: SQLAlchemy engine
        table_names: List of table names to check

    Returns:
        dict: Dictionary mapping table names to lists of (index_name, column_name) tuples
    """
    existing_indexes = {}

    try:
        with engine.connect() as conn:
            for table_name in table_names:
                # Query pg_indexes for index information
                result = conn.execute(
                    text(
                        """
                    SELECT
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE tablename = :table_name
                    ORDER BY indexname
                """
                    ),
                    {"table_name": table_name},
                )

                indexes = []
                for row in result:
                    index_name = row[0]
                    index_def = row[1]

                    # Extract column name from CREATE INDEX statement
                    # Format: CREATE INDEX index_name ON table_name (column_name)
                    if "(" in index_def and ")" in index_def:
                        column_part = index_def.split("(")[1].split(")")[0].strip()
                        # Handle single column indexes (ignore multi-column for now)
                        if "," not in column_part:
                            indexes.append((index_name, column_part))

                existing_indexes[table_name] = indexes
                logger.info(f"Found {len(indexes)} indexes for table '{table_name}'")

    except Exception as e:
        logger.error(f"Error querying indexes: {str(e)}")
        return {}

    return existing_indexes


def validate_indexes():
    """
    Validate that all expected indexes exist and are correctly configured.

    Returns:
        dict: Validation results with status for each expected index
    """
    engine = get_engine()
    table_names = list(EXPECTED_INDEXES.keys())

    logger.info("Starting index validation...")
    logger.info(f"Checking tables: {', '.join(table_names)}")

    # Get existing indexes from database
    existing_indexes = get_existing_indexes(engine, table_names)

    if not existing_indexes:
        logger.error("Failed to retrieve existing indexes from database")
        return {}

    validation_results = {}

    # Validate each expected index
    for table_name, expected_indexes in EXPECTED_INDEXES.items():
        table_results = {}

        if table_name not in existing_indexes:
            logger.warning(f"Table '{table_name}' not found in database")
            for index_name, _ in expected_indexes:
                table_results[index_name] = {
                    "status": "❌",
                    "reason": f"Table '{table_name}' not found",
                    "expected_column": None,
                    "found": False,
                }
        else:
            existing_table_indexes = dict(existing_indexes[table_name])

            for expected_index_name, expected_column in expected_indexes:
                if expected_index_name in existing_table_indexes:
                    found_column = existing_table_indexes[expected_index_name]
                    if found_column == expected_column:
                        table_results[expected_index_name] = {
                            "status": "✅",
                            "reason": "Index exists and matches expectations",
                            "expected_column": expected_column,
                            "found_column": found_column,
                            "found": True,
                        }
                        logger.info(
                            f"✅ Index '{expected_index_name}' validated successfully"
                        )
                    else:
                        table_results[expected_index_name] = {
                            "status": "❌",
                            "reason": f"Column mismatch: expected '{expected_column}', found '{found_column}'",
                            "expected_column": expected_column,
                            "found_column": found_column,
                            "found": True,
                        }
                        logger.warning(
                            f"❌ Index '{expected_index_name}' has wrong column"
                        )
                else:
                    table_results[expected_index_name] = {
                        "status": "❌",
                        "reason": "Index not found",
                        "expected_column": expected_column,
                        "found_column": None,
                        "found": False,
                    }
                    logger.warning(f"❌ Index '{expected_index_name}' not found")

        validation_results[table_name] = table_results

    return validation_results


def generate_report(validation_results):
    """
    Generate a formatted validation report.

    Args:
        validation_results: Results from validate_indexes()

    Returns:
        str: Formatted report string
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("DATABASE INDEX VALIDATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    total_expected = 0
    total_found = 0

    for table_name, table_results in validation_results.items():
        report_lines.append(f"Table: {table_name}")
        report_lines.append("-" * (len(table_name) + 7))

        for index_name, result in table_results.items():
            total_expected += 1
            if result["found"] and result["status"] == "✅":
                total_found += 1

            status = result["status"]
            reason = result["reason"]
            expected_col = result["expected_column"] or "N/A"

            report_lines.append(f"  {status} {index_name}")
            report_lines.append(f"     Column: {expected_col}")
            report_lines.append(f"     Status: {reason}")

        report_lines.append("")

    # Summary
    report_lines.append("=" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 80)
    report_lines.append(f"Total indexes expected: {total_expected}")
    report_lines.append(f"Total indexes found: {total_found}")
    report_lines.append(
        f"Success rate: {total_found}/{total_expected} ({total_found/total_expected*100:.1f}%)"
    )

    if total_found == total_expected:
        report_lines.append("🎉 All expected indexes are present and correct!")
    else:
        report_lines.append(
            "⚠️  Some indexes are missing or incorrect. Run add_indexes.py to create them."
        )

    return "\n".join(report_lines)


def save_report_to_file(report_content):
    """
    Save the validation report to a log file.

    Args:
        report_content: The report content as a string
    """
    # Ensure logs directory exists
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"index_validation_{timestamp}.log")

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        logger.info(f"Report saved to: {log_file}")
    except Exception as e:
        logger.error(f"Failed to save report to file: {str(e)}")


def main():
    """Main function to run the validation."""
    logger.info("Starting database index validation...")

    try:
        # Run validation
        validation_results = validate_indexes()

        if not validation_results:
            logger.error("Validation failed - no results returned")
            return

        # Generate and log report
        report = generate_report(validation_results)
        logger.info("Index validation report", extra={"context": {"report": report}})

        # Save report to file
        save_report_to_file(report)

        logger.info("Index validation completed successfully")

    except Exception as e:
        logger.error(f"Validation failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
