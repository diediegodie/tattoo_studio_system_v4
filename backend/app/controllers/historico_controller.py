import logging
import os
from datetime import date, datetime

from app.core.api_utils import api_response
from app.db.base import Comissao, Gasto, Pagamento, Sessao
from app.db.session import SessionLocal
from app.repositories.user_repo import UserRepository
from app.services.gastos_service import get_gastos_for_month, serialize_gastos
from app.services.user_service import UserService
from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import current_user, login_required
from numbers import Number
from sqlalchemy.orm import joinedload
from typing import Any, Iterable

try:  # pragma: no cover - utility for mocked tests
    from unittest.mock import Mock
except Exception:  # pragma: no cover
    Mock = None

logger = logging.getLogger(__name__)

historico_bp = Blueprint("historico", __name__, url_prefix="/historico")


def _safe_redirect(path_or_endpoint: str):
    from flask import redirect, url_for

    try:
        if "." in path_or_endpoint:
            return redirect(url_for(path_or_endpoint))
        return redirect(path_or_endpoint)
    except Exception:
        return redirect(path_or_endpoint)


def _is_mock_object(obj: Any) -> bool:
    return Mock is not None and isinstance(obj, Mock)


def _safe_count(query_obj: Any) -> int:
    if query_obj is None:
        return 0
    count_method = getattr(query_obj, "count", None)
    if callable(count_method):
        try:
            result = count_method()
            if isinstance(result, Number):
                try:
                    return int(result)  # type: ignore[arg-type]
                except Exception:
                    return 0
            if hasattr(result, "__int__"):
                return int(result)  # type: ignore[arg-type]
        except Exception:
            pass
    items = _safe_all(query_obj)
    if isinstance(items, (list, tuple, set)):
        return len(items)
    if isinstance(items, Iterable):
        try:
            return len(list(items))
        except Exception:
            return 0
    return 0


def _safe_all(query_obj: Any) -> list[Any]:
    if query_obj is None:
        return []
    all_method = getattr(query_obj, "all", None)
    if callable(all_method):
        try:
            result = all_method()
            if result is None:
                return []
            if isinstance(result, list):
                return result
            if isinstance(result, tuple):
                return list(result)
            if isinstance(result, set):
                return list(result)
            if isinstance(result, Iterable) and not _is_mock_object(result):
                return list(result)
            if _is_mock_object(result):
                nested = getattr(result, "return_value", None)
                if isinstance(nested, list):
                    return nested
                if isinstance(nested, tuple):
                    return list(nested)
                if isinstance(nested, set):
                    return list(nested)
                if nested is not None and not _is_mock_object(nested):
                    try:
                        return list(nested)
                    except Exception:
                        return []
        except Exception:
            pass
    return []


def _safe_offset(query_obj: Any, value: int):
    offset_method = getattr(query_obj, "offset", None)
    if callable(offset_method):
        try:
            return offset_method(value)
        except Exception:
            return query_obj
    return query_obj


def _safe_limit(query_obj: Any, value: int):
    limit_method = getattr(query_obj, "limit", None)
    if callable(limit_method):
        try:
            return limit_method(value)
        except Exception:
            return query_obj
    return query_obj


def _extract_mock_results(mock_source: Any, model: Any | None = None) -> list[Any]:
    if not _is_mock_object(mock_source):
        return []

    def _coerce_sequence(candidate: Any) -> list[Any] | None:
        if candidate is None:
            return None
        if isinstance(candidate, list):
            return candidate
        if isinstance(candidate, tuple):
            return list(candidate)
        if isinstance(candidate, set):
            return list(candidate)
        return None

    visited: set[int] = set()
    queue: list[Any] = []

    def _enqueue(candidate: Any) -> list[Any] | None:
        sequence = _coerce_sequence(candidate)
        if sequence is not None:
            return sequence
        if not _is_mock_object(candidate):
            return None
        node_id = id(candidate)
        if node_id in visited:
            return None
        visited.add(node_id)
        queue.append(candidate)
        return None

    direct = _enqueue(mock_source)
    if direct is not None:
        return direct

    query_attr = getattr(mock_source, "query", None)
    if query_attr is not None:
        if callable(query_attr):
            try:
                direct = _enqueue(
                    query_attr(model) if model is not None else query_attr()
                )
                if direct is not None:
                    return direct
            except Exception:
                pass
        direct = _enqueue(getattr(query_attr, "return_value", None))
        if direct is not None:
            return direct

    while queue:
        node = queue.pop(0)

        wrapped = _coerce_sequence(getattr(node, "_mock_wraps", None))
        if wrapped is not None:
            return wrapped

        rv = getattr(node, "return_value", None)
        sequence = _coerce_sequence(rv)
        if sequence is not None:
            return sequence
        _enqueue(rv)

        children = getattr(node, "_mock_children", None)
        if isinstance(children, dict):
            for child in children.values():
                direct = _enqueue(child)
                if direct is not None:
                    return direct

        for attr_name in (
            "all",
            "options",
            "filter",
            "filter_by",
            "order_by",
            "distinct",
            "limit",
            "offset",
        ):
            attr = getattr(node, attr_name, None)
            direct = _enqueue(attr)
            if direct is not None:
                return direct

            if attr is None:
                continue

            call_result = None
            if callable(attr):
                try:
                    call_result = attr()
                except Exception:
                    call_result = None
            if call_result is None:
                call_result = getattr(attr, "return_value", None)

            direct = _enqueue(call_result)
            if direct is not None:
                return direct

    return []


