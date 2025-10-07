"""Main route handlers for sessoes module.

Handles web-based CRUD operations for sessions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Union

from app.controllers.sessoes_controller import sessoes_bp
from app.controllers.sessoes_helpers import _get_user_service
from app.core.validation import SessaoValidator
from app.db.base import Client, Sessao
from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from werkzeug.wrappers.response import Response

logger = logging.getLogger(__name__)


def _render_nova_sessao_form(
    db_session: Optional[Any],
    *,
    clients: Optional[Sequence[Client]] = None,
    artists: Optional[Sequence[Any]] = None,
    event: Optional[Any] = None,
    is_google_event: bool = False,
    event_title_with_suffix: str = "",
    form_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Render the "nova sessão" form with consistent context."""

    if clients is not None:
        resolved_clients = list(clients)
    elif db_session is not None:
        resolved_clients = db_session.query(Client).order_by(Client.name).all()
    else:
        resolved_clients = []

    if artists is not None:
        resolved_artists = list(artists)
    elif db_session is not None:
        user_service = _get_user_service()
        resolved_artists = user_service.list_artists()
    else:
        resolved_artists = []

    return render_template(
        "nova_sessao.html",
        clients=resolved_clients,
        artists=resolved_artists,
        event=event,
        is_google_event=is_google_event,
        event_title_with_suffix=event_title_with_suffix,
        form_data=form_data or {},
    )


@sessoes_bp.route("/", methods=["GET"])
@login_required
def sessoes_home() -> Response:
    """Root route for sessoes - redirects to list."""
    return redirect(url_for("sessoes.list_sessoes"))


@sessoes_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_sessao() -> Union[str, Response]:
    """Create a new session/appointment."""
    db = None
    try:
        from app.db.session import SessionLocal

        db = SessionLocal()

        if request.method == "GET":
            clients = db.query(Client).order_by(Client.name).all()

            user_service = _get_user_service()
            artists = user_service.list_artists()

            event_id = request.args.get("event_id")
            event = None
            is_google_event = False
            event_title_with_suffix = ""

            if event_id:
                try:
                    from datetime import timedelta

                    from app.services.google_calendar_service import (
                        GoogleCalendarService,
                    )
                    from flask_login import current_user

                    calendar_service = GoogleCalendarService()

                    if calendar_service.is_user_authorized(str(current_user.id)):
                        start_date = datetime.now() - timedelta(days=30)
                        end_date = start_date + timedelta(days=90)

                        events = calendar_service.get_user_events(
                            str(current_user.id), start_date, end_date
                        )

                        for candidate in events:
                            if (
                                candidate.google_event_id == event_id
                                or candidate.id == event_id
                            ):
                                event = candidate
                                is_google_event = bool(candidate.google_event_id)
                                event_title = candidate.title or "Evento sem título"
                                if (
                                    is_google_event
                                    and "(google agenda)" not in event_title
                                ):
                                    event_title_with_suffix = (
                                        f"{event_title} (google agenda)"
                                    )
                                else:
                                    event_title_with_suffix = event_title
                                break

                        if not event:
                            logger.warning("Event with ID %s not found", event_id)
                except Exception as err:  # pragma: no cover - fallback path
                    logger.error("Error fetching event data: %s", err)

            return _render_nova_sessao_form(
                db,
                clients=clients,
                artists=artists,
                event=event,
                is_google_event=is_google_event,
                event_title_with_suffix=event_title_with_suffix,
            )

        sessao_request_data: Dict[str, Any] = {
            "data": request.form.get("data"),
            "cliente_id": request.form.get("cliente_id"),
            "artista_id": request.form.get("artista_id"),
            "valor": request.form.get("valor"),
            "status": request.form.get("status") or "active",
            "observacoes": request.form.get("observacoes"),
        }

        google_event_id = request.form.get("google_event_id")

        validator = SessaoValidator()
        validation_result = validator.validate(sessao_request_data)

        if not validation_result.is_valid:
            for error_message in validation_result.errors:
                flash(error_message, "error")
            return _render_nova_sessao_form(db, form_data=sessao_request_data)

        if google_event_id:
            existing_session = (
                db.query(Sessao)
                .filter(Sessao.google_event_id == google_event_id)
                .first()
            )
            if existing_session:
                flash("Uma sessão para este evento do Google já existe.", "info")
                return redirect(url_for("sessoes.list_sessoes"))

        cleaned_data = validation_result.cleaned_data
        parsed_date = cleaned_data.get("data")
        cliente_id_int = cleaned_data.get("cliente_id")
        artista_id_int = cleaned_data.get("artista_id")
        valor_decimal = cleaned_data.get("valor")
        status_value = cleaned_data.get("status") or "active"
        observacoes = cleaned_data.get("observacoes")

        if parsed_date is None or cliente_id_int is None or artista_id_int is None:
            flash("Dados da sessão incompletos após validação.", "error")
            return _render_nova_sessao_form(db, form_data=sessao_request_data)

        sessao = Sessao(
            data=parsed_date,
            valor=valor_decimal,
            observacoes=observacoes,
            cliente_id=cliente_id_int,
            artista_id=artista_id_int,
            google_event_id=google_event_id,
            status=status_value,
        )

        try:
            db.add(sessao)
            db.commit()
        except IntegrityError as integrity_error:
            db.rollback()
            logger.info("IntegrityError creating sessao: %s", integrity_error)
            flash("Sessão já existe (submissão duplicada).", "info")
            return _render_nova_sessao_form(db, form_data=sessao_request_data)

        flash("Sessão criada com sucesso!", "success")
        return redirect(url_for("sessoes.list_sessoes"))

    except Exception as err:  # pragma: no cover - unexpected failure path
        logger.error("Error in nova_sessao: %s", err)
        flash("Erro interno do servidor.", "error")
        try:
            return _render_nova_sessao_form(db)
        except Exception:
            return Response("", status=500)
    finally:
        if db:
            db.close()

    return redirect(url_for("sessoes.nova_sessao"))


