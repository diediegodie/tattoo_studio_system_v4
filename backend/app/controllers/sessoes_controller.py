"""
Sessions Controller - SOLID-compliant HTTP route handlers for session operations.

Following SOLID principles:
- Single Responsibility: Only handles HTTP request/response for session operations
- Dependency Inversion: Uses services instead of direct database access
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from werkzeug.wrappers.response import Response
from flask_login import login_required
from typing import Union
import logging

from services.user_service import UserService
from repositories.user_repo import UserRepository
from db.session import SessionLocal
from db.base import Client, Sessao
from decimal import Decimal
from datetime import datetime, date, time

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
sessoes_bp = Blueprint("sessoes", __name__, url_prefix="/sessoes")


def api_response(
    success: bool, message: str, data: dict = None, status_code: int = 200
):
    """Consistent JSON API response used across controllers."""
    return jsonify({"success": success, "message": message, "data": data}), status_code


def _get_user_service() -> UserService:
    """Dependency injection factory for UserService."""
    db_session = SessionLocal()
    user_repo = UserRepository(db_session)
    return UserService(user_repo)


@sessoes_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_sessao() -> Union[str, Response]:
    """Create a new session/appointment."""
    db = None
    try:
        db = SessionLocal()

        if request.method == "GET":
            # Render form with clients from clients table (actual client data)
            from db.base import Client

            clients = db.query(Client).order_by(Client.name).all()

            # Use service to get artists following SOLID principles
            user_service = _get_user_service()
            artists = user_service.list_artists()

            return render_template("nova_sessao.html", clients=clients, artists=artists)

        elif request.method == "POST":
            # Process form submission
            data = request.form.get("data")
            hora = request.form.get("hora")
            cliente_id = request.form.get("cliente_id")
            artista_id = request.form.get("artista_id")
            valor = request.form.get("valor")
            observacoes = request.form.get("observacoes")

            # Validate required fields
            if not all([data, hora, cliente_id, artista_id, valor]):
                flash("Todos os campos obrigatórios devem ser preenchidos.", "error")
                return redirect(url_for("sessoes.nova_sessao"))

            # Create session
            sessao = Sessao(
                data=data,
                hora=hora,
                valor=valor,
                observacoes=observacoes,
                cliente_id=cliente_id,
                artista_id=artista_id,
            )

            db.add(sessao)
            db.commit()

            flash("Sessão criada com sucesso!", "success")
            return redirect(url_for("sessoes.list_sessoes"))

    except Exception as e:
        logger.error(f"Error in nova_sessao: {str(e)}")
        flash("Erro interno do servidor.", "error")
        return redirect(url_for("sessoes.nova_sessao"))
    finally:
        if db:
            db.close()

    # This should never be reached, but for type safety
    return redirect(url_for("sessoes.nova_sessao"))


@sessoes_bp.route("/list")
@login_required
def list_sessoes() -> str:
    """List all sessions."""
    db = None
    try:
        db = SessionLocal()
        # Load sessions with their relationships (cliente and artista)
        from sqlalchemy.orm import joinedload

        sessoes = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .all()
        )

        # Also provide clients and artists (same pattern as nova_sessao) so
        # templates can render user-friendly select options for edit modals.
        from db.base import Client

        clients = db.query(Client).order_by(Client.name).all()

        user_service = _get_user_service()
        artists = user_service.list_artists()

        return render_template(
            "sessoes.html", sessoes=sessoes, clients=clients, artists=artists
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        flash("Erro ao carregar sessões.", "error")
        return render_template("sessoes.html", sessoes=[])
    finally:
        if db:
            db.close()


# -------------------------
# REST API endpoints for sessoes
# -------------------------


@sessoes_bp.route("/api", methods=["GET"])
@login_required
def api_list_sessoes():
    """Return JSON array of sessions."""
    db = None
    try:
        db = SessionLocal()
        from sqlalchemy.orm import joinedload

        sessoes = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .all()
        )

        def to_dict(s):
            return {
                "id": s.id,
                "data": s.data.isoformat() if s.data else None,
                "hora": s.hora.strftime("%H:%M:%S") if s.hora else None,
                "cliente": (
                    {"id": s.cliente.id, "name": s.cliente.name} if s.cliente else None
                ),
                "artista": (
                    {"id": s.artista.id, "name": s.artista.name} if s.artista else None
                ),
                "valor": float(s.valor) if s.valor is not None else None,
                "observacoes": s.observacoes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }

        return jsonify([to_dict(s) for s in sessoes]), 200
    except Exception as e:
        logger.error(f"Error in api_list_sessoes: {str(e)}")
        return jsonify([]), 500
    finally:
        if db:
            db.close()


@sessoes_bp.route("/api/<int:sessao_id>", methods=["GET"])
@login_required
def api_get_sessao(sessao_id: int):
    db = None
    try:
        db = SessionLocal()
        s = db.query(Sessao).get(sessao_id)
        if not s:
            return api_response(False, "Sessão não encontrada", None, 404)

        data = {
            "id": s.id,
            "data": s.data.isoformat() if s.data else None,
            "hora": s.hora.strftime("%H:%M:%S") if s.hora else None,
            "cliente": (
                {"id": s.cliente.id, "name": s.cliente.name} if s.cliente else None
            ),
            "artista": (
                {"id": s.artista.id, "name": s.artista.name} if s.artista else None
            ),
            "valor": float(s.valor) if s.valor is not None else None,
            "observacoes": s.observacoes,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        return api_response(True, "Sessão encontrada", data, 200)
    except Exception as e:
        logger.error(f"Error in api_get_sessao: {str(e)}")
        return api_response(False, f"Error: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@sessoes_bp.route("/api/<int:sessao_id>", methods=["PUT"])
@login_required
def api_update_sessao(sessao_id: int):
    db = None
    try:
        db = SessionLocal()
        if not request.is_json:
            return api_response(False, "Expected JSON payload", None, 400)
        payload = request.get_json()

        s = db.query(Sessao).get(sessao_id)
        if not s:
            return api_response(False, "Sessão não encontrada", None, 404)

        # Update fields if provided
        try:
            if "data" in payload and payload["data"]:
                # Expect YYYY-MM-DD
                s.data = (
                    date.fromisoformat(payload["data"])
                    if isinstance(payload["data"], str)
                    else payload["data"]
                )
            if "hora" in payload and payload["hora"]:
                # Accept HH:MM or HH:MM:SS
                try:
                    s.hora = time.fromisoformat(payload["hora"])
                except Exception:
                    s.hora = datetime.strptime(payload["hora"], "%H:%M").time()
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
            return api_response(False, f"Update failed: {str(e)}", None, 400)

        data = {
            "id": s.id,
            "data": s.data.isoformat() if s.data else None,
            "hora": s.hora.strftime("%H:%M:%S") if s.hora else None,
            "cliente": (
                {"id": s.cliente.id, "name": s.cliente.name} if s.cliente else None
            ),
            "artista": (
                {"id": s.artista.id, "name": s.artista.name} if s.artista else None
            ),
            "valor": float(s.valor) if s.valor is not None else None,
            "observacoes": s.observacoes,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        return api_response(True, "Sessão atualizada com sucesso", data, 200)
    finally:
        if db:
            db.close()


@sessoes_bp.route("/api/<int:sessao_id>", methods=["DELETE"])
@login_required
def api_delete_sessao(sessao_id: int):
    db = None
    try:
        db = SessionLocal()
        s = db.query(Sessao).get(sessao_id)
        if not s:
            return api_response(False, "Sessão não encontrada", None, 404)

        try:
            db.delete(s)
            db.commit()
        except Exception as e:
            db.rollback()
            return api_response(False, f"Delete failed: {str(e)}", None, 400)

        return api_response(True, "Sessão excluída", None, 200)
    finally:
        if db:
            db.close()


# DEPRECATED: Legacy endpoint - use /artist/create instead
@sessoes_bp.route("/cadastrar_artista", methods=["POST"])
def cadastrar_artista() -> tuple[Response, int]:
    """Legacy endpoint for artist creation.

    DEPRECATED: Use /artist/create_form instead.
    This is kept for backwards compatibility only.
    """
    logger.warning(
        "Using deprecated endpoint /sessoes/cadastrar_artista. Use /artist/create_form instead."
    )

    try:
        user_service = _get_user_service()
        nome = request.form.get("artista")

        if not nome:
            return jsonify({"error": "Nome do artista é obrigatório."}), 400

        artist = user_service.register_artist(name=nome.strip())

        return jsonify({"id": artist.id, "name": artist.name}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in legacy cadastrar_artista: {str(e)}")
        return jsonify({"error": "Erro interno do servidor."}), 500
