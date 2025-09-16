"""
Extrato Generation Service - Main generation functions.

This module contains the core extrato generation logic, separated from
the main service for better maintainability.
"""

import json
import logging
from datetime import datetime
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.base import (
    Pagamento,
    Sessao,
    Comissao,
    Extrato,
    Gasto,
)
from app.services.extrato_core import (
    check_existing_extrato,
    query_data,
    serialize_data,
    calculate_totals,
    _log_extrato_run,
)

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
        # Break circular reference between Sessao and Pagamento
        for s in sessoes:
            setattr(s, "payment_id", None)
        db.commit()
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
    """Calculate totals for the current month from the database, including gastos."""
    from datetime import datetime
    from sqlalchemy import func

    today = datetime.now()
    start_date = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_date = datetime(today.year + 1, 1, 1)
    else:
        end_date = datetime(today.year, today.month + 1, 1)

    # Get pagamentos
    pagamentos = (
        db.query(Pagamento)
        .options(joinedload(Pagamento.artista))
        .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
        .all()
    )

    # Get comissoes
    comissoes = (
        db.query(Comissao)
        .options(joinedload(Comissao.artista))
        .filter(Comissao.created_at >= start_date, Comissao.created_at < end_date)
        .all()
    )

    # Get gastos
    gastos = (
        db.query(Gasto).filter(Gasto.data >= start_date, Gasto.data < end_date).all()
    )

    # Serialize for calculation
    pagamentos_data = [
        {
            "valor": float(p.valor),
            "artista_name": p.artista.name if p.artista else None,
            "forma_pagamento": p.forma_pagamento,
        }
        for p in pagamentos
    ]

    comissoes_data = [
        {
            "valor": float(c.valor),
            "artista_name": c.artista.name if c.artista else None,
        }
        for c in comissoes
    ]

    gastos_data = [
        {
            "valor": float(g.valor),
            "forma_pagamento": g.forma_pagamento,
            "categoria": getattr(g, "categoria", None),
        }
        for g in gastos
    ]

    # Use existing calculate_totals function
    return calculate_totals(pagamentos_data, [], comissoes_data, gastos_data)


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
