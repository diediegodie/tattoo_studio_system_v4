from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging

from app.db.session import SessionLocal
from app.db.base import Gasto
from app.services.gastos_service import get_gastos_for_month, serialize_gastos
from app.core.api_utils import api_response

logger = logging.getLogger(__name__)


gastos_bp = Blueprint("gastos", __name__, url_prefix="/gastos")


@gastos_bp.route("/", methods=["GET"])
@login_required
def gastos_home():
    db = None
    try:
        db = SessionLocal()
        # Compute start and end of current month
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1)
        else:
            end_date = datetime(today.year, today.month + 1, 1)

        gastos = get_gastos_for_month(db, start_date, end_date)
        gastos_json = serialize_gastos(gastos)

        return render_template("gastos.html", gastos_json=gastos_json)
    except Exception as e:
        logger.exception("Error loading gastos: %s", e)
        flash("Erro ao carregar gastos.", "error")
        return render_template("gastos.html", gastos_json=[])
    finally:
        if db:
            db.close()


@gastos_bp.route("/create", methods=["POST"])
@login_required
def create_gasto():
    db = None
    try:
        db = SessionLocal()

        # Accept form or JSON
        if request.is_json:
            payload = request.get_json(silent=True) or {}
        else:
            payload = request.form.to_dict()

        logger.info("Received payload for gasto creation: %s", payload)

        # Extract fields
        data_str = payload.get("data")
        valor_str = payload.get("valor")
        descricao = (payload.get("descricao") or "").strip()
        forma_pagamento = (payload.get("forma_pagamento") or "").strip()

        # Validate
        errors = []
        try:
            if not data_str:
                errors.append("Data é obrigatória.")
                data_val = None
            else:
                data_val = datetime.strptime(data_str, "%Y-%m-%d").date()
        except Exception:
            errors.append("Data inválida. Use o formato AAAA-MM-DD.")
            data_val = None

        try:
            valor_dec = Decimal(str(valor_str)) if valor_str is not None else None
            if valor_dec is None or valor_dec <= Decimal("0"):
                errors.append("Valor deve ser maior que zero.")
        except (InvalidOperation, TypeError):
            errors.append("Valor inválido.")
            valor_dec = None

        if not descricao:
            errors.append("Descrição é obrigatória.")

        if not forma_pagamento:
            errors.append("Forma de pagamento é obrigatória.")

        logger.info(
            "Validation results: errors=%s, data_val=%s, valor_dec=%s, descricao='%s', forma_pagamento='%s'",
            errors,
            data_val,
            valor_dec,
            descricao,
            forma_pagamento,
        )

        if errors:
            if request.is_json:
                return api_response(False, "; ".join(errors), None, 400)
            for err in errors:
                flash(err, "error")
            return redirect(url_for("gastos.gastos_home"))

        # Ensure current_user is set
        if current_user is None or current_user.id is None:
            logger.error("current_user is None or has no id")
            raise ValueError("User not authenticated")

        logger.info("Creating Gasto with created_by=%s", current_user.id)

        # Create Gasto
        gasto = Gasto(
            data=data_val,
            valor=valor_dec,
            descricao=descricao,
            forma_pagamento=forma_pagamento,
            created_by=current_user.id,
        )

        logger.info("Gasto object created: %s", gasto)

        db.add(gasto)
        logger.info("About to commit gasto to database")
        db.commit()
        logger.info("Gasto committed successfully, refreshing...")
        db.refresh(gasto)
        logger.info("Gasto refreshed: id=%s", gasto.id)

        if request.is_json:
            return api_response(
                True,
                "Gasto registrado com sucesso.",
                {"gasto": serialize_gastos([gasto])[0]},
                201,
            )

        flash("Gasto registrado com sucesso.", "success")
        return redirect(url_for("gastos.gastos_home"))

    except Exception as e:
        if db:
            db.rollback()
        logger.exception("Failed to create gasto: %s", e)
        if request.is_json:
            return api_response(False, f"Erro ao registrar gasto: {str(e)}", None, 500)
        flash("Erro ao registrar gasto.", "error")
        return redirect(url_for("gastos.gastos_home"))
    finally:
        if db:
            db.close()
