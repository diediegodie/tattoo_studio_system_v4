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

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
sessoes_bp = Blueprint("sessoes", __name__, url_prefix="/sessoes")


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
        return render_template("sessoes.html", sessoes=sessoes)
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        flash("Erro ao carregar sessões.", "error")
        return render_template("sessoes.html", sessoes=[])
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
