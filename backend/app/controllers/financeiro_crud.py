"""
CRUD operations for financeiro module.
Handles web-based CRUD operations for payments.
"""

import logging

from app.controllers.financeiro_helpers import (
    _get_user_service,
    _safe_redirect,
    _safe_render,
)
from app.db.base import Client
from app.db.base import Pagamento as PagamentoModel
from app.db.session import SessionLocal
from app.repositories.pagamento_repository import PagamentoRepository
from flask import Blueprint, flash
from flask_login import login_required

logger = logging.getLogger(__name__)

# Import the blueprint from financeiro_controller instead of creating a new one
from app.controllers.financeiro_controller import financeiro_bp  # noqa: E402


@financeiro_bp.route("/editar-pagamento/<int:pagamento_id>", methods=["GET"])
@login_required
def editar_pagamento(pagamento_id: int):
    """Render the pagamento form prefilled for editing (reuses registrar template)."""
    db = None
    try:
        db = SessionLocal()
        pagamento = db.query(PagamentoModel).get(pagamento_id)
        if not pagamento:
            flash("Pagamento não encontrado.", "error")
            return _safe_redirect("/financeiro/")

        clients = db.query(Client).order_by(Client.name).all()
        user_service = _get_user_service()
        artists = user_service.list_artists()

        # Prefill form values from pagamento
        return _safe_render(
            "registrar_pagamento.html",
            clients=clients,
            artists=artists,
            data=pagamento.data.isoformat() if pagamento.data else "",
            cliente_id=getattr(pagamento, "cliente_id", ""),
            artista_id=getattr(pagamento, "artista_id", ""),
            valor=(
                str(pagamento.valor)
                if getattr(pagamento, "valor", None) is not None
                else ""
            ),
            forma_pagamento=getattr(pagamento, "forma_pagamento", ""),
            observacoes=getattr(pagamento, "observacoes", ""),
            sessao_id=getattr(pagamento, "sessao_id", ""),
            edit_id=pagamento_id,
        )
    except Exception as e:
        logger.exception("Error loading pagamento for edit: %s", e)
        flash("Erro ao carregar pagamento.", "error")
        return _safe_redirect("/financeiro/")
    finally:
        if db:
            db.close()


@financeiro_bp.route("/delete-pagamento/<int:pagamento_id>", methods=["POST"])
@login_required
def delete_pagamento(pagamento_id: int):
    """Web wrapper to delete a pagamento and redirect back to financeiro."""
    db = None
    try:
        db = SessionLocal()
        repo = PagamentoRepository(db)
        existing = repo.get_by_id(pagamento_id)
        if not existing:
            flash("Pagamento não encontrado.", "error")
            return _safe_redirect("/financeiro/")

        ok = repo.delete(pagamento_id)
        if not ok:
            flash("Falha ao excluir pagamento.", "error")
        else:
            flash("Pagamento excluído com sucesso.", "success")

        return _safe_redirect("/financeiro/")
    except Exception as e:
        logger.exception("Error deleting pagamento: %s", e)
        if db:
            db.rollback()
        flash("Erro ao excluir pagamento.", "error")
        return _safe_redirect("/financeiro/")
    finally:
        if db:
            db.close()
