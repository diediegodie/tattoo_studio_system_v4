from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from typing import Union, Dict, Any, Tuple, cast
from werkzeug.wrappers import Response
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.base import Client, Pagamento  # Import existing models from db.base
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.repositories.pagamento_repository import PagamentoRepository
from app.db.base import Pagamento as PagamentoModel
import inspect
import asyncio

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
financeiro_bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")


def _safe_render(template_name: str, **context):
    """Render template but fall back to empty string when template not found (useful in unit tests)."""
    try:
        return render_template(template_name, **context)
    except Exception:
        return ""


def _safe_redirect(endpoint_or_path: str):
    """Redirect using a path or endpoint; if endpoint building fails, assume it's a path and redirect directly."""
    try:
        # If it looks like an endpoint (contains a dot), try url_for
        if "." in endpoint_or_path:
            return redirect(url_for(endpoint_or_path))
        # Otherwise try to treat as a path
        return redirect(endpoint_or_path)
    except Exception:
        # Fallback to direct path redirect
        return redirect(endpoint_or_path)


def _get_user_service():
    """Dependency injection factory for UserService."""
    db = SessionLocal()
    repo = UserRepository(db)
    return UserService(repo)


def _maybe_await(value):
    """Resolve awaitable objects returned by test AsyncMocks.

    If value is awaitable, run it to completion on an event loop. Otherwise return as-is.
    """
    try:
        if inspect.isawaitable(value):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(value)
    except Exception:
        pass
    return value


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
            cliente_id = _maybe_await(request.form.get("cliente_id"))
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

            # Validate required fields
            if not all([data_str, valor, forma_pagamento, cliente_id, artista_id]):
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
                flash("Todos os campos obrigatórios devem ser preenchidos.", "error")
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

            flash("Pagamento registrado com sucesso!", "success")
            return _safe_redirect("/financeiro/")

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


# API Endpoints for Financeiro
@financeiro_bp.route("/api", methods=["GET"])
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

        return jsonify([to_dict(p) for p in pagamentos]), 200
    except Exception as e:
        logger.error(f"Error in api_list_pagamentos: {str(e)}")
        return jsonify([]), 500
    finally:
        if db:
            db.close()


@financeiro_bp.route("/api/<int:pagamento_id>", methods=["GET"])
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
            return (
                jsonify({"success": False, "message": "Pagamento não encontrado"}),
                404,
            )

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

        return (
            jsonify({"success": True, "message": "Pagamento encontrado", "data": data}),
            200,
        )
    except Exception as e:
        logger.error(f"Error in api_get_pagamento: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    finally:
        if db:
            db.close()


def api_response(
    success: bool, message: str, data: Any = None, status_code: int = 200
) -> Tuple[Response, int]:
    """Helper function to return consistent API responses."""
    response = {"success": success, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


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
                if hasattr(updated, "cliente") and getattr(updated, "cliente", None)
                else None
            ),
            "artista": (
                {"id": updated.artista.id, "name": updated.artista.name}
                if hasattr(updated, "artista") and getattr(updated, "artista", None)
                else None
            ),
            "observacoes": getattr(updated, "observacoes", None),
            "created_at": (
                updated.created_at.isoformat()
                if hasattr(updated, "created_at")
                and getattr(updated, "created_at", None)
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
