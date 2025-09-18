"""
Extrato Core Service - Basic utilities and data processing.

This module contains the core utilities for extrato processing,
including data querying, serialization, calculation, and validation.
"""

import json
import os
import logging
import uuid
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Tuple, Any
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.base import (
    Pagamento,
    Sessao,
    Comissao,
    Extrato,
    Client,
    User,
    ExtratoRunLog,
    Gasto,
)
from app.services.undo_service import UndoService
from app.services.backup_service import BackupService

# Configure logging
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs("backend/logs", exist_ok=True)

# Add rotating file handler for extrato operations
extrato_handler = RotatingFileHandler(
    "backend/logs/extrato_operations.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
extrato_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s",
        defaults={"correlation_id": "N/A"},
    )
)
logger.addHandler(extrato_handler)
logger.setLevel(logging.INFO)


def get_previous_month():
    """Get the previous month and year."""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    return last_day_prev_month.month, last_day_prev_month.year


def check_existing_extrato(db, mes, ano, force=False):
    """Check if extrato already exists for the month/year."""
    existing = db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
    if existing:
        if not force:
            print(
                f"ERROR: Extrato for {mes}/{ano} already exists. Use --force to overwrite."
            )
            return False
        else:
            print(f"WARNING: Overwriting existing extrato for {mes}/{ano}.")
            db.delete(existing)
            db.commit()
    return True


def query_data(db, mes, ano):
    """Query Pagamento, Sessao, Comissao, Gasto for the month/year."""
    start_date = datetime(ano, mes, 1)
    if mes == 12:
        end_date = datetime(ano + 1, 1, 1)
    else:
        end_date = datetime(ano, mes + 1, 1)

    # Query Pagamentos with joins
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

    # Query Sessoes
    sessoes = (
        db.query(Sessao)
        .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
        .filter(Sessao.data >= start_date, Sessao.data < end_date)
        .all()
    )

    # Query Comissoes with joins
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

    # Query Gastos
    gastos = (
        db.query(Gasto)
        .options(joinedload(Gasto.creator))
        .filter(Gasto.data >= start_date, Gasto.data < end_date)
        .all()
    )

    return pagamentos, sessoes, comissoes, gastos


def serialize_data(pagamentos, sessoes, comissoes, gastos):
    """Serialize data into JSON-compatible dicts."""
    pagamentos_data = []
    for p in pagamentos:
        pagamentos_data.append(
            {
                "data": p.data.isoformat() if p.data else None,
                "cliente_name": p.cliente.name if p.cliente else None,
                "artista_name": p.artista.name if p.artista else None,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "observacoes": p.observacoes,
                "sessao_data": (
                    p.sessao.data.isoformat() if p.sessao and p.sessao.data else None
                ),
            }
        )

    sessoes_data = []
    for s in sessoes:
        sessoes_data.append(
            {
                "data": s.data.isoformat() if s.data else None,
                "hora": s.hora.isoformat() if s.hora else None,
                "cliente_name": s.cliente.name if s.cliente else None,
                "artista_name": s.artista.name if s.artista else None,
                "valor": float(s.valor),
                "status": s.status,
                "observacoes": s.observacoes,
            }
        )

    comissoes_data = []
    for c in comissoes:
        cliente_name = (
            c.pagamento.sessao.cliente.name
            if c.pagamento and c.pagamento.sessao and c.pagamento.sessao.cliente
            else None
        )
        comissoes_data.append(
            {
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "artista_name": c.artista.name if c.artista else None,
                "cliente_name": cliente_name,
                "pagamento_valor": float(c.pagamento.valor) if c.pagamento else None,
                "percentual": float(c.percentual),
                "valor": float(c.valor),
                "observacoes": c.observacoes,
            }
        )

    gastos_data = []
    for g in gastos:
        categoria = getattr(g, "categoria", None)  # Optional, forward-compatible
        gastos_data.append(
            {
                "data": g.data.isoformat() if g.data else None,
                "valor": float(g.valor),
                "descricao": g.descricao,
                "forma_pagamento": g.forma_pagamento,
                "categoria": categoria,
                "created_by": g.created_by,
            }
        )

    return pagamentos_data, sessoes_data, comissoes_data, gastos_data