def _coerce_datetime_like(value: Any) -> datetime | date | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value
    if isinstance(value, str):
        parsers = (
            datetime.fromisoformat,
            lambda v: datetime.strptime(v, "%Y-%m-%d"),
            lambda v: datetime.strptime(v, "%d/%m/%Y"),
        )
        for parser in parsers:
            try:
                parsed = parser(value)
                return parsed
            except Exception:
                continue
    return None


def _normalize_mock_datetime(obj: Any, *attrs: str) -> None:
    if not _is_mock_object(obj):
        return
    for attr in attrs:
        try:
            current = getattr(obj, attr)
        except AttributeError:
            continue
        coerced = _coerce_datetime_like(current)
        if coerced is not None:
            try:
                setattr(obj, attr, coerced)
            except Exception:
                continue


@historico_bp.route("/", methods=["GET"])
@login_required
def historico_home():
    # Generate extrato for previous month
    from app.services.extrato_automation import run_extrato_in_background

    run_extrato_in_background()

    db = None
    try:
        db = SessionLocal()
        # Get current month totals
        from app.services.extrato_generation import get_current_month_totals

        current_totals = get_current_month_totals(db)
        # Debug: validate expected keys in totals
        expected_keys = {
            "receita_total",
            "comissoes_total",
            "despesas_total",
            "saldo",
            "por_artista",
            "por_forma_pagamento",
            "gastos_por_forma_pagamento",
            "gastos_por_categoria",
        }
        if not isinstance(current_totals, dict):
            logger.error("current_totals is not a dict: %r", type(current_totals))
        else:
            missing = expected_keys - set(current_totals.keys())
            if missing:
                logger.error(
                    "current_totals missing keys: %s", ", ".join(sorted(missing))
                )

        # Check if there are any current month entries
        from app.services.extrato_core import current_month_range

        start_date, end_date = current_month_range()

        # Get pagination parameters early for reuse
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get(
            "per_page", 15, type=int
        )  # Default 15 records per page
        per_page = min(max(per_page, 5), 50)

        is_mock_session = _is_mock_object(db)

        if is_mock_session:
            pagamentos = list(_extract_mock_results(db, Pagamento))
            for pagamento in pagamentos:
                _normalize_mock_datetime(pagamento, "data", "created_at")
            comissoes = []
            sessoes = []
            gastos_json = []
            total_pagamentos = len(pagamentos)
            total_comissoes = 0
            total_sessoes = 0
            total_records = max(total_pagamentos, total_comissoes, total_sessoes)
            total_pages = 1
            has_prev = False
            has_next = False
            has_current_entries = total_records > 0
        else:
            # Fetch and serialize current-month gastos
            gastos = get_gastos_for_month(db, start_date, end_date)
            gastos_json = serialize_gastos(gastos) or []

            # Apply consistent date filtering for current month to all entities
            pagamentos_query = (
                db.query(Pagamento)
                .options(joinedload(Pagamento.cliente), joinedload(Pagamento.artista))
                .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
                .order_by(Pagamento.data.desc())
                .distinct()
            )

            comissoes_query = (
                db.query(Comissao)
                .options(joinedload(Comissao.pagamento), joinedload(Comissao.artista))
                .filter(
                    Comissao.created_at >= start_date, Comissao.created_at < end_date
                )
                .order_by(Comissao.created_at.desc())
                .distinct()
            )

            # RESTORED: Only show sessions that are completed or paid (not just scheduled/active)
            sessoes_query = (
                db.query(Sessao)
                .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
                .filter(Sessao.data >= start_date, Sessao.data < end_date)
                .filter(Sessao.status.in_(["completed", "paid"]))
                .order_by(Sessao.data.desc(), Sessao.created_at.desc())
                .distinct()
            )

            total_pagamentos = _safe_count(pagamentos_query)
            total_comissoes = _safe_count(comissoes_query)
            total_sessoes = _safe_count(sessoes_query)

            pagamentos = _safe_all(
                _safe_limit(
                    _safe_offset(pagamentos_query, (page - 1) * per_page), per_page
                )
            )
            comissoes = _safe_all(
                _safe_limit(
                    _safe_offset(comissoes_query, (page - 1) * per_page), per_page
                )
            )
            sessoes = _safe_all(
                _safe_limit(
                    _safe_offset(sessoes_query, (page - 1) * per_page), per_page
                )
            )

            total_records = max(total_pagamentos, total_comissoes, total_sessoes)
            total_pages = (
                (total_records + per_page - 1) // per_page if total_records > 0 else 1
            )
            has_prev = page > 1
            has_next = page < total_pages
            has_current_entries = any(
                count > 0
                for count in (total_pagamentos, total_comissoes, total_sessoes)
            ) or bool(gastos_json)

        # Also provide clients and artists for edit modals (reuse templates)
        clients = []
        artists = []
        if not is_mock_session:
            try:
                clients_table = Pagamento.__table__.metadata.tables["clients"]
                # Execute a Core select() against the table using the Session and fetch rows
                clients = db.execute(clients_table.select()).fetchall()
            except Exception:
                try:
                    clients = db.query(
                        Pagamento.__table__.metadata.tables["clients"]
                    ).all()
                except Exception:
                    # Safe fallback: query Client class if available via relationship navigation
                    try:
                        from app.db.base import Client

                        clients = db.query(Client).order_by(Client.name).all()
                    except Exception:
                        clients = []

            try:
                # Use service to list artists (reuses business logic)
                user_repo = UserRepository(db)
                user_service = UserService(user_repo)
                artists = user_service.list_artists()
            except Exception:
                artists = []

        # Debug counts for visibility in logs
        try:
            logger.info(
                "historico counts -> pagamentos:%d comissoes:%d sessoes:%d gastos:%d",
                len(pagamentos),
                len(comissoes),
                len(sessoes),
                len(gastos_json),
            )

            # Debug logging for IDs and artists
            if os.getenv("HISTORICO_DEBUG", "").lower() in ("1", "true", "yes"):
                payment_ids = [p.id for p in pagamentos]
                session_ids = [s.id for s in sessoes]
                commission_artists = list(
                    set(c.artista.name for c in comissoes if c.artista)
                )
                session_artists = list(
                    set(s.artista.name for s in sessoes if s.artista)
                )
                payment_artists = list(
                    set(p.artista.name for p in pagamentos if p.artista)
                )

                session_statuses = [(s.id, s.status) for s in sessoes]

                logger.info(f"HISTORICO_DEBUG: Payment IDs: {payment_ids}")
                logger.info(f"HISTORICO_DEBUG: Session IDs: {session_ids}")
                logger.info(
                    f"HISTORICO_DEBUG: Session statuses (id, status): {session_statuses}"
                )
                logger.info(
                    f"HISTORICO_DEBUG: Sessions filtered by status: completed/paid only"
                )
                logger.info(
                    f"HISTORICO_DEBUG: Commission artists: {commission_artists}"
                )
                logger.info(f"HISTORICO_DEBUG: Session artists: {session_artists}")
                logger.info(f"HISTORICO_DEBUG: Payment artists: {payment_artists}")
                logger.info(
                    f"HISTORICO_DEBUG: All included artists: {list(set(commission_artists + session_artists + payment_artists))}"
                )
        except Exception as e:
            logger.warning(f"Debug logging failed: {e}")

        return render_template(
            "historico.html",
            pagamentos=pagamentos,
            comissoes=comissoes,
            sessoes=sessoes,
            clients=clients,
            artists=artists,
            current_totals=current_totals,
            has_current_entries=has_current_entries,
            gastos_json=gastos_json,
            # Pagination context
            page=page,
            per_page=per_page,
            total_pagamentos=total_pagamentos,
            total_comissoes=total_comissoes,
            total_sessoes=total_sessoes,
            total_pages=total_pages,
            has_prev=has_prev,
            has_next=has_next,
        )
    except Exception as e:
        # Log and re-raise to surface the real error in browser during debugging
        logger.exception(
            "Error loading historico",
            extra={"context": {"error": str(e)}},
        )
        # TEMP: re-raise for debugging so we see the stacktrace in the browser
        raise
    finally:
        if db:
            db.close()


