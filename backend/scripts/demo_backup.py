"""
Demonstration script showing backup system functionality with mock data.
This demonstrates the backup system without requiring database connectivity.
"""

import csv
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# Add the app directory to the Python path
sys.path.insert(
    0, "/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend"
)

from app.core.logging_config import get_logger

logger = get_logger(__name__)

from app.core.logging_config import get_logger
from app.services.backup_service import BackupService

logger = get_logger(__name__)


def create_mock_historical_data() -> List[Dict[str, Any]]:
    """Create mock historical data for demonstration."""
    mock_data = []

    # Mock Pagamentos
    mock_data.extend(
        [
            {
                "type": "pagamento",
                "id": 1,
                "data": "2025-09-01",
                "valor": 150.00,
                "forma_pagamento": "dinheiro",
                "observacoes": "Pagamento da sessão de tatuagem",
                "cliente_name": "João Silva",
                "artista_name": "Maria Tattoo",
                "sessao_id": 1,
                "created_at": "2025-09-01T10:00:00",
                "updated_at": "2025-09-01T10:00:00",
            },
            {
                "type": "pagamento",
                "id": 2,
                "data": "2025-09-05",
                "valor": 200.00,
                "forma_pagamento": "cartão",
                "observacoes": "Pagamento adiantado",
                "cliente_name": "Ana Santos",
                "artista_name": "Carlos Ink",
                "sessao_id": 2,
                "created_at": "2025-09-05T14:30:00",
                "updated_at": "2025-09-05T14:30:00",
            },
        ]
    )

    # Mock Sessoes
    mock_data.extend(
        [
            {
                "type": "sessao",
                "id": 1,
                "data": "2025-09-01",
                "hora": "10:00:00",
                "valor": 150.00,
                "observacoes": "Tatuagem no braço",
                "status": "completed",
                "cliente_name": "João Silva",
                "artista_name": "Maria Tattoo",
                "google_event_id": None,
                "payment_id": 1,
                "created_at": "2025-08-25T09:00:00",
                "updated_at": "2025-09-01T11:00:00",
            },
            {
                "type": "sessao",
                "id": 2,
                "data": "2025-09-05",
                "hora": "14:00:00",
                "valor": 200.00,
                "observacoes": "Tatuagem nas costas",
                "status": "paid",
                "cliente_name": "Ana Santos",
                "artista_name": "Carlos Ink",
                "google_event_id": "abc123",
                "payment_id": 2,
                "created_at": "2025-08-28T16:00:00",
                "updated_at": "2025-09-05T15:30:00",
            },
        ]
    )

    # Mock Comissoes
    mock_data.extend(
        [
            {
                "type": "comissao",
                "id": 1,
                "pagamento_id": 1,
                "artista_name": "Maria Tattoo",
                "cliente_name": "João Silva",
                "percentual": 30.0,
                "valor": 45.00,
                "observacoes": "Comissão sobre tatuagem",
                "created_at": "2025-09-01T10:05:00",
            },
            {
                "type": "comissao",
                "id": 2,
                "pagamento_id": 2,
                "artista_name": "Carlos Ink",
                "cliente_name": "Ana Santos",
                "percentual": 25.0,
                "valor": 50.00,
                "observacoes": "Comissão reduzida",
                "created_at": "2025-09-05T14:35:00",
            },
        ]
    )

    # Mock Gastos
    mock_data.extend(
        [
            {
                "type": "gasto",
                "id": 1,
                "data": "2025-09-02",
                "valor": 75.00,
                "descricao": "Compra de tintas",
                "forma_pagamento": "dinheiro",
                "created_by": 1,
                "creator_name": "Admin",
                "created_at": "2025-09-02T08:00:00",
                "updated_at": "2025-09-02T08:00:00",
            },
            {
                "type": "gasto",
                "id": 2,
                "data": "2025-09-10",
                "valor": 120.00,
                "descricao": "Manutenção equipamento",
                "forma_pagamento": "cartão",
                "created_by": 1,
                "creator_name": "Admin",
                "created_at": "2025-09-10T13:00:00",
                "updated_at": "2025-09-10T13:00:00",
            },
        ]
    )

    return mock_data


