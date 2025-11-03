"""
Extrato controller - handles extrato API endpoints and web pages.
"""

import json
import logging

from app.db.base import Extrato
from app.db.session import SessionLocal
from app.services.extrato_generation import (
    generate_extrato as _service_generate_extrato,
)
from flask import Blueprint, jsonify, request
from flask_login import login_required


def generate_extrato(mes: int, ano: int, force: bool = False):
    """Compatibility wrapper that delegates to the extrato generation service."""
    return _service_generate_extrato(mes, ano, force=force)


logger = logging.getLogger(__name__)

extrato_bp = Blueprint("extrato", __name__, url_prefix="/extrato")


@extrato_bp.route("/api", methods=["GET"])
@login_required
def api_get_extrato():
    """Get extrato data for a specific month/year.

    Query parameters:
    - mes: Month (01-12)
    - ano: Year (YYYY)

    Returns JSON with extrato data.
    """
    mes = request.args.get("mes")
    ano = request.args.get("ano")

    if not mes or not ano:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Parâmetros 'mes' e 'ano' são obrigatórios",
                }
            ),
            400,
        )

    try:
        mes = int(mes)
        ano = int(ano)

        if mes < 1 or mes > 12:
            return (
                jsonify({"success": False, "message": "Mês deve estar entre 1 e 12"}),
                400,
            )

        if ano < 2000 or ano > 2100:
            return (
                jsonify(
                    {"success": False, "message": "Ano deve estar entre 2000 e 2100"}
                ),
                400,
            )

    except ValueError:
        return (
            jsonify(
                {"success": False, "message": "Mês e ano devem ser números válidos"}
            ),
            400,
        )

    db = SessionLocal()
    try:
        # Query the extrato for the specified month/year
        extrato = (
            db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
        )

        if not extrato:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Extrato não encontrado para {mes:02d}/{ano}",
                    }
                ),
                404,
            )

        # Parse JSON data from the extrato - safely extract actual values
        try:
            pagamentos_raw = getattr(extrato, "pagamentos", None)
            sessoes_raw = getattr(extrato, "sessoes", None)
            comissoes_raw = getattr(extrato, "comissoes", None)
            gastos_raw = getattr(extrato, "gastos", None)
            totais_raw = getattr(extrato, "totais", None)

            pagamentos = json.loads(pagamentos_raw) if pagamentos_raw else []
            sessoes = json.loads(sessoes_raw) if sessoes_raw else []
            comissoes = json.loads(comissoes_raw) if comissoes_raw else []
            gastos = json.loads(gastos_raw) if gastos_raw else []
            totais = json.loads(totais_raw) if totais_raw else {}

        except (json.JSONDecodeError, AttributeError) as json_error:
            logger.error(f"Error parsing JSON data from extrato: {str(json_error)}")
            return (
                jsonify(
                    {"success": False, "message": "Erro ao processar dados do extrato"}
                ),
                500,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Extrato encontrado para {mes:02d}/{ano}",
                    "data": {
                        "mes": mes,
                        "ano": ano,
                        "pagamentos": pagamentos,
                        "sessoes": sessoes,
                        "comissoes": comissoes,
                        "gastos": gastos,
                        "totais": totais,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in api_get_extrato: {str(e)}")
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500

    finally:
        db.close()
