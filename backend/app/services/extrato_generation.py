"""
Extrato Generation Service - Main generation functions.

This module contains the core extrato generation logic, separated from
the main service for better maintainability.
"""

import json
import logging
from datetime import datetime

from app.db.base import Comissao, Extrato, Gasto, Pagamento, Sessao
from app.db.session import SessionLocal
from app.services.extrato_core import (
    _log_extrato_run,
    calculate_totals,
    check_existing_extrato,
    query_data,
    serialize_data,
)
from sqlalchemy.orm import joinedload

# Configure logging
logger = logging.getLogger(__name__)


def generate_extrato(mes, ano, force=False):
    """Generate extrato for the given month/year if it doesn't exist."""
    import logging

    logger = logging.getLogger(__name__)

    db = SessionLocal()
    try:
        if not check_existing_extrato(db, mes, ano, force):
            return

        # Query data
        pagamentos, sessoes, comissoes, gastos = query_data(db, mes, ano)
        logger.info(
            f"Generating extrato for {mes}/{ano}: {len(pagamentos)} pagamentos, {len(sessoes)} sessoes, {len(comissoes)} comissoes, {len(gastos)} gastos."
        )

        # Serialize
        pagamentos_data, sessoes_data, comissoes_data, gastos_data = serialize_data(
            pagamentos, sessoes, comissoes, gastos
        )

        # Calculate totals
        totais = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Create extrato
        extrato = Extrato(
            mes=mes,
            ano=ano,
            pagamentos=json.dumps(pagamentos_data),
            sessoes=json.dumps(sessoes_data),
            comissoes=json.dumps(comissoes_data),
            gastos=json.dumps(gastos_data),
            totais=json.dumps(totais),
        )
        db.add(extrato)

        logger.info("Extrato created successfully.")

        # Delete original records in dependency order, breaking circular references
        for c in comissoes:
            db.delete(c)
        # Break circular reference between Sessao and Pagamento on both sides
        for p in pagamentos:
            try:
                setattr(p, "sessao_id", None)
            except Exception:
                pass
        for s in sessoes:
            try:
                setattr(s, "payment_id", None)
            except Exception:
                pass
        db.commit()
        # Now safely delete
        for p in pagamentos:
            db.delete(p)
        for s in sessoes:
            db.delete(s)
        for g in gastos:
            db.delete(g)
        db.commit()

        logger.info(
            f"Deleted {len(pagamentos)} pagamentos, {len(sessoes)} sessoes, {len(comissoes)} comissoes, {len(gastos)} gastos."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"ERROR generating extrato: {str(e)}")
        raise
    finally:
        db.close()


def get_current_month_totals(db):
    """Calculate totals for the current month from the database, including gastos.

    Uses centralized current_month_range() and query_data() to ensure all entities
    are filtered by the same date window.
    """
    import os

    from app.services.extrato_core import (
        calculate_totals,
        current_month_range,
        serialize_data,
    )

    start_date, end_date = current_month_range()

    # Debug logging if enabled
    if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
        logger.info(
            f"HISTORICO_DEBUG: Current month window: {start_date} to {end_date}"
        )

    # Build from Pagamento as source of truth within [start_date, end_date)
    pagamentos = (
        db.query(Pagamento)
        .options(
            joinedload(Pagamento.cliente),
            joinedload(Pagamento.artista),
            joinedload(Pagamento.sessao),
            joinedload(Pagamento.comissoes),
        )
        .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
        .order_by(Pagamento.data.desc())
        .all()
    )

    # Some unit tests may monkeypatch query return values; ensure we have a concrete list
    def _safe_list(value):
        try:
            return list(value)
        except Exception:
            return []

    pagamentos = pagamentos if isinstance(pagamentos, list) else _safe_list(pagamentos)
    # Derive sessions strictly via Sessao.payment_id to avoid missing links
    try:
        payment_ids = [p.id for p in pagamentos]
        sessoes = (
            (
                db.query(Sessao)
                .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
                .filter(Sessao.payment_id.in_(payment_ids))
                .all()
            )
            if payment_ids
            else []
        )
    except Exception:
        # Fallback to relationship on Pagamento if direct query fails (best-effort)
        pagamentos_fallback = (
            pagamentos if isinstance(pagamentos, list) else _safe_list(pagamentos)
        )
        try:
            sessoes = [
                p.sessao for p in pagamentos_fallback if getattr(p, "sessao", None)
            ]
        except Exception:
            sessoes = []
    comissoes = []
    for p in pagamentos:
        pcs = getattr(p, "comissoes", [])
        if pcs:
            comissoes.extend(list(pcs))
    # Gastos remain independent by their own date field
    gastos = (
        db.query(Gasto)
        .options(joinedload(Gasto.creator))
        .filter(Gasto.data >= start_date, Gasto.data < end_date)
        .all()
    )

    # Debug counts
    if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
        logger.info(
            f"HISTORICO_DEBUG: Queried counts - pagamentos:{len(pagamentos)} sessoes:{len(sessoes)} comissoes:{len(comissoes)} gastos:{len(gastos)}"
        )

    # Serialize for calculation
    pagamentos_data, sessoes_data, comissoes_data, gastos_data = serialize_data(
        pagamentos, sessoes, comissoes, gastos
    )

    # Calculate totals (now includes receita_liquida)
    totals = calculate_totals(
        pagamentos_data, sessoes_data, comissoes_data, gastos_data
    )

    # Debug final totals
    if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
        logger.info(
            f"HISTORICO_DEBUG: Final totals - receita_total:{totals['receita_total']} comissoes_total:{totals['comissoes_total']} despesas_total:{totals['despesas_total']} receita_liquida:{totals['receita_liquida']}"
        )

    return totals


def check_and_generate_extrato(mes=None, ano=None, force=False):
    """Check and generate extrato for the given or previous month.

    Enhanced version with production-ready logic and database logging.
    """
    import logging

    from app.services.extrato_core import get_previous_month, should_run_monthly_extrato

    logger = logging.getLogger(__name__)

    try:
        # If specific month/year provided, use those
        if mes is not None and ano is not None:
            logger.info(f"Generating extrato for specific month: {mes}/{ano}")
            generate_extrato(mes, ano, force=force)
            # Log successful run
            _log_extrato_run(mes, ano, "success", "Manual generation completed")
            return

        # Check if we should run the monthly automation
        if not force and not should_run_monthly_extrato():
            logger.info(
                "Monthly extrato generation skipped - already ran this month or too early in month"
            )
            return

        # Get previous month and generate
        mes, ano = get_previous_month()
        logger.info(f"Running monthly extrato generation for {mes}/{ano}")
        generate_extrato(mes, ano, force=force)

        # Log successful run
        _log_extrato_run(mes, ano, "success", "Monthly automation completed")

    except Exception as e:
        # Log failed run
        if mes is not None and ano is not None:
            _log_extrato_run(mes, ano, "error", str(e))
        logger.error(f"Error in check_and_generate_extrato: {str(e)}")
        raise