@sessoes_bp.route("/finalizar/<int:sessao_id>", methods=["POST"])
@login_required
def finalizar_sessao(sessao_id: int) -> Response:
    """Mark session as completed and redirect to payment registration."""
    db = None
    try:
        from app.db.session import SessionLocal

        db = SessionLocal()

        sessao = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .filter(Sessao.id == sessao_id)
            .first()
        )
        if not sessao:
            flash("Sessão não encontrada.", "error")
            return redirect("/sessoes/list")

        current_status = getattr(sessao, "status", None)
        if current_status and current_status == "completed":
            flash("Esta sessão já foi finalizada.", "info")
            return redirect("/sessoes/list")

        setattr(sessao, "status", "completed")
        setattr(sessao, "updated_at", datetime.now())
        db.commit()

        flash(
            "Sessão marcada como finalizada. Redirecionando para registro de pagamento.",
            "success",
        )

        data_value = getattr(sessao, "data", None)
        valor_value = getattr(sessao, "valor", None)
        observacoes_value = getattr(sessao, "observacoes", None)

        data_str = data_value.isoformat() if data_value is not None else ""
        valor_float = float(valor_value) if valor_value is not None else 0.0

        cliente_param = getattr(sessao, "cliente_id", "")
        artista_param = getattr(sessao, "artista_id", "")
        qs = (
            f"/financeiro/registrar-pagamento?sessao_id={sessao_id}&data={data_str}"
            f"&cliente_id={cliente_param}&artista_id={artista_param}&valor={valor_float}&observacoes={observacoes_value or ''}"
        )
        return redirect(qs)

    except Exception as err:
        logger.error("Error finalizing session %s: %s", sessao_id, err)
        flash("Erro ao finalizar sessão.", "error")
        return redirect("/sessoes/list")
    finally:
        if db:
            db.close()


@sessoes_bp.route("/list")
def list_sessoes() -> str:
    """List all active sessions."""
    db = None
    try:
        from app.db.session import SessionLocal

        db = SessionLocal()

        sessoes = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .filter(Sessao.status == "active")
            .order_by(Sessao.data.asc(), Sessao.created_at.asc())
            .all()
        )

        clients = db.query(Client).order_by(Client.name).all()

        user_service = _get_user_service()
        artists = user_service.list_artists()

        return render_template(
            "sessoes.html", sessoes=sessoes, clients=clients, artists=artists
        )
    except Exception as err:
        logger.error("Error listing sessions: %s", err)
        flash("Erro ao carregar sessões.", "error")
        try:
            return render_template("sessoes.html", sessoes=[])
        except Exception:
            return ""
    finally:
        if db:
            db.close()