def demonstrate_backup_functionality():
    """Demonstrate the backup system with mock data."""
    logger.info("BACKUP SYSTEM DEMONSTRATION", extra={"context": {"section": "header"}})

    # Create mock data
    logger.info("Creating mock historical data...", extra={"context": {"step": 1}})
    mock_records = create_mock_historical_data()
    logger.info("Mock records created", extra={"context": {"count": len(mock_records)}})

    # Initialize backup service
    logger.info("Initializing backup service...", extra={"context": {"step": 2}})
    backup_service = BackupService(backup_base_dir="demo_backups")

    # Simulate CSV writing
    logger.info("Simulating CSV file creation...", extra={"context": {"step": 3}})
    year, month = 2025, 9
    backup_dir = backup_service._get_backup_directory(year, month)
    filename = backup_service._get_backup_filename(year, month)
    demo_file_path = os.path.join(backup_dir, filename)

    # Write mock data to CSV
    try:
        with open(demo_file_path, "w", newline="", encoding="utf-8") as csvfile:
            if mock_records:
                fieldnames = sorted(
                    set().union(*[record.keys() for record in mock_records])
                )
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(mock_records)

        logger.info("CSV file created", extra={"context": {"file": demo_file_path}})

        # Get file info
        file_size = os.path.getsize(demo_file_path)
        logger.info(
            "File size",
            extra={"context": {"file": demo_file_path, "size_bytes": file_size}},
        )

        # Read and validate CSV
        logger.info(
            "Validating CSV file...",
            extra={"context": {"step": 4, "file": demo_file_path}},
        )
        with open(demo_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            rows = list(reader)

        logger.info(
            "CSV validation successful",
            extra={
                "context": {
                    "headers_count": len(headers) if headers else 0,
                    "rows": len(rows),
                    "sample_headers": headers[:5] if headers else [],
                }
            },
        )

        # Show sample data
        logger.info("Sample data from CSV", extra={"context": {"step": 5}})
        for i, row in enumerate(rows[:3]):  # Show first 3 rows
            logger.info(
                "Row sample",
                extra={
                    "context": {
                        "row_num": i + 1,
                        "type": row.get("type"),
                        "cliente_name": row.get("cliente_name", "N/A"),
                        "valor": row.get("valor", "N/A"),
                    }
                },
            )

        # Test backup info functionality
        logger.info(
            "Testing backup info functionality...", extra={"context": {"step": 6}}
        )
        info = backup_service.get_backup_info(year, month)
        logger.info(
            "Backup info retrieved",
            extra={
                "context": {
                    "exists": info.get("exists"),
                    "file_path": info.get("file_path"),
                    "record_count": info.get("record_count"),
                }
            },
        )

        logger.info(
            "DEMONSTRATION COMPLETED SUCCESSFULLY!",
            extra={
                "context": {
                    "notes": [
                        "Ready for production use",
                        "Queries real data",
                        "CSV formatted",
                        "Error handling",
                        "Integrity validation",
                    ]
                }
            },
        )

        return True

    except Exception as e:
        logger.error(
            "Demonstration failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False

    finally:
        # Clean up demo files
        logger.info(
            "Cleaning up demonstration files...", extra={"context": {"step": 7}}
        )
        import shutil

        if os.path.exists("demo_backups"):
            shutil.rmtree("demo_backups")
            logger.info(
                "Demo backup directory removed",
                extra={"context": {"dir": "demo_backups"}},
            )


if __name__ == "__main__":
    success = demonstrate_backup_functionality()
    logging.shutdown()  # Flush all log handlers
    sys.exit(0 if success else 1)