def calculate_totals(pagamentos_data, sessoes_data, comissoes_data, gastos_data=None):
    """Calculate totals including despesas if provided."""
    import os

    gastos_data = gastos_data or []

    # FIXED: Calculate revenue from payments only (actual money received)
    # Previous logic incorrectly double-counted by adding sessions + payments
    receita_total = sum(float(p.get("valor", 0)) for p in pagamentos_data)
    comissoes_total = sum(float(c.get("valor", 0)) for c in comissoes_data)
    despesas_total = sum(float(g.get("valor", 0)) for g in gastos_data)

    # Debug logging if enabled
    if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
        logger.info(
            f"HISTORICO_DEBUG: calculate_totals - receita_total:{receita_total} comissoes_total:{comissoes_total} despesas_total:{despesas_total}"
        )

    # ...existing code...

    # Por artista
    artistas = {}
    for p in pagamentos_data:
        artista = p["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
            artistas[artista]["receita"] += p["valor"]

    for s in sessoes_data:
        artista = s["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
            artistas[artista]["receita"] += s["valor"]

    for c in comissoes_data:
        artista = c["artista_name"]
        if artista and artista in artistas:
            artistas[artista]["comissao"] += c["valor"]

    por_artista = [
        {"artista": k, "receita": v["receita"], "comissao": v["comissao"]}
        for k, v in artistas.items()
    ]

    # Por forma de pagamento (receitas)
    formas = {}
    for p in pagamentos_data:
        forma = p["forma_pagamento"]
        if forma:
            formas[forma] = formas.get(forma, 0) + p["valor"]

    por_forma_pagamento = [{"forma": k, "total": v} for k, v in formas.items()]

    # Gastos por forma de pagamento
    gastos_por_forma = {}
    for g in gastos_data:
        forma = g.get("forma_pagamento")
        if forma:
            gastos_por_forma[forma] = gastos_por_forma.get(forma, 0) + g["valor"]
    gastos_por_forma_pagamento = [
        {"forma": k, "total": v} for k, v in gastos_por_forma.items()
    ]

    # Gastos por categoria (optional field)
    gastos_por_categoria_map = {}
    for g in gastos_data:
        categoria = g.get("categoria") or "Outros"
        gastos_por_categoria_map[categoria] = (
            gastos_por_categoria_map.get(categoria, 0) + g["valor"]
        )
    gastos_por_categoria = [
        {"categoria": k, "total": v} for k, v in gastos_por_categoria_map.items()
    ]

    saldo = receita_total - despesas_total  # commissions shown separately
    receita_liquida = receita_total - comissoes_total  # for UI display

    return {
        "receita_total": receita_total,
        "comissoes_total": comissoes_total,
        "despesas_total": despesas_total,
        "saldo": saldo,
        "receita_liquida": receita_liquida,
        "por_artista": por_artista,
        "por_forma_pagamento": por_forma_pagamento,
        "gastos_por_forma_pagamento": gastos_por_forma_pagamento,
        "gastos_por_categoria": gastos_por_categoria,
    }


def verify_backup_before_transfer(year: int, month: int) -> bool:
    """
    Verify that a backup exists and is valid before proceeding with data transfer.

    Args:
        year: Year of the backup to verify
        month: Month of the backup to verify

    Returns:
        True if backup exists and is valid, False otherwise
    """
    logger.info(f"Verifying backup exists for {month:02d}/{year} before data transfer")

    try:
        backup_service = BackupService()
        backup_exists = backup_service.verify_backup_exists(year, month)

        if backup_exists:
            logger.info(f"✓ Backup verification successful for {month:02d}/{year}")
            return True
        else:
            logger.error(f"✗ Backup verification failed for {month:02d}/{year}")
            return False

    except Exception as e:
        logger.error(
            f"Error during backup verification for {month:02d}/{year}: {str(e)}"
        )
        return False


def delete_historical_records_atomic(
    db_session,
    pagamentos: list,
    sessoes: list,
    comissoes: list,
    gastos: list,
    mes: int,
    ano: int,
    correlation_id: Optional[str] = None,
) -> bool:
    """
    Safely delete historical records from the database within an atomic transaction.

    This function handles the deletion of records from the historico tables in the correct
    dependency order to maintain referential integrity. All deletions occur within the
    provided database session/transaction.

    Args:
        db_session: Active SQLAlchemy session (within transaction)
        pagamentos: List of Pagamento objects to delete
        sessoes: List of Sessao objects to delete
        comissoes: List of Comissao objects to delete
        gastos: List of Gasto objects to delete
        mes: Month of the records being deleted
        ano: Year of the records being deleted

    Returns:
        True if all deletions successful, False if any deletion failed

    Note:
        This function assumes it's being called within an active transaction.
        The caller is responsible for commit/rollback.
    """
    extra = {"correlation_id": correlation_id} if correlation_id else {}

    try:
        logger.info(
            f"Starting deletion of historical records for {mes:02d}/{ano}", extra=extra
        )

        total_records = len(pagamentos) + len(sessoes) + len(comissoes) + len(gastos)
        if total_records == 0:
            logger.info("No records to delete", extra=extra)
            return True

        logger.info(
            f"Deleting {total_records} total records in dependency order", extra=extra
        )

        # Step 1: Delete commissions first (they depend on payments)
        # Commissions have foreign key to pagamentos, so delete them first
        deleted_comissoes = 0
        for comissao in comissoes:
            try:
                db_session.delete(comissao)
                deleted_comissoes += 1
            except Exception as e:
                logger.error(
                    f"Failed to delete commission {comissao.id}: {str(e)}", extra=extra
                )
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_comissoes} commissions", extra=extra)

        # Step 2: Break circular references between Sessao and Pagamento
        # This prevents foreign key constraint violations when deleting payments/sessions
        logger.info(
            "Breaking circular references between sessions and payments", extra=extra
        )
        for sessao in sessoes:
            try:
                # Set payment_id to None to break the circular reference
                setattr(sessao, "payment_id", None)
                logger.debug(
                    f"Set payment_id to None for session {sessao.id}", extra=extra
                )
            except Exception as e:
                logger.error(
                    f"Failed to break reference for session {sessao.id}: {str(e)}",
                    extra=extra,
                )
                raise  # Re-raise to trigger transaction rollback

        logger.info(
            "✓ Broke circular references between sessions and payments", extra=extra
        )

        # Step 3: Delete payments (now safe to delete since references are broken)
        deleted_pagamentos = 0
        for pagamento in pagamentos:
            try:
                db_session.delete(pagamento)
                deleted_pagamentos += 1
            except Exception as e:
                logger.error(
                    f"Failed to delete payment {pagamento.id}: {str(e)}", extra=extra
                )
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_pagamentos} payments", extra=extra)

        # Step 4: Delete sessions (now safe to delete)
        deleted_sessoes = 0
        for sessao in sessoes:
            try:
                db_session.delete(sessao)
                deleted_sessoes += 1
            except Exception as e:
                logger.error(
                    f"Failed to delete session {sessao.id}: {str(e)}", extra=extra
                )
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_sessoes} sessions", extra=extra)

        # Step 5: Delete expenses (independent table, no dependencies)
        deleted_gastos = 0
        for gasto in gastos:
            try:
                db_session.delete(gasto)
                deleted_gastos += 1
            except Exception as e:
                logger.error(
                    f"Failed to delete expense {gasto.id}: {str(e)}", extra=extra
                )
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_gastos} expenses", extra=extra)

        # Verify all records were deleted
        expected_deletions = (
            len(pagamentos) + len(sessoes) + len(comissoes) + len(gastos)
        )
        actual_deletions = (
            deleted_pagamentos + deleted_sessoes + deleted_comissoes + deleted_gastos
        )

        if actual_deletions != expected_deletions:
            error_msg = f"Deletion count mismatch: expected {expected_deletions}, got {actual_deletions}"
            logger.error(error_msg, extra=extra)
            raise ValueError(error_msg)

        logger.info(
            f"✓ Successfully deleted all {actual_deletions} historical records for {mes:02d}/{ano}",
            extra=extra,
        )
        return True

    except Exception as e:
        logger.error(f"Error during historical records deletion: {str(e)}", extra=extra)
        raise  # Re-raise to ensure transaction rollback


def _log_extrato_run(mes, ano, status, message=None):
    """Log an extrato generation run to the database."""
    from app.db.session import SessionLocal
    from app.db.base import ExtratoRunLog

    db = SessionLocal()
    try:
        run_log = ExtratoRunLog(mes=mes, ano=ano, status=status, message=message)
        db.add(run_log)
        db.commit()
    except Exception as e:
        print(f"Warning: Could not log extrato run: {e}")
    finally:
        db.close()


def current_month_range():
    """Compute start and end datetime for the current month (server-local time).

    Returns (start_date, end_date) as naive datetime objects.
    TODO: Consider timezone handling if app spans multiple timezones.
    """
    from datetime import datetime

    now = datetime.now()
    start_date = datetime(now.year, now.month, 1)
    if now.month == 12:
        end_date = datetime(now.year + 1, 1, 1)
    else:
        end_date = datetime(now.year, now.month + 1, 1)
    return start_date, end_date
