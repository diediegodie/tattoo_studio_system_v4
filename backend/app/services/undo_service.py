"""
Undo service for extrato operations.

Provides functionality to:
- Create snapshots before transfers
- Store snapshots for potential rollback
- Restore data from snapshots
- Clean up old snapshots
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.db.base import Extrato, ExtratoSnapshot
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class UndoService:
    """Service for managing extrato undo operations."""

    def __init__(self):
        self.retention_days = 30  # Keep snapshots for 30 days

    def create_snapshot(self, mes: int, ano: int, correlation_id: str) -> str:
        """
        Create a snapshot of current extrato data before transfer.

        Args:
            mes: Month of the extrato
            ano: Year of the extrato
            correlation_id: Correlation ID for tracking

        Returns:
            Snapshot ID
        """
        snapshot_id = str(uuid.uuid4())[:8]

        db = SessionLocal()
        try:
            # Check if extrato exists
            existing_extrato = (
                db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
            )

            if not existing_extrato:
                logger.info(
                    f"No existing extrato found for {mes}/{ano}, skipping snapshot"
                )
                return snapshot_id

            # Create snapshot data
            snapshot_data = {
                "extrato_id": existing_extrato.id,
                "mes": existing_extrato.mes,
                "ano": existing_extrato.ano,
                "pagamentos": existing_extrato.pagamentos,
                "sessoes": existing_extrato.sessoes,
                "comissoes": existing_extrato.comissoes,
                "gastos": existing_extrato.gastos,
                "totais": existing_extrato.totais,
                "created_at": getattr(existing_extrato, "created_at", None),
                "correlation_id": correlation_id,
            }
            # Convert created_at to ISO format if it exists
            if snapshot_data["created_at"]:
                snapshot_data["created_at"] = snapshot_data["created_at"].isoformat()

            # Store snapshot
            snapshot = ExtratoSnapshot(
                snapshot_id=snapshot_id,
                mes=mes,
                ano=ano,
                data=json.dumps(snapshot_data),
                created_at=datetime.now(),
                correlation_id=correlation_id,
            )

            db.add(snapshot)
            db.commit()

            logger.info(
                f"Created snapshot {snapshot_id} for extrato {mes}/{ano} with correlation {correlation_id}"
            )
            return snapshot_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating snapshot for {mes}/{ano}: {str(e)}")
            raise
        finally:
            db.close()

    def restore_from_snapshot(self, snapshot_id: str, correlation_id: str) -> bool:
        """
        Restore extrato data from a snapshot.

        Args:
            snapshot_id: ID of the snapshot to restore from
            correlation_id: Correlation ID for tracking

        Returns:
            True if successful, False otherwise
        """
        db = SessionLocal()
        try:
            # Find snapshot
            snapshot = (
                db.query(ExtratoSnapshot)
                .filter(ExtratoSnapshot.snapshot_id == snapshot_id)
                .first()
            )

            if not snapshot:
                logger.error(f"Snapshot {snapshot_id} not found")
                return False

            # Parse snapshot data
            snapshot_data = json.loads(getattr(snapshot, "data", "{}"))

            # Find or create extrato record
            extrato = (
                db.query(Extrato)
                .filter(
                    Extrato.mes == snapshot_data["mes"],
                    Extrato.ano == snapshot_data["ano"],
                )
                .first()
            )

            if not extrato:
                # Create new extrato record
                extrato = Extrato(mes=snapshot_data["mes"], ano=snapshot_data["ano"])
                db.add(extrato)

            # Restore data
            extrato.receita_total = snapshot_data.get("receita_total", 0)
            extrato.comissoes_total = snapshot_data.get("comissoes_total", 0)
            extrato.gastos_total = snapshot_data.get("gastos_total", 0)
            extrato.lucro_total = snapshot_data.get("lucro_total", 0)
            extrato.sessoes_count = snapshot_data.get("sessoes_count", 0)
            extrato.pagamentos_count = snapshot_data.get("pagamentos_count", 0)

            # Update timestamps
            created_at_str = snapshot_data.get("created_at")
            if created_at_str:
                setattr(extrato, "created_at", datetime.fromisoformat(created_at_str))
            if snapshot_data.get("updated_at"):
                extrato.updated_at = datetime.fromisoformat(snapshot_data["updated_at"])

            db.commit()

            logger.info(
                f"Restored extrato {snapshot_data['mes']}/{snapshot_data['ano']} from snapshot {snapshot_id} with correlation {correlation_id}"
            )
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error restoring from snapshot {snapshot_id}: {str(e)}")
            return False
        finally:
            db.close()

    def list_snapshots(
        self, mes: Optional[int] = None, ano: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List available snapshots.

        Args:
            mes: Filter by month (optional)
            ano: Filter by year (optional)

        Returns:
            List of snapshot information
        """
        db = SessionLocal()
        try:
            query = db.query(ExtratoSnapshot)

            if mes is not None:
                query = query.filter(ExtratoSnapshot.mes == mes)
            if ano is not None:
                query = query.filter(ExtratoSnapshot.ano == ano)

            snapshots = query.order_by(ExtratoSnapshot.created_at.desc()).all()

            result = []
            for snapshot in snapshots:
                result.append(
                    {
                        "snapshot_id": snapshot.snapshot_id,
                        "mes": snapshot.mes,
                        "ano": snapshot.ano,
                        "created_at": snapshot.created_at.isoformat(),
                        "correlation_id": snapshot.correlation_id,
                        "data_size": (
                            len(getattr(snapshot, "data", ""))
                            if getattr(snapshot, "data", None)
                            else 0
                        ),
                    }
                )

            return result

        finally:
            db.close()

    def cleanup_old_snapshots(self) -> int:
        """
        Clean up snapshots older than retention period.

        Returns:
            Number of snapshots deleted
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        db = SessionLocal()
        try:
            deleted_count = (
                db.query(ExtratoSnapshot)
                .filter(ExtratoSnapshot.created_at < cutoff_date)
                .delete()
            )

            db.commit()

            logger.info(f"Cleaned up {deleted_count} old snapshots")
            return deleted_count

        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up old snapshots: {str(e)}")
            return 0
        finally:
            db.close()

    def get_snapshot_details(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a snapshot.

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            Snapshot details or None if not found
        """
        db = SessionLocal()
        try:
            snapshot = (
                db.query(ExtratoSnapshot)
                .filter(ExtratoSnapshot.snapshot_id == snapshot_id)
                .first()
            )

            if not snapshot:
                return None

            snapshot_data = (
                json.loads(getattr(snapshot, "data", "{}"))
                if getattr(snapshot, "data", None)
                else {}
            )

            return {
                "snapshot_id": snapshot.snapshot_id,
                "mes": snapshot.mes,
                "ano": snapshot.ano,
                "created_at": snapshot.created_at.isoformat(),
                "correlation_id": snapshot.correlation_id,
                "data": snapshot_data,
            }

        finally:
            db.close()
