"""
Backup service for exporting historical data to CSV files.
Following SOLID principles with single responsibility for backup operations.
"""

import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.db.base import Pagamento, Sessao, Comissao, Gasto, Client, User

logger = logging.getLogger(__name__)


class BackupService:
    """
    Service responsible for backing up historical data to CSV files.

    Single Responsibility: Handle all backup-related operations including
    data retrieval, CSV generation, file management, and validation.
    """

    def __init__(self, backup_base_dir: str = "backups"):
        """
        Initialize backup service.

        Args:
            backup_base_dir: Base directory for storing backup files
        """
        self.backup_base_dir = backup_base_dir
        self._ensure_backup_directory_exists()
        self._ensure_logs_directory_exists()

    def _ensure_backup_directory_exists(self) -> None:
        """Create backup directory structure if it doesn't exist."""
        if not os.path.exists(self.backup_base_dir):
            os.makedirs(self.backup_base_dir)
            logger.info(f"Created backup directory: {self.backup_base_dir}")

    def _ensure_logs_directory_exists(self) -> None:
        """Create logs directory if it doesn't exist."""
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            logger.info(f"Created logs directory: {logs_dir}")

    def _get_backup_directory(self, year: int, month: int) -> str:
        """
        Get the backup directory path for a specific year and month.

        Args:
            year: Year for the backup
            month: Month for the backup

        Returns:
            Path to the backup directory
        """
        dir_path = os.path.join(self.backup_base_dir, f"{year:04d}_{month:02d}")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"Created backup subdirectory: {dir_path}")
        return dir_path

    def _get_backup_filename(self, year: int, month: int) -> str:
        """
        Generate backup filename for the given year and month.

        Args:
            year: Year for the backup
            month: Month for the backup

        Returns:
            Backup filename
        """
        return f"backup_{year:04d}_{month:02d}.csv"

    def _query_historical_data(
        self, db, year: int, month: int
    ) -> Tuple[List, List, List, List]:
        """
        Query all historical data for the specified month and year.

        Args:
            db: Database session
            year: Year to query
            month: Month to query

        Returns:
            Tuple of (pagamentos, sessoes, comissoes, gastos)
        """
        logger.info(f"Querying historical data for {month:02d}/{year}")

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Query Pagamentos with relationships
        pagamentos = (
            db.query(Pagamento)
            .options(
                joinedload(Pagamento.cliente),
                joinedload(Pagamento.artista),
                joinedload(Pagamento.sessao),
            )
            .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
            .all()
        )

        # Query Sessoes with relationships
        sessoes = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .filter(Sessao.data >= start_date, Sessao.data < end_date)
            .all()
        )

        # Query Comissoes with relationships
        comissoes = (
            db.query(Comissao)
            .options(
                joinedload(Comissao.artista),
                joinedload(Comissao.pagamento).joinedload(Pagamento.cliente),
                joinedload(Comissao.pagamento).joinedload(Pagamento.sessao),
            )
            .filter(Comissao.created_at >= start_date, Comissao.created_at < end_date)
            .all()
        )

        # Query Gastos with relationships
        gastos = (
            db.query(Gasto)
            .options(joinedload(Gasto.creator))
            .filter(Gasto.data >= start_date, Gasto.data < end_date)
            .all()
        )

        logger.info(
            f"Found {len(pagamentos)} payments, {len(sessoes)} sessions, "
            f"{len(comissoes)} commissions, {len(gastos)} expenses"
        )

        return pagamentos, sessoes, comissoes, gastos

    def _serialize_historical_data(
        self, pagamentos: List, sessoes: List, comissoes: List, gastos: List
    ) -> List[Dict[str, Any]]:
        """
        Serialize all historical data into a list of dictionaries for CSV export.

        Args:
            pagamentos: List of Pagamento objects
            sessoes: List of Sessao objects
            comissoes: List of Comissao objects
            gastos: List of Gasto objects

        Returns:
            List of dictionaries representing all historical records
        """
        logger.info("Serializing historical data for CSV export")
        records = []

        # Serialize Pagamentos
        for p in pagamentos:
            record = {
                "type": "pagamento",
                "id": p.id,
                "data": p.data.isoformat() if p.data else "",
                "valor": float(p.valor) if p.valor else 0.0,
                "forma_pagamento": p.forma_pagamento or "",
                "observacoes": p.observacoes or "",
                "cliente_name": p.cliente.name if p.cliente else "",
                "artista_name": p.artista.name if p.artista else "",
                "sessao_id": p.sessao_id,
                "created_at": p.created_at.isoformat() if p.created_at else "",
                "updated_at": p.updated_at.isoformat() if p.updated_at else "",
            }
            records.append(record)

        # Serialize Sessoes
        for s in sessoes:
            record = {
                "type": "sessao",
                "id": s.id,
                "data": s.data.isoformat() if s.data else "",
                "hora": s.hora.isoformat() if s.hora else "",
                "valor": float(s.valor) if s.valor else 0.0,
                "observacoes": s.observacoes or "",
                "status": s.status or "",
                "cliente_name": s.cliente.name if s.cliente else "",
                "artista_name": s.artista.name if s.artista else "",
                "google_event_id": s.google_event_id or "",
                "payment_id": s.payment_id,
                "created_at": s.created_at.isoformat() if s.created_at else "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
            }
            records.append(record)

        # Serialize Comissoes
        for c in comissoes:
            cliente_name = ""
            if c.pagamento and c.pagamento.cliente:
                cliente_name = c.pagamento.cliente.name

            record = {
                "type": "comissao",
                "id": c.id,
                "pagamento_id": c.pagamento_id,
                "artista_name": c.artista.name if c.artista else "",
                "cliente_name": cliente_name,
                "percentual": float(c.percentual) if c.percentual else 0.0,
                "valor": float(c.valor) if c.valor else 0.0,
                "observacoes": c.observacoes or "",
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            records.append(record)

        # Serialize Gastos
        for g in gastos:
            record = {
                "type": "gasto",
                "id": g.id,
                "data": g.data.isoformat() if g.data else "",
                "valor": float(g.valor) if g.valor else 0.0,
                "descricao": g.descricao or "",
                "forma_pagamento": g.forma_pagamento or "",
                "created_by": g.created_by,
                "creator_name": g.creator.name if g.creator else "",
                "created_at": g.created_at.isoformat() if g.created_at else "",
                "updated_at": g.updated_at.isoformat() if g.updated_at else "",
            }
            records.append(record)

        logger.info(f"Serialized {len(records)} total records")
        return records

    def _write_csv_file(self, records: List[Dict[str, Any]], file_path: str) -> bool:
        """
        Write records to CSV file.

        Args:
            records: List of dictionaries to write
            file_path: Path to the CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Writing {len(records)} records to CSV file: {file_path}")

            if not records:
                logger.warning("No records to write to CSV")
                return False

            # Get all unique keys from all records
            fieldnames = set()
            for record in records:
                fieldnames.update(record.keys())
            fieldnames = sorted(fieldnames)

            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)

            logger.info(f"Successfully wrote CSV file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing CSV file {file_path}: {str(e)}")
            return False

    def _validate_csv_file(self, file_path: str) -> bool:
        """
        Validate that the CSV file was created successfully and is readable.

        Args:
            file_path: Path to the CSV file

        Returns:
            True if file is valid, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"CSV file does not exist: {file_path}")
                return False

            file_size = os.path.getsize(file_path)
            logger.info(f"CSV file created successfully. Size: {file_size} bytes")

            # Try to read the file to ensure it's valid
            with open(file_path, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                row_count = sum(1 for row in reader)

            logger.info(
                f"CSV file validation successful. Contains {row_count} data rows"
            )
            return True

        except Exception as e:
            logger.error(f"Error validating CSV file {file_path}: {str(e)}")
            return False

    def create_backup(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Create a backup of all historical data for the specified month and year.

        Args:
            year: Year to backup (defaults to current year)
            month: Month to backup (defaults to current month)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Use current month/year if not specified
            now = datetime.now()
            if year is None:
                year = now.year
            if month is None:
                month = now.month

            logger.info(f"Starting backup process for {month:02d}/{year}")

            # Get backup file path
            backup_dir = self._get_backup_directory(year, month)
            filename = self._get_backup_filename(year, month)
            file_path = os.path.join(backup_dir, filename)

            # Check if backup already exists
            if os.path.exists(file_path):
                logger.warning(f"Backup file already exists: {file_path}")
                return False, f"Backup already exists for {month:02d}/{year}"

            # Query historical data
            db = SessionLocal()
            try:
                pagamentos, sessoes, comissoes, gastos = self._query_historical_data(
                    db, year, month
                )

                if not any([pagamentos, sessoes, comissoes, gastos]):
                    logger.info(f"No historical data found for {month:02d}/{year}")
                    return True, f"No data to backup for {month:02d}/{year}"

                # Serialize data
                records = self._serialize_historical_data(
                    pagamentos, sessoes, comissoes, gastos
                )

                # Write CSV file
                if not self._write_csv_file(records, file_path):
                    return False, "Failed to write CSV file"

                # Validate CSV file
                if not self._validate_csv_file(file_path):
                    return False, "CSV file validation failed"

                logger.info(f"Backup completed successfully: {file_path}")
                return True, f"Backup created successfully: {file_path}"

            finally:
                db.close()

        except Exception as e:
            error_msg = f"Backup failed for {month:02d}/{year}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def verify_backup_exists(self, year: int, month: int) -> bool:
        """
        Verify that a backup exists for the specified month and year.

        Args:
            year: Year to check
            month: Month to check

        Returns:
            True if backup exists and is valid, False otherwise
        """
        try:
            backup_dir = self._get_backup_directory(year, month)
            filename = self._get_backup_filename(year, month)
            file_path = os.path.join(backup_dir, filename)

            if not os.path.exists(file_path):
                logger.warning(f"Backup file does not exist: {file_path}")
                return False

            # Validate the file
            return self._validate_csv_file(file_path)

        except Exception as e:
            logger.error(f"Error verifying backup for {month:02d}/{year}: {str(e)}")
            return False

    def get_backup_info(self, year: int, month: int) -> Dict[str, Any]:
        """
        Get information about a backup file.

        Args:
            year: Year of the backup
            month: Month of the backup

        Returns:
            Dictionary with backup information
        """
        try:
            backup_dir = self._get_backup_directory(year, month)
            filename = self._get_backup_filename(year, month)
            file_path = os.path.join(backup_dir, filename)

            if not os.path.exists(file_path):
                return {
                    "exists": False,
                    "file_path": file_path,
                    "file_size": 0,
                    "record_count": 0,
                    "created_at": None,
                }

            file_size = os.path.getsize(file_path)
            created_at = datetime.fromtimestamp(os.path.getctime(file_path))

            # Count records
            record_count = 0
            try:
                with open(file_path, "r", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    record_count = sum(1 for row in reader)
            except Exception as e:
                logger.warning(f"Could not count records in {file_path}: {str(e)}")

            return {
                "exists": True,
                "file_path": file_path,
                "file_size": file_size,
                "record_count": record_count,
                "created_at": created_at.isoformat(),
                "year": year,
                "month": month,
            }

        except Exception as e:
            logger.error(f"Error getting backup info for {month:02d}/{year}: {str(e)}")
            return {"exists": False, "error": str(e)}