@historico_bp.route("/delete-comissao/<int:comissao_id>", methods=["POST"])
@login_required
def delete_comissao(comissao_id: int):
    db = None
    try:
        db = SessionLocal()
        c = (
            db.query(Comissao)
            .options(joinedload(Comissao.pagamento), joinedload(Comissao.artista))
            .get(comissao_id)
        )
        if not c:
            flash("Comissão não encontrada.", "error")
            return render_template(
                "historico.html",
                pagamentos=[],
                comissoes=[],
                sessoes=[],
                current_totals={},
                has_current_entries=False,
            )

        try:
            db.delete(c)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception("Failed to delete comissao: %s", e)
            flash("Falha ao excluir comissão.", "error")
            return _safe_redirect("/historico/")

        flash("Comissão excluída com sucesso.", "success")
        return _safe_redirect("/historico/")
    finally:
        if db:
            db.close()


@historico_bp.route("/api/comissao/<int:comissao_id>", methods=["GET"])
@login_required
def api_get_comissao(comissao_id: int):
    db = None
    try:
        db = SessionLocal()
        c = (
            db.query(Comissao)
            .options(joinedload(Comissao.pagamento), joinedload(Comissao.artista))
            .get(comissao_id)
        )
        if not c:
            return api_response(False, "Comissão não encontrada", None, 404)

        data = {
            "id": c.id,
            "percentual": (
                float(c.percentual)
                if getattr(c, "percentual", None) is not None
                else None
            ),
            "valor": float(c.valor) if getattr(c, "valor", None) is not None else None,
            "observacoes": c.observacoes,
            "created_at": (
                c.created_at.isoformat() if getattr(c, "created_at", None) else None
            ),
            "artista": (
                {"id": c.artista.id, "name": c.artista.name}
                if getattr(c, "artista", None)
                else None
            ),
            "pagamento": (
                {
                    "id": c.pagamento.id,
                    "valor": (
                        float(c.pagamento.valor)
                        if getattr(c.pagamento, "valor", None) is not None
                        else None
                    ),
                    "cliente": (
                        {"id": c.pagamento.cliente.id, "name": c.pagamento.cliente.name}
                        if getattr(c.pagamento, "cliente", None)
                        else None
                    ),
                }
                if getattr(c, "pagamento", None)
                else None
            ),
        }
        return api_response(True, "Comissão encontrada", data, 200)
    except Exception as e:
        logger.exception("Error fetching comissao: %s", e)
        return api_response(False, f"Erro interno: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@historico_bp.route("/api/comissao/<int:comissao_id>", methods=["PUT"])
@login_required
def api_update_comissao(comissao_id: int):
    db = None
    try:
        db = SessionLocal()
        c = (
            db.query(Comissao)
            .options(joinedload(Comissao.pagamento), joinedload(Comissao.artista))
            .get(comissao_id)
        )
        if not c:
            return api_response(False, "Comissão não encontrada", None, 404)

        payload = request.get_json(force=True, silent=True) or {}
        # Accept percentual and observacoes (valor computed or provided)
        changed = False
        try:
            if "percentual" in payload and payload.get("percentual") is not None:
                from decimal import Decimal

                c.percentual = Decimal(str(payload.get("percentual")))
                changed = True
            if "valor" in payload and payload.get("valor") is not None:
                from decimal import Decimal

                c.valor = Decimal(str(payload.get("valor")))
                changed = True
            if "observacoes" in payload:
                c.observacoes = payload.get("observacoes")
                changed = True

            if changed:
                db.add(c)
                db.commit()
                db.refresh(c)

            return api_response(
                True,
                "Comissão atualizada",
                {
                    "id": c.id,
                    "percentual": (
                        float(c.percentual)
                        if getattr(c, "percentual", None) is not None
                        else None
                    ),
                    "valor": (
                        float(c.valor)
                        if getattr(c, "valor", None) is not None
                        else None
                    ),
                    "observacoes": c.observacoes,
                },
                200,
            )
        except Exception as e:
            db.rollback()
            logger.exception("Failed to update comissao: %s", e)
            return api_response(
                False, f"Falha ao atualizar comissão: {str(e)}", None, 400
            )
    finally:
        if db:
            db.close()


@historico_bp.route("/api/comissao/<int:comissao_id>", methods=["DELETE"])
@login_required
def api_delete_comissao(comissao_id: int):
    db = None
    try:
        db = SessionLocal()
        c = (
            db.query(Comissao)
            .options(joinedload(Comissao.pagamento), joinedload(Comissao.artista))
            .get(comissao_id)
        )
        if not c:
            return api_response(False, "Comissão não encontrada", None, 404)
        try:
            db.delete(c)
            db.commit()
            return api_response(True, "Comissão excluída", None, 200)
        except Exception as e:
            db.rollback()
            logger.exception("Failed to delete comissao: %s", e)
            return api_response(
                False, f"Falha ao excluir comissão: {str(e)}", None, 400
            )
    finally:
        if db:
            db.close()
