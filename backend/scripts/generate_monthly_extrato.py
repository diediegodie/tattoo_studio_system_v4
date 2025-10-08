"""
Script to generate monthly extrato (snapshot) for the tattoo studio system.

This script:
- Queries data from the previous month (or specified --mes --ano).
- Serializes essential data into JSON.
- Calculates totals (revenue, commissions, by artist, by payment method).
- Inserts a new Extrato record.
- Deletes the original records from Pagamento, Sessao, and Comissao for that month.
- Ensures immutability and uniqueness per month/year.

Usage:
- Run manually: python generate_monthly_extrato.py [--mes MM] [--ano YYYY] [--force]
- If no args, uses previous month.
- Scheduled via CRON: 0 1 1 * * /path/to/script.sh

Requirements:
- Run inside the app container or with correct PYTHONPATH.
- Database must be accessible.
"""

import argparse
import json
import logging
from datetime import datetime, timedelta

from app.core.logging_config import get_logger
from app.db.base import Client, Comissao, Extrato, Gasto, Pagamento, Sessao, User
from app.db.session import SessionLocal
from sqlalchemy.orm import joinedload

logger = get_logger(__name__)


def get_previous_month():
    """Get the previous month and year."""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    return last_day_prev_month.month, last_day_prev_month.year


def check_existing_extrato(db, mes, ano, force):
    """Check if extrato already exists for the month/year."""
    existing = db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
    if existing:
        if not force:
            logger.error(
                "Extrato already exists",
                extra={"context": {"mes": mes, "ano": ano, "action": "abort"}},
            )
            return False
        else:
            logger.warning(
                "Overwriting existing extrato",
                extra={"context": {"mes": mes, "ano": ano}},
            )
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

    # Query Comissoes with joins - filter by pagamento date, not created_at
    comissoes = (
        db.query(Comissao)
        .join(Pagamento, Comissao.pagamento_id == Pagamento.id)
        .options(
            joinedload(Comissao.artista),
            joinedload(Comissao.pagamento).joinedload(Pagamento.cliente),
            joinedload(Comissao.pagamento).joinedload(Pagamento.sessao),
        )
        .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
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
        categoria = getattr(g, "categoria", None)
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
    receita_total = sum(p["valor"] for p in pagamentos_data)
    comissoes_total = sum(c["valor"] for c in comissoes_data)
    gastos_data = gastos_data or []
    despesas_total = sum(g["valor"] for g in gastos_data)

    # Por artista - FIXED: Include artists with commissions even if they have no payments
    artistas = {}
    for p in pagamentos_data:
        artista = p["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
            artistas[artista]["receita"] += p["valor"]

    for c in comissoes_data:
        artista = c["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
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

    # Gastos por categoria
    gastos_por_categoria_map = {}
    for g in gastos_data:
        categoria = g.get("categoria") or "Outros"
        gastos_por_categoria_map[categoria] = (
            gastos_por_categoria_map.get(categoria, 0) + g["valor"]
        )
    gastos_por_categoria = [
        {"categoria": k, "total": v} for k, v in gastos_por_categoria_map.items()
    ]

    saldo = receita_total - despesas_total

    return {
        "receita_total": receita_total,
        "comissoes_total": comissoes_total,
        "despesas_total": despesas_total,
        "saldo": saldo,
        "por_artista": por_artista,
        "por_forma_pagamento": por_forma_pagamento,
        "gastos_por_forma_pagamento": gastos_por_forma_pagamento,
        "gastos_por_categoria": gastos_por_categoria,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate monthly extrato snapshot.")
    parser.add_argument("--mes", type=int, help="Month (1-12)")
    parser.add_argument("--ano", type=int, help="Year (e.g., 2025)")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing extrato"
    )
    args = parser.parse_args()

    if args.mes and args.ano:
        mes, ano = args.mes, args.ano
    else:
        mes, ano = get_previous_month()

    logger.info("Generating extrato", extra={"context": {"mes": mes, "ano": ano}})

    db = SessionLocal()
    try:
        # Check existing
        if not check_existing_extrato(db, mes, ano, args.force):
            return

        # Query data
        pagamentos, sessoes, comissoes, gastos = query_data(db, mes, ano)
        logger.info(
            "Data queried",
            extra={
                "context": {
                    "pagamentos": len(pagamentos),
                    "sessoes": len(sessoes),
                    "comissoes": len(comissoes),
                    "gastos": len(gastos),
                }
            },
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
            totais=json.dumps(totais),
            gastos=json.dumps(gastos_data),
        )
        db.add(extrato)
        db.commit()

        logger.info(
            "Extrato created successfully", extra={"context": {"mes": mes, "ano": ano}}
        )

        # Delete original records in dependency order, breaking circular references
        for c in comissoes:
            db.delete(c)
        # Break circular reference between Sessao and Pagamento
        for s in sessoes:
            s.payment_id = None
        db.commit()
        for p in pagamentos:
            db.delete(p)
        for s in sessoes:
            db.delete(s)
        for g in gastos:
            db.delete(g)
        db.commit()

        logger.info(
            "Original records deleted",
            extra={
                "context": {
                    "pagamentos": len(pagamentos),
                    "sessoes": len(sessoes),
                    "comissoes": len(comissoes),
                    "gastos": len(gastos),
                }
            },
        )

    except Exception as e:
        db.rollback()
        logger.error(
            "Extrato generation failed",
            extra={"context": {"error": str(e), "mes": mes, "ano": ano}},
            exc_info=True,
        )
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
