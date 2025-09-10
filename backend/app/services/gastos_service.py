"""Gastos service utilities.

Provides a reusable query to fetch expenses (Gasto) within a date window and
optional serializers for frontend-facing payloads.
"""

from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.db.base import Gasto


def get_gastos_for_month(
    db: Session, start_date: datetime, end_date: datetime
) -> List[Gasto]:
    """Return all Gasto records within [start_date, end_date) ordered by date.

    - Includes joinedload for the creator relationship for convenience.
    - The function is intentionally generic and reusable by controllers/services.
    """
    return (
        db.query(Gasto)
        .options(joinedload(Gasto.creator))
        .filter(Gasto.data >= start_date, Gasto.data < end_date)
        .order_by(Gasto.data.asc())
        .all()
    )


def serialize_gasto(g: Gasto) -> Dict[str, Any]:
    """Serialize a single Gasto to a JSON-compatible dict.

    Note: categoria is optional and may not exist on the model; we use getattr
    for forward-compatibility.
    """
    valor = getattr(g, "valor", None)
    try:
        valor_float = float(valor) if valor is not None else None
    except Exception:
        valor_float = None

    return {
        "id": getattr(g, "id", None),
        "data": g.data.isoformat() if getattr(g, "data", None) else None,
        "valor": valor_float,
        "descricao": getattr(g, "descricao", None),
        "forma_pagamento": getattr(g, "forma_pagamento", None),
        "categoria": getattr(g, "categoria", None),
        "created_by": getattr(g, "created_by", None),
        "created_by_name": (
            getattr(g.creator, "name", None) if getattr(g, "creator", None) else None
        ),
    }


def serialize_gastos(gastos: List[Gasto]) -> List[Dict[str, Any]]:
    """Serialize a list of Gasto objects."""
    return [serialize_gasto(g) for g in gastos]
