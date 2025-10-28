"""
API endpoints for financeiro module.
Handles JSON API operations for payments.
"""

import logging
from datetime import datetime

from app.core.api_utils import api_response
from app.db.base import Pagamento
from app.db.session import SessionLocal
from app.repositories.pagamento_repository import PagamentoRepository
from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy.orm import joinedload
from app.core.csrf_config import csrf
from app.core.limiter_config import limiter

logger = logging.getLogger(__name__)

# Import the blueprint from financeiro_controller instead of creating a new one
from app.controllers.financeiro_controller import financeiro_bp  # noqa: E402


@financeiro_bp.route("/api", methods=["GET"])
@limiter.limit("100 per minute")
@login_required
def api_list_pagamentos():
    """Return JSON array of payments."""
    db = None
    try:
        db = SessionLocal()

        pagamentos = (
            db.query(Pagamento)
            .options(joinedload(Pagamento.cliente), joinedload(Pagamento.artista))
            .order_by(Pagamento.data.desc())  # Most recent first
            .all()
        )

        def to_dict(p):
            return {
                "id": p.id,
                "data": (
                    p.data.isoformat()
                    if hasattr(p, "data") and getattr(p, "data", None)
                    else None
                ),
                "valor": (
                    float(getattr(p, "valor"))
                    if getattr(p, "valor", None) is not None
                    else None
                ),
                "forma_pagamento": p.forma_pagamento,
                "cliente": (
                    {"id": p.cliente.id, "name": p.cliente.name}
                    if hasattr(p, "cliente") and p.cliente
                    else None
                ),
                "artista": (
                    {"id": p.artista.id, "name": p.artista.name}
                    if hasattr(p, "artista") and p.artista
                    else None
                ),
                "observacoes": getattr(p, "observacoes", None),
                "created_at": (
                    p.created_at.isoformat()
                    if hasattr(p, "created_at") and getattr(p, "created_at", None)
                    else None
                ),
            }

        return api_response(
            True,
            "Pagamentos recuperados com sucesso",
            [to_dict(p) for p in pagamentos],
            200,
        )
    except Exception as e:
        logger.error(f"Error in api_list_pagamentos: {str(e)}")
        return api_response(False, "Erro interno do servidor", None, 500)
    finally:
        if db:
            db.close()


@financeiro_bp.route("/api/<int:pagamento_id>", methods=["GET"])
@limiter.limit("100 per minute")
@login_required
def api_get_pagamento(pagamento_id: int):
    """Get a single payment by ID."""
    db = None
    try:
        db = SessionLocal()
        p = (
            db.query(Pagamento)
            .options(joinedload(Pagamento.cliente), joinedload(Pagamento.artista))
            .get(pagamento_id)
        )

        if not p:
            return api_response(False, "Pagamento não encontrado", None, 404)

        data = {
            "id": p.id,
            "data": (
                p.data.isoformat()
                if hasattr(p, "data") and getattr(p, "data", None)
                else None
            ),
            "valor": (
                float(getattr(p, "valor"))
                if getattr(p, "valor", None) is not None
                else None
            ),
            "forma_pagamento": p.forma_pagamento,
            "cliente": (
                {"id": p.cliente.id, "name": p.cliente.name}
                if hasattr(p, "cliente") and p.cliente
                else None
            ),
            "artista": (
                {"id": p.artista.id, "name": p.artista.name}
                if hasattr(p, "artista") and p.artista
                else None
            ),
            "observacoes": getattr(p, "observacoes", None),
            "created_at": (
                p.created_at.isoformat()
                if hasattr(p, "created_at") and getattr(p, "created_at", None)
                else None
            ),
        }

        return api_response(True, "Pagamento encontrado", data, 200)
    except Exception as e:
        logger.error(f"Error in api_get_pagamento: {str(e)}")
        return api_response(False, f"Erro: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@csrf.exempt
@limiter.limit("30 per minute")
@financeiro_bp.route("/api/<int:pagamento_id>", methods=["PUT"])
@login_required
def api_update_pagamento(pagamento_id: int):
    """Update a pagamento by ID via JSON payload."""
    db = None
    try:
        db = SessionLocal()
        repo = PagamentoRepository(db)
        existing = repo.get_by_id(pagamento_id)
        if not existing:
            return api_response(False, "Pagamento não encontrado", None, 404)

        payload = request.get_json(force=True, silent=True) or {}

        # Server-side validation: forma_pagamento must be present and non-empty for PUT updates
        if (
            "forma_pagamento" not in payload
            or payload.get("forma_pagamento") is None
            or str(payload.get("forma_pagamento")).strip() == ""
        ):
            return api_response(False, "Forma de pagamento obrigatória", None, 400)

        # Normalize and convert fields we expect
        data_updates = {}
        if "data" in payload and payload.get("data"):
            try:
                data_str = payload.get("data")
                if data_str:
                    data_updates["data"] = datetime.fromisoformat(data_str).date()
            except Exception:
                # if cannot parse, ignore and let repository handle validation
                pass

        for key in (
            "valor",
            "forma_pagamento",
            "cliente_id",
            "artista_id",
            "observacoes",
        ):
            if key in payload:
                data_updates[key] = payload.get(key)

        updated = repo.update(pagamento_id, data_updates)
        if not updated:
            return api_response(False, "Falha ao atualizar pagamento", None, 500)

        # Build response payload similar to api_get_pagamento
        data = {
            "id": updated.id,
            "data": (
                updated.data.isoformat()
                if hasattr(updated, "data") and getattr(updated, "data", None)
                else None
            ),
            "valor": (
                float(getattr(updated, "valor"))
                if getattr(updated, "valor", None) is not None
                else None
            ),
            "forma_pagamento": updated.forma_pagamento,
            "cliente": (
                {"id": updated.cliente.id, "name": updated.cliente.name}
                if hasattr(updated, "cliente") and updated.cliente
                else None
            ),
            "artista": (
                {"id": updated.artista.id, "name": updated.artista.name}
                if hasattr(updated, "artista") and updated.artista
                else None
            ),
            "observacoes": getattr(updated, "observacoes", None),
            "created_at": (
                updated.created_at.isoformat()
                if hasattr(updated, "created_at") and updated.created_at is not None
                else None
            ),
        }

        return api_response(True, "Pagamento atualizado", data, 200)
    except Exception as e:
        logger.exception("Error updating pagamento: %s", e)
        if db:
            db.rollback()
        return api_response(False, f"Erro interno: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@csrf.exempt
@limiter.limit("30 per minute")
@financeiro_bp.route("/api/<int:pagamento_id>", methods=["DELETE"])
@login_required
def api_delete_pagamento(pagamento_id: int):
    """Delete a pagamento by ID."""
    db = None
    try:
        db = SessionLocal()
        repo = PagamentoRepository(db)
        existing = repo.get_by_id(pagamento_id)
        if not existing:
            return api_response(False, "Pagamento não encontrado", None, 404)

        ok = repo.delete(pagamento_id)
        if not ok:
            return api_response(False, "Falha ao excluir pagamento", None, 500)

        return api_response(True, "Pagamento excluído", None, 200)
    except Exception as e:
        logger.exception("Error deleting pagamento: %s", e)
        if db:
            db.rollback()
        return api_response(False, f"Erro interno: {str(e)}", None, 500)
    finally:
        if db:
            db.close()
