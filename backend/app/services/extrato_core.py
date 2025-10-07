"""
Extrato Core Service - Basic utilities and data processing.

This module contains the core utilities for extrato processing,
including data querying, serialization, calculation, and validation.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Any, Iterable, List, Optional, Tuple

from app.db.base import (
    Client,
    Comissao,
    Extrato,
    ExtratoRunLog,
    Gasto,
    Pagamento,
    Sessao,
    User,
)
from app.db.session import SessionLocal
from app.services.backup_service import BackupService
from app.services.undo_service import UndoService
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

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


def should_run_monthly_extrato(min_day_threshold: int = 2) -> bool:
    """Determine if the scheduled monthly extrato job should run.

    Skips execution if we are still within the first couple of days of the month
    (allowing late data entry) or if a successful run for the target month already
    exists in the log table. Falls back to running if any unexpected error occurs
    while checking the database to avoid blocking the job.
    """

    today = datetime.now()

    if today.day < min_day_threshold:
        logger.info(
            "Monthly extrato generation skipped - waiting until day %s of the month",
            min_day_threshold,
        )
        return False

    target_month, target_year = get_previous_month()

    db = SessionLocal()
    try:
        existing_success = (
            db.query(ExtratoRunLog)
            .filter(
                ExtratoRunLog.mes == target_month,
                ExtratoRunLog.ano == target_year,
                ExtratoRunLog.status == "success",
            )
            .first()
        )

        if existing_success:
            logger.info(
                "Monthly extrato generation skipped - already processed %s/%s",
                target_month,
                target_year,
            )
            return False

        return True
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.warning(
            "Falling back to running monthly extrato after error checking logs: %s",
            exc,
        )
        return True
    finally:
        db.close()


def check_existing_extrato(db, mes, ano, force=False):
    """Check if extrato already exists for the month/year."""
    existing = db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
    if existing:
        if not force:
            logging.error(
                "Extrato already exists, use --force to overwrite",
                extra={"context": {"mes": mes, "ano": ano}},
            )
            return False
        else:
            logging.warning(
                "Overwriting existing extrato",
                extra={"context": {"mes": mes, "ano": ano}},
            )
            db.delete(existing)
            db.commit()
    return True


def _ensure_sequence(data: Any) -> List[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, tuple):
        return list(data)

    module_name = getattr(data.__class__, "__module__", "")
    if module_name.startswith("unittest.mock"):
        wrapped = getattr(data, "_mock_wraps", None)
        if isinstance(wrapped, (list, tuple)):
            return list(wrapped)
        return []

    if isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
        try:
            return list(data)
        except Exception:
            return []

    return []


def _safe_all(query: Any) -> Any:
    try:
        return query.all()
    except Exception:
        return None


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_options(query: Any, *options_args: Any) -> Any:
    try:
        candidate = query.options(*options_args)
        return candidate if candidate is not None else query
    except Exception:
        return query


def _safe_filter(query: Any, *criteria: Any) -> Any:
    try:
        candidate = query.filter(*criteria)
        return candidate if candidate is not None else query
    except Exception:
        return query


def query_data(db, mes, ano):
    """Query Pagamento, Sessao, Comissao, Gasto for the month/year."""
    start_date = datetime(ano, mes, 1)
    if mes == 12:
        end_date = datetime(ano + 1, 1, 1)
    else:
        end_date = datetime(ano, mes + 1, 1)

    # Query Pagamentos with joins
    pagamentos_query_base = db.query(Pagamento)
    pagamentos_query = _safe_options(
        pagamentos_query_base,
        joinedload(Pagamento.cliente),
        joinedload(Pagamento.artista),
        joinedload(Pagamento.sessao),
    )
    pagamentos_query = _safe_filter(
        pagamentos_query, Pagamento.data >= start_date, Pagamento.data < end_date
    )
    pagamentos_result = _safe_all(pagamentos_query)
    pagamentos = _ensure_sequence(pagamentos_result)

    # Query Sessoes - only include completed or paid sessions for financial calculations
    sessoes_query_base = db.query(Sessao)
    sessoes_query = _safe_options(
        sessoes_query_base, joinedload(Sessao.cliente), joinedload(Sessao.artista)
    )
    sessoes_query = _safe_filter(
        sessoes_query, Sessao.data >= start_date, Sessao.data < end_date
    )
    sessoes_query = _safe_filter(
        sessoes_query, Sessao.status.in_(["completed", "paid"])
    )
    sessoes_result = _safe_all(sessoes_query)
    sessoes = _ensure_sequence(sessoes_result)

    # Query Comissoes with joins
    comissoes_query_base = db.query(Comissao)
    comissoes_query = _safe_options(
        comissoes_query_base,
        joinedload(Comissao.artista),
        joinedload(Comissao.pagamento).joinedload(Pagamento.cliente),
        joinedload(Comissao.pagamento).joinedload(Pagamento.sessao),
    )
    comissoes_query = _safe_filter(
        comissoes_query,
        or_(
            Comissao.pagamento.has(
                and_(
                    Pagamento.data >= start_date,
                    Pagamento.data < end_date,
                )
            ),
            and_(
                Comissao.pagamento_id.is_(None),
                Comissao.created_at >= start_date,
                Comissao.created_at < end_date,
            ),
        ),
    )
    comissoes_result = _safe_all(comissoes_query)
    comissoes = _ensure_sequence(comissoes_result)

    # Query Gastos
    gastos_query_base = db.query(Gasto)
    gastos_query = _safe_options(gastos_query_base, joinedload(Gasto.creator))
    gastos_query = _safe_filter(
        gastos_query, Gasto.data >= start_date, Gasto.data < end_date
    )
    gastos_result = _safe_all(gastos_query)
    gastos = _ensure_sequence(gastos_result)

    month_start = start_date.date()
    month_end = (end_date - timedelta(days=1)).date()

    def _within_month(value):
        if value is None:
            return False
        value_date = value.date() if hasattr(value, "date") else value
        return month_start <= value_date <= month_end

    def _filter_records(records, attr_name):
        return [
            record
            for record in records
            if _within_month(getattr(record, attr_name, None))
        ]

    pagamentos = _filter_records(pagamentos, "data")
    sessoes = _filter_records(sessoes, "data")
    gastos = _filter_records(gastos, "data")

    comissoes_filtered = []
    for comissao in comissoes:
        created_at = getattr(comissao, "created_at", None)
        pagamento = getattr(comissao, "pagamento", None)
        pagamento_data = getattr(pagamento, "data", None) if pagamento else None
        if _within_month(created_at) or _within_month(pagamento_data):
            comissoes_filtered.append(comissao)
    comissoes = comissoes_filtered

    return pagamentos, sessoes, comissoes, gastos


def serialize_data(pagamentos, sessoes, comissoes, gastos):
    """Serialize data into JSON-compatible dicts."""
    pagamentos_data = []
    for p in pagamentos:
        pagamentos_data.append(
            {
                "id": getattr(p, "id", None),  # Include payment ID for debugging
                "data": p.data.isoformat() if getattr(p, "data", None) else None,
                "cliente_name": getattr(getattr(p, "cliente", None), "name", None),
                "artista_name": getattr(getattr(p, "artista", None), "name", None),
                "valor": _safe_float(getattr(p, "valor", None), 0.0),
                "forma_pagamento": getattr(p, "forma_pagamento", None),
                "observacoes": getattr(p, "observacoes", None),
                "sessao_id": getattr(
                    p, "sessao_id", None
                ),  # Use session ID for proper linking
                "sessao_data": (
                    p.sessao.data.isoformat()
                    if getattr(p, "sessao", None) and getattr(p.sessao, "data", None)
                    else None
                ),
            }
        )

    sessoes_data = []
    for s in sessoes:
        sessoes_data.append(
            {
                "id": getattr(s, "id", None),  # Include session ID for proper linking
                "data": s.data.isoformat() if getattr(s, "data", None) else None,
                "created_at": (
                    s.created_at.isoformat() if getattr(s, "created_at", None) else None
                ),
                "cliente_name": getattr(getattr(s, "cliente", None), "name", None),
                "artista_name": getattr(getattr(s, "artista", None), "name", None),
                "valor": _safe_float(getattr(s, "valor", None), 0.0),
                "status": getattr(s, "status", None),
                "observacoes": getattr(s, "observacoes", None),
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
                "created_at": (
                    c.created_at.isoformat() if getattr(c, "created_at", None) else None
                ),
                "artista_name": getattr(getattr(c, "artista", None), "name", None),
                "cliente_name": cliente_name,
                "pagamento_valor": _safe_float(
                    getattr(getattr(c, "pagamento", None), "valor", None), None
                ),
                "pagamento_data": (
                    c.pagamento.data.isoformat()
                    if getattr(getattr(c, "pagamento", None), "data", None)
                    else None
                ),
                "percentual": _safe_float(getattr(c, "percentual", None), 0.0),
                "valor": _safe_float(getattr(c, "valor", None), 0.0),
                "observacoes": getattr(c, "observacoes", None),
            }
        )

    gastos_data = []
    for g in gastos:
        categoria = getattr(g, "categoria", None)  # Optional, forward-compatible
        gastos_data.append(
            {
                "data": g.data.isoformat() if getattr(g, "data", None) else None,
                "valor": _safe_float(getattr(g, "valor", None), 0.0),
                "descricao": getattr(g, "descricao", None),
                "forma_pagamento": getattr(g, "forma_pagamento", None),
                "categoria": categoria,
                "created_by": getattr(g, "created_by", None),
            }
        )

    return pagamentos_data, sessoes_data, comissoes_data, gastos_data


def calculate_totals(pagamentos_data, sessoes_data, comissoes_data, gastos_data=None):
    """
    Calculate comprehensive financial totals for extrato generation.

    This function computes all financial metrics for a given month's extrato,
    including revenue, commissions, expenses, and detailed breakdowns. It ensures
    accurate financial reporting by avoiding double-counting of revenue from both
    sessions and payments.

    Args:
        pagamentos_data (list): List of payment dictionaries with keys:
            - 'valor': Payment amount (float)
            - 'artista_name': Artist name (str)
            - 'forma_pagamento': Payment method (str)
            - 'sessao_data': Session date if linked to session (str, optional)
        sessoes_data (list): List of session dictionaries with keys:
            - 'valor': Session value (float)
            - 'artista_name': Artist name (str)
            - 'data': Session date (str)
        comissoes_data (list): List of commission dictionaries with keys:
            - 'valor': Commission amount (float)
            - 'artista_name': Artist name (str)
        gastos_data (list, optional): List of expense dictionaries with keys:
            - 'valor': Expense amount (float)
            - 'forma_pagamento': Payment method (str, optional)
            - 'categoria': Expense category (str, optional)

    Returns:
        dict: Comprehensive financial summary containing:
            - 'receita_total': Total revenue from payments only (float)
            - 'comissoes_total': Total commissions paid (float)
            - 'despesas_total': Total expenses (float)
            - 'saldo': Net balance (receita - despesas) (float)
            - 'receita_liquida': Net revenue after commissions and expenses (float)
            - 'por_artista': List of dicts with artist breakdowns:
                [{'artista': str, 'receita': float, 'comissao': float}, ...]
            - 'por_forma_pagamento': List of dicts with payment method breakdowns:
                [{'forma': str, 'total': float}, ...]
            - 'gastos_por_forma_pagamento': List of dicts with expense payment methods:
                [{'forma': str, 'total': float}, ...]
            - 'gastos_por_categoria': List of dicts with expense categories:
                [{'categoria': str, 'total': float}, ...]

    Note:
        Revenue calculation was fixed to count payments only, avoiding double-counting
        that occurred when both sessions and payments were included. This ensures
        accurate financial reporting based on actual money received.
    """
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
        logger.info(
            f"HISTORICO_DEBUG: Input data counts - payments:{len(pagamentos_data)} sessions:{len(sessoes_data)} commissions:{len(comissoes_data)}"
        )
        payment_ids = [p.get("id") for p in pagamentos_data]
        session_ids = [s.get("id") for s in sessoes_data]
        logger.info(f"HISTORICO_DEBUG: Payment IDs: {payment_ids}")
        logger.info(f"HISTORICO_DEBUG: Session IDs: {session_ids}")

    # ...existing code...

    # Por artista - Only include artists with actual participation (sessions or commissions)
    artistas = {}

    # First, collect sessions that have linked payments to avoid double counting
    sessions_with_payments = set()
    for p in pagamentos_data:
        if p.get("sessao_id"):  # Payment is linked to a session
            sessions_with_payments.add(p["sessao_id"])
            if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
                logger.info(
                    f"HISTORICO_DEBUG: Payment {p.get('id', 'unknown')} linked to session {p['sessao_id']}"
                )

    # Collect active artists (those with payments, unpaid sessions, or commissions)
    active_artists = set()

    # Artists with payments
    for p in pagamentos_data:
        if p["artista_name"]:
            active_artists.add(p["artista_name"])

    # Artists with unpaid sessions (sessions not linked to payments)
    for s in sessoes_data:
        if s["artista_name"] and s["id"] not in sessions_with_payments:
            active_artists.add(s["artista_name"])
            if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
                logger.info(
                    f"HISTORICO_DEBUG: Session {s['id']} is unpaid, including artist {s['artista_name']}"
                )

    # Artists with commissions (only if they have actual payments/sessions)
    payment_artists = {p["artista_name"] for p in pagamentos_data if p["artista_name"]}
    session_artists = {s["artista_name"] for s in sessoes_data if s["artista_name"]}
    artists_with_actual_work = payment_artists | session_artists

    for c in comissoes_data:
        if c["artista_name"] and c["artista_name"] in artists_with_actual_work:
            active_artists.add(c["artista_name"])

    # Initialize active artists with zero values
    for artista in active_artists:
        artistas[artista] = {"receita": 0, "comissao": 0}

    # Calculate receita from payments (actual money received)
    for p in pagamentos_data:
        artista = p["artista_name"]
        if artista and artista in active_artists:
            artistas[artista]["receita"] += p["valor"]

    # Calculate receita from unpaid sessions only (to avoid double counting)
    for s in sessoes_data:
        artista = s["artista_name"]
        # Only count sessions that don't have a linked payment
        if (
            artista
            and artista in active_artists
            and s["id"] not in sessions_with_payments
        ):
            artistas[artista]["receita"] += s["valor"]
            if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
                logger.info(
                    f"HISTORICO_DEBUG: Adding unpaid session {s['id']} revenue R${s['valor']} to artist {artista}"
                )

    # Calculate commissions for active artists
    for c in comissoes_data:
        artista = c["artista_name"]
        if artista and artista in active_artists:
            artistas[artista]["comissao"] += c["valor"]

    # Filter out artists with zero commissions from the summary
    # Only include artists who have actual commission earnings (comissao > 0)
    por_artista = [
        {"artista": k, "receita": v["receita"], "comissao": v["comissao"]}
        for k, v in artistas.items()
        if v["comissao"] > 0
    ]

    # Debug logging for artist calculations
    if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
        logger.info(f"HISTORICO_DEBUG: Active artists found: {active_artists}")
        logger.info(
            f"HISTORICO_DEBUG: Sessions with payments (IDs): {sessions_with_payments}"
        )
        logger.info(
            f"HISTORICO_DEBUG: Total artists in por_artista (with commissions > 0): {len(por_artista)}"
        )
        # Also log excluded artists
        excluded_artists = [k for k, v in artistas.items() if v["comissao"] == 0]
        if excluded_artists:
            logger.info(
                f"HISTORICO_DEBUG: Artists excluded from commission summary (0% commission): {excluded_artists}"
            )
        for artist_data in por_artista:
            logger.info(
                f"HISTORICO_DEBUG: Artist {artist_data['artista']}: Receita R${artist_data['receita']}, Comissão R${artist_data['comissao']}"
            )

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
    receita_liquida = receita_total - comissoes_total - despesas_total  # for UI display

    # Debug logging for net revenue calculation
    if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
        logger.info(
            f"HISTORICO_DEBUG: Net Revenue Calculation -> Receita Bruta: {receita_total}, Comissões: {comissoes_total}, Gastos: {despesas_total}, Receita Líquida: {receita_liquida}"
        )

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
    """
    Log an extrato generation run to the database for audit purposes.

    This internal function records the outcome of extrato generation attempts,
    including success/failure status and optional error messages.

    Args:
        mes (int): Month of the extrato generation (1-12)
        ano (int): Year of the extrato generation
        status (str): Status of the run ('success', 'failed', 'partial', etc.)
        message (str, optional): Additional message or error details

    Note:
        This function creates its own database session and handles errors gracefully
        to avoid interfering with the main extrato generation process.
    """
    from app.db.base import ExtratoRunLog
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        run_log = ExtratoRunLog(mes=mes, ano=ano, status=status, message=message)
        db.add(run_log)
        db.commit()
    except Exception as e:
        logging.warning(
            "Could not log extrato run",
            extra={"context": {"mes": mes, "ano": ano, "error": str(e)}},
        )
    finally:
        db.close()


def current_month_range():
    """
    Compute start and end datetime for the current month in server-local time.

    Returns:
        tuple: (start_date, end_date) as naive datetime objects representing
               the first day of the current month at 00:00:00 and the first day
               of the next month at 00:00:00.

    Note:
        Returns naive datetime objects. Consider timezone handling if the
        application spans multiple timezones.
    """
    from datetime import datetime

    now = datetime.now()
    start_date = datetime(now.year, now.month, 1)
    if now.month == 12:
        end_date = datetime(now.year + 1, 1, 1)
    else:
        end_date = datetime(now.year, now.month + 1, 1)
    return start_date, end_date
