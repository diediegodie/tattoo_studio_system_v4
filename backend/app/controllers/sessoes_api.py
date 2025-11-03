"""
API endpoints for sessoes module.
Handles JSON API operations for sessions.
"""

import logging
from datetime import date
from decimal import Decimal

from app.controllers.sessoes_helpers import api_response
from app.db.base import Sessao
from app.db.session import SessionLocal
from flask import request
from flask_login import login_required
from sqlalchemy.orm import joinedload
from app.core.csrf_config import csrf
from app.core.limiter_config import limiter
from app.core.auth_decorators import require_session_authorization

logger = logging.getLogger(__name__)

# Import the blueprint from sessoes_controller instead of creating a new one
from app.controllers.sessoes_controller import sessoes_bp  # noqa: E402


@sessoes_bp.route("/api", methods=["GET"])
@limiter.limit("100 per minute")
@csrf.exempt  # JSON API - uses session authentication
@login_required
def api_list_sessoes():
    """Return JSON array of sessions."""
    db = None
    try:
        db = SessionLocal()

        sessoes = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .order_by(Sessao.data.asc(), Sessao.created_at.asc())
            .all()
        )

        def to_dict(s):
            return {
                "id": s.id,
                "data": s.data.isoformat() if s.data else None,
                "cliente": (
                    {"id": s.cliente.id, "name": s.cliente.name} if s.cliente else None
                ),
                "artista": (
                    {"id": s.artista.id, "name": s.artista.name} if s.artista else None
                ),
                "valor": float(s.valor) if s.valor is not None else None,
                "observacoes": s.observacoes,
                "google_event_id": s.google_event_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }

        return api_response(
            True, "Sessões recuperadas com sucesso", [to_dict(s) for s in sessoes]
        )
    except Exception as e:
        logger.error(f"Error in api_list_sessoes: {str(e)}")
        return api_response(False, "Erro interno do servidor", None, 500)
    finally:
        if db:
            db.close()


@sessoes_bp.route("/api/<int:sessao_id>", methods=["GET"])
@limiter.limit("100 per minute")
@csrf.exempt  # JSON API - uses session authentication
@login_required
def api_get_sessao(sessao_id: int):
    db = None
    try:
        db = SessionLocal()
        s = db.get(Sessao, sessao_id)
        if not s:
            return api_response(False, "Sessão não encontrada", None, 404)

        data = {
            "id": s.id,
            "data": s.data.isoformat() if s.data else None,
            "cliente": (
                {"id": s.cliente.id, "name": s.cliente.name} if s.cliente else None
            ),
            "artista": (
                {"id": s.artista.id, "name": s.artista.name} if s.artista else None
            ),
            "valor": float(s.valor) if s.valor is not None else None,
            "observacoes": s.observacoes,
            "google_event_id": s.google_event_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        return api_response(True, "Sessão encontrada", data, 200)
    except Exception as e:
        logger.error(f"Error in api_get_sessao: {str(e)}")
        return api_response(False, f"Erro: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@csrf.exempt
@limiter.limit("30 per minute")
@sessoes_bp.route("/api/<int:sessao_id>", methods=["PUT"])
@require_session_authorization
def api_update_sessao(sessao_id: int):
    db = None
    try:
        db = SessionLocal()
        if not request.is_json:
            return api_response(False, "Expected JSON payload", None, 400)
        payload = request.get_json()

        s = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .get(sessao_id)
        )
        if not s:
            return api_response(False, "Sessão não encontrada", None, 404)

        # Server-side validation: ensure required fields are present
        required_fields = ["data", "cliente_id", "artista_id", "valor"]
        for field in required_fields:
            if (
                field not in payload
                or payload.get(field) is None
                or str(payload.get(field)).strip() == ""
            ):
                return api_response(False, f"Campo {field} é obrigatório", None, 400)

        # Update fields if provided
        try:
            if "data" in payload and payload["data"]:
                # Expect YYYY-MM-DD
                s.data = (
                    date.fromisoformat(payload["data"])
                    if isinstance(payload["data"], str)
                    else payload["data"]
                )
            if "cliente_id" in payload and payload["cliente_id"]:
                s.cliente_id = int(payload["cliente_id"])
            if "artista_id" in payload and payload["artista_id"]:
                s.artista_id = int(payload["artista_id"])
            if "valor" in payload and payload["valor"] is not None:
                s.valor = Decimal(str(payload["valor"]))
            if "observacoes" in payload:
                s.observacoes = payload.get("observacoes")

            db.add(s)
            db.commit()
            db.refresh(s)
        except Exception as e:
            db.rollback()
            return api_response(False, f"Falha na atualização: {str(e)}", None, 400)

        data = {
            "id": s.id,
            "data": s.data.isoformat() if s.data else None,
            "cliente": (
                {"id": s.cliente.id, "name": s.cliente.name} if s.cliente else None
            ),
            "artista": (
                {"id": s.artista.id, "name": s.artista.name} if s.artista else None
            ),
            "valor": float(s.valor) if s.valor is not None else None,
            "observacoes": s.observacoes,
            "google_event_id": s.google_event_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        return api_response(True, "Sessão atualizada com sucesso", data, 200)
    finally:
        if db:
            db.close()


@csrf.exempt
@limiter.limit("30 per minute")
@sessoes_bp.route("/api/<int:sessao_id>", methods=["DELETE"])
@require_session_authorization
def api_delete_sessao(sessao_id: int):
    db = None
    try:
        db = SessionLocal()

        s = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .get(sessao_id)
        )
        if not s:
            return api_response(False, "Sessão não encontrada", None, 404)

        try:
            db.delete(s)
            db.commit()
        except Exception:
            db.rollback()
            return api_response(False, "Falha ao excluir sessão", None, 400)

        return api_response(True, "Sessão excluída", None, 200)
    finally:
        if db:
            db.close()
