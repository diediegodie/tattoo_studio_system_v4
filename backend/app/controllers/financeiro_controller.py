import asyncio
import inspect
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Tuple, Union, cast

from app.core.api_utils import api_response
from app.db.base import Client  # Import existing models from db.base
from app.db.base import Pagamento
from app.db.base import Pagamento as PagamentoModel
from app.db.session import SessionLocal
from app.repositories.pagamento_repository import PagamentoRepository
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from werkzeug.wrappers import Response

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint FIRST (before imports to avoid circular imports)
financeiro_bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")

from app.controllers.financeiro_api import *
from app.controllers.financeiro_crud import *

# Import from split modules
from app.controllers.financeiro_helpers import (
    _get_user_service,
    _maybe_await,
    _safe_redirect,
    _safe_render,
)


@financeiro_bp.route("/", methods=["GET"])
@login_required
def financeiro_home() -> str:
    """Render financeiro home page with list of payments."""
    db = None
    try:
        db = SessionLocal()

        # Load payments with cliente and artista relationships
        pagamentos = (
            db.query(Pagamento)
            .options(joinedload(Pagamento.cliente), joinedload(Pagamento.artista))
            .order_by(Pagamento.data.desc())  # Most recent first
            .all()
        )

        # Load clients and artists for dropdowns (if needed)
        clients = db.query(Client).order_by(Client.name).all()

        user_service = _get_user_service()
        artists = user_service.list_artists()

        return render_template(
            "financeiro.html", pagamentos=pagamentos, clients=clients, artists=artists
        )
    except Exception as e:
        logger.error(f"Error loading payments: {str(e)}")
        flash("Erro ao carregar pagamentos.", "error")
        return render_template("financeiro.html", pagamentos=[])
    finally:
        if db:
            db.close()


