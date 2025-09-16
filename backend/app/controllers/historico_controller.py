from flask import Blueprint, render_template, flash, jsonify, request
from flask_login import login_required, current_user
from app.db.session import SessionLocal
from app.db.base import Pagamento, Comissao, Sessao, Gasto
from sqlalchemy.orm import joinedload
import logging
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.core.api_utils import api_response
from app.services.gastos_service import get_gastos_for_month, serialize_gastos

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
        from datetime import datetime

        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1)
        else:
            end_date = datetime(today.year, today.month + 1, 1)

        has_current_entries = (
            db.query(Pagamento)
            .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
            .count()
            > 0
            or db.query(Comissao)
            .filter(Comissao.created_at >= start_date, Comissao.created_at < end_date)
            .count()
            > 0
            or db.query(Sessao)
            .filter(Sessao.data >= start_date, Sessao.data < end_date)
            .count()
            > 0
            or db.query(Gasto)
            .filter(Gasto.data >= start_date, Gasto.data < end_date)
            .count()
            > 0
        )

        # Fetch and serialize current-month gastos
        gastos = get_gastos_for_month(db, start_date, end_date)
        gastos_json = serialize_gastos(gastos)

        pagamentos = (
            db.query(Pagamento)
            .options(joinedload(Pagamento.cliente), joinedload(Pagamento.artista))
            .order_by(Pagamento.data.desc())
            .all()
        )

        comissoes = (
            db.query(Comissao)
            .options(joinedload(Comissao.pagamento), joinedload(Comissao.artista))
            .order_by(Comissao.created_at.desc())
            .all()
        )

        sessoes = (
            db.query(Sessao)
            .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
            .filter(Sessao.status.in_(["completed", "paid"]))
            .order_by(Sessao.data.desc(), Sessao.hora.desc())
            .all()
        )

        # Also provide clients and artists for edit modals (reuse templates)
        try:
            clients_table = Pagamento.__table__.metadata.tables["clients"]
            # Execute a Core select() against the table using the Session and fetch rows
            clients = db.execute(clients_table.select()).fetchall()
        except Exception:
            try:
                clients = db.query(Pagamento.__table__.metadata.tables["clients"]).all()
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
        except Exception:
            pass

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
        )
    except Exception as e:
        # Log and re-raise to surface the real error in browser during debugging
        logger.exception("Error loading historico: %s", e)
        print(f"Historico error: {e}")
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
        c = db.query(Comissao).get(comissao_id)
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
        c = db.query(Comissao).get(comissao_id)
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
        c = db.query(Comissao).get(comissao_id)
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
