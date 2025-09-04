"""
Service for managing extrato generation and retrieval.
Reuses logic from generate_monthly_extrato.py for modularity.
"""

import json
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from ..db.session import SessionLocal
from ..db.base import Pagamento, Sessao, Comissao, Extrato, Client, User


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
    """Query Pagamento, Sessao, Comissao for the month/year."""
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

    return pagamentos, sessoes, comissoes


def serialize_data(pagamentos, sessoes, comissoes):
    """Serialize data into JSON-compatible dicts."""
    pagamentos_data = []
    for p in pagamentos:
        pagamentos_data.append(
            {
                "data": p.data.isoformat() if p.data else None,
                "hora": p.hora.isoformat() if p.hora else None,
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

    return pagamentos_data, sessoes_data, comissoes_data


def calculate_totals(pagamentos_data, sessoes_data, comissoes_data):
    """Calculate totals."""
    receita_total = sum(p["valor"] for p in pagamentos_data)
    comissoes_total = sum(c["valor"] for c in comissoes_data)

    # Por artista
    artistas = {}
    for p in pagamentos_data:
        artista = p["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
            artistas[artista]["receita"] += p["valor"]

    for c in comissoes_data:
        artista = c["artista_name"]
        if artista and artista in artistas:
            artistas[artista]["comissao"] += c["valor"]

    por_artista = [
        {"artista": k, "receita": v["receita"], "comissao": v["comissao"]}
        for k, v in artistas.items()
    ]

    # Por forma de pagamento
    formas = {}
    for p in pagamentos_data:
        forma = p["forma_pagamento"]
        if forma:
            formas[forma] = formas.get(forma, 0) + p["valor"]

    por_forma_pagamento = [{"forma": k, "total": v} for k, v in formas.items()]

    return {
        "receita_total": receita_total,
        "comissoes_total": comissoes_total,
        "por_artista": por_artista,
        "por_forma_pagamento": por_forma_pagamento,
    }


def generate_extrato(mes, ano, force=False):
    """Generate extrato for the given month/year if it doesn't exist."""
    db = SessionLocal()
    try:
        if not check_existing_extrato(db, mes, ano, force):
            return

        # Query data
        pagamentos, sessoes, comissoes = query_data(db, mes, ano)
        print(
            f"Generating extrato for {mes}/{ano}: {len(pagamentos)} pagamentos, {len(sessoes)} sessoes, {len(comissoes)} comissoes."
        )

        # Serialize
        pagamentos_data, sessoes_data, comissoes_data = serialize_data(
            pagamentos, sessoes, comissoes
        )

        # Calculate totals
        totais = calculate_totals(pagamentos_data, sessoes_data, comissoes_data)

        # Create extrato
        extrato = Extrato(
            mes=mes,
            ano=ano,
            pagamentos=json.dumps(pagamentos_data),
            sessoes=json.dumps(sessoes_data),
            comissoes=json.dumps(comissoes_data),
            totais=json.dumps(totais),
        )
        db.add(extrato)
        db.commit()

        print("Extrato created successfully.")

        # Delete original records
        for p in pagamentos:
            db.delete(p)
        for s in sessoes:
            db.delete(s)
        for c in comissoes:
            db.delete(c)
        db.commit()

        print(
            f"Deleted {len(pagamentos)} pagamentos, {len(sessoes)} sessoes, {len(comissoes)} comissoes."
        )

    except Exception as e:
        db.rollback()
        print(f"ERROR generating extrato: {str(e)}")
        raise
    finally:
        db.close()


def check_and_generate_extrato(mes=None, ano=None):
    """Check and generate extrato for the given or previous month."""
    if mes is None or ano is None:
        mes, ano = get_previous_month()
    generate_extrato(mes, ano, force=False)