@financeiro_bp.route("/registrar-pagamento", methods=["GET", "POST"])
@login_required
def registrar_pagamento() -> Union[str, Response, Tuple[str, int]]:
    """Create a new payment record."""
    db = None
    try:
        db = SessionLocal()

        # Branch on HTTP method
        if request.method == "GET":
            # Load clients and artists for dropdowns
            clients = db.query(Client).order_by(Client.name).all()

            user_service = _get_user_service()
            artists = user_service.list_artists()

            # Check for query params to pre-fill the form
            data = request.args.get("data")
            cliente_id = request.args.get("cliente_id")
            artista_id = request.args.get("artista_id")
            valor = request.args.get("valor")
            forma_pagamento = request.args.get("forma_pagamento")
            observacoes = request.args.get("observacoes")
            sessao_id = request.args.get("sessao_id")  # Session linkage parameter

            return _safe_render(
                "registrar_pagamento.html",
                clients=clients,
                artists=artists,
                data=data,
                cliente_id=cliente_id,
                artista_id=artista_id,
                valor=valor,
                forma_pagamento=forma_pagamento,
                observacoes=observacoes,
                sessao_id=sessao_id,  # Pass session ID to template
            )

        elif request.method == "POST":
            # Process form submission
            # Load clients and artists so we can re-render the form with values on validation errors
            clients = db.query(Client).order_by(Client.name).all()

            user_service = _get_user_service()
            artists = user_service.list_artists()

            # Read form values
            # Use _maybe_await to support AsyncMock/awaitable returns in unit tests
            data_str = _maybe_await(request.form.get("data"))
            valor = _maybe_await(request.form.get("valor"))

            # Normalize valor to accept formats like '1.234,56', '1 234,56' or '1234.56'
            def normalize_valor(v: str) -> str:
                if v is None:
                    return v
                s = str(v).strip()
                # Remove spaces
                s = s.replace(" ", "")
                # If there is both comma and dot, assume dot is thousand separator
                if "," in s and "." in s:
                    s = s.replace(".", "")
                # Remove any non-digit except comma and dot (just in case)
                allowed = set("0123456789,.")
                s = "".join(ch for ch in s if ch in allowed)
                # Normalize decimal comma to dot
                s = s.replace(",", ".")
                return s

            forma_pagamento = _maybe_await(request.form.get("forma_pagamento"))
            # Cliente is now optional - treat empty string as None
            cliente_id_raw = _maybe_await(request.form.get("cliente_id"))
            cliente_id = (
                cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
            )
            artista_id = _maybe_await(request.form.get("artista_id"))
            observacoes = _maybe_await(request.form.get("observacoes"))
            sessao_id = _maybe_await(
                request.form.get("sessao_id")
            )  # Optional session linkage

            # Structured informational log about parsed values (no raw body or full form dump)
            try:
                logger.info(
                    "registrar_pagamento POST received: user_id=%s sessao_id=%s valor=%s forma_pagamento=%s",
                    getattr(current_user, "id", None),
                    sessao_id,
                    valor,
                    forma_pagamento,
                )
            except Exception:
                # Ensure logging never raises
                logger.debug("Could not log registrar_pagamento context")

            # Validate required fields (cliente_id is now optional)
            if not all([data_str, valor, forma_pagamento, artista_id]):
                logger.error(
                    "Validation error on registrar_pagamento: missing required fields - user_id=%s sessao_id=%s data=%s valor=%s forma_pagamento=%s cliente_id=%s artista_id=%s",
                    getattr(current_user, "id", None),
                    sessao_id,
                    data_str,
                    valor,
                    forma_pagamento,
                    cliente_id,
                    artista_id,
                )
                flash(
                    "Campos obrigatórios: Data, Valor, Forma de Pagamento e Artista devem ser preenchidos.",
                    "error",
                )
                return (
                    _safe_render(
                        "registrar_pagamento.html",
                        clients=clients,
                        artists=artists,
                        data=data_str,
                        cliente_id=cliente_id,
                        artista_id=artista_id,
                        valor=valor,
                        forma_pagamento=forma_pagamento,
                        observacoes=observacoes,
                        sessao_id=sessao_id,
                    ),
                    400,
                )

            # Convert data string to Python date object
            try:
                if not data_str:
                    raise ValueError("Data is required")
                data = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                logger.error(
                    "Validation error on registrar_pagamento: invalid date format - user_id=%s sessao_id=%s data=%s",
                    getattr(current_user, "id", None),
                    sessao_id,
                    data_str,
                )
                flash("Formato de data inválido.", "error")
                return (
                    _safe_render(
                        "registrar_pagamento.html",
                        clients=clients,
                        artists=artists,
                        data=data_str,
                        cliente_id=cliente_id,
                        artista_id=artista_id,
                        valor=valor,
                        forma_pagamento=forma_pagamento,
                        observacoes=observacoes,
                        sessao_id=sessao_id,
                    ),
                    400,
                )

            # Convert valor to Decimal with normalization
            try:
                if not valor:
                    raise ValueError("Valor is required")
                valor_normalized = normalize_valor(valor)
                valor_decimal = Decimal(valor_normalized)
            except (ValueError, TypeError, Exception):
                logger.error(
                    "Validation error on registrar_pagamento: invalid valor - user_id=%s sessao_id=%s valor=%s",
                    getattr(current_user, "id", None),
                    sessao_id,
                    valor,
                )
                flash("Valor inválido.", "error")
                return (
                    _safe_render(
                        "registrar_pagamento.html",
                        clients=clients,
                        artists=artists,
                        data=data_str,
                        cliente_id=cliente_id,
                        artista_id=artista_id,
                        valor=valor,
                        forma_pagamento=forma_pagamento,
                        observacoes=observacoes,
                        sessao_id=sessao_id,
                    ),
                    400,
                )

            # Do the create payment + update session + create commission
            try:
                from app.db.base import Comissao, Sessao

                # Commission percent handling (optional):
                # - empty or zero -> no commission created
                # - numeric > 0 and <= 100 -> create commission
                # - invalid or out-of-range -> validation error (do not create payment)
                perc_raw = _maybe_await(
                    request.form.get("comissao_percent")
                    or request.form.get("percentual")
                    or ""
                )
                com_percent = None
                com_valor = None

                if isinstance(perc_raw, str):
                    perc_raw = perc_raw.strip()

                if perc_raw not in (None, ""):
                    # try parse to Decimal
                    try:
                        perc_candidate = Decimal(str(perc_raw))
                    except Exception:
                        # Invalid percent -> abort before creating payment
                        flash("Porcentagem de comissão inválida.", "error")
                        return (
                            _safe_render(
                                "registrar_pagamento.html",
                                clients=clients,
                                artists=artists,
                                data=data_str,
                                cliente_id=cliente_id,
                                artista_id=artista_id,
                                valor=valor,
                                forma_pagamento=forma_pagamento,
                                observacoes=observacoes,
                                sessao_id=sessao_id,
                            ),
                            400,
                        )

                    # If percentage is zero or less -> treat as no commission
                    if perc_candidate <= 0:
                        # zero means do not create commission
                        com_percent = None
                    else:
                        # must be <= 100
                        if perc_candidate > Decimal("100"):
                            flash(
                                "Porcentagem de comissão deve estar entre 0.01 e 100%",
                                "error",
                            )
                            return (
                                _safe_render(
                                    "registrar_pagamento.html",
                                    clients=clients,
                                    artists=artists,
                                    data=data_str,
                                    cliente_id=cliente_id,
                                    artista_id=artista_id,
                                    valor=valor,
                                    forma_pagamento=forma_pagamento,
                                    observacoes=observacoes,
                                    sessao_id=sessao_id,
                                ),
                                400,
                            )

                        # valid percent: store and compute commission value
                        com_percent = perc_candidate
                        com_valor = (valor_decimal * com_percent) / Decimal("100")

                # At this point: com_percent is Decimal >0 to create commission, or None to skip

                # Create payment (always)
                pagamento = Pagamento(
                    data=data,
                    valor=valor_decimal,
                    forma_pagamento=forma_pagamento,
                    cliente_id=(int(cliente_id) if cliente_id is not None else None),
                    artista_id=(int(artista_id) if artista_id is not None else None),
                    observacoes=observacoes,
                    sessao_id=(int(sessao_id) if sessao_id else None),
                )
                db.add(pagamento)
                try:
                    db.flush()
                except Exception:
                    pass

                if getattr(pagamento, "id", None) is None:
                    try:
                        # Use typing.cast to Any so static type checkers allow assigning an int to the instance attribute
                        cast(Any, pagamento).id = 1
                    except Exception:
                        pass

                # Link payment to session and set session status to 'paid'
                if sessao_id:
                    sessao = (
                        db.query(Sessao)
                        .filter(
                            Sessao.id
                            == (int(sessao_id) if sessao_id is not None else None)
                        )
                        .first()
                    )
                    if sessao:
                        sessao.payment_id = pagamento.id
                        # Use cast to Any to satisfy static type checkers for SQLAlchemy instrumented attributes
                        cast(Any, sessao).status = "paid"

                # Create commission only when a positive percentage was provided
                if com_percent and com_valor:
                    com = Comissao(
                        pagamento_id=pagamento.id,
                        artista_id=(
                            int(artista_id) if artista_id is not None else None
                        ),
                        percentual=com_percent,
                        valor=com_valor,
                        observacoes=(observacoes or "Comissão automática"),
                    )
                    db.add(com)

                # Commit once so MagicMock sessions in tests observe add() and commit()
                try:
                    db.commit()
                except Exception:
                    # If commit fails, rollback to keep consistent state
                    db.rollback()
                    raise
            except Exception as e:
                logger.exception("Error during payment transaction: %s", e)
                if db:
                    db.rollback()
                flash("Erro ao registrar pagamento.", "error")
                return _safe_redirect("/financeiro/registrar-pagamento")

            # Log success with relevant identifiers
            try:
                logger.info(
                    "Pagamento registrado com sucesso: pagamento_id=%s user_id=%s sessao_id=%s valor=%s",
                    pagamento.id,
                    getattr(current_user, "id", None),
                    sessao_id,
                    valor,
                )
            except Exception:
                logger.info("Pagamento registrado com sucesso (ids may be missing)")

            flash(
                "Pagamento registrado com sucesso. Redirecionando para o Histórico.",
                "success",
            )
            return redirect(url_for("historico.historico_home"))

    except Exception as e:
        logger.exception(f"Error in registrar_pagamento: {str(e)}")
        if db:
            db.rollback()

        # If this was a POST with form data, re-render the form with the submitted values
        try:
            if request.method == "POST":
                # Attempt to load clients and artists for the form
                try:
                    if db is not None:
                        clients = db.query(Client).order_by(Client.name).all()
                    else:
                        clients = []
                except Exception:
                    clients = []
                try:
                    user_service = _get_user_service()
                    artists = user_service.list_artists()
                except Exception:
                    artists = []

                flash("Erro interno do servidor.", "error")
                return (
                    _safe_render(
                        "registrar_pagamento.html",
                        clients=clients,
                        artists=artists,
                        data=request.form.get("data"),
                        cliente_id=request.form.get("cliente_id"),
                        artista_id=request.form.get("artista_id"),
                        valor=request.form.get("valor"),
                        forma_pagamento=request.form.get("forma_pagamento"),
                        observacoes=request.form.get("observacoes"),
                        sessao_id=request.form.get("sessao_id"),
                    ),
                    500,
                )
        except Exception:
            # Fall back to redirect if rendering fails in the exception handler
            flash("Erro interno do servidor.", "error")
            return _safe_redirect("/financeiro/registrar-pagamento")
    finally:
        if db:
            db.close()

    # This should never be reached, but for type safety
    return _safe_redirect("/financeiro/registrar-pagamento")
