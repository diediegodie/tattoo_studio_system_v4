"""
Reports controller for comparative analysis and chart generation.

Provides endpoints for:
- Month-over-month extrato comparisons
- Revenue trend analysis
- Commission vs revenue analysis
- Chart generation for frontend
"""

import base64
import io
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import matplotlib.pyplot as plt
from app.db.base import Extrato, ExtratoRunLog
from app.db.session import SessionLocal
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def require_admin():
    """Decorator to check if user is admin."""
    if (
        not current_user.is_authenticated
        or not hasattr(current_user, "role")
        or current_user.role != "admin"
    ):
        return (
            jsonify(
                {"success": False, "message": "Acesso de administrador necessário"}
            ),
            403,
        )
    return None


@reports_bp.route("/extrato/comparison", methods=["GET"])
@login_required
def get_extrato_comparison():
    """
    Get comparative data for extrato analysis.

    Query parameters:
    - months: Number of months to compare (default: 6, max: 12)
    - include_charts: Whether to include base64-encoded charts (default: false)
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        months = min(int(request.args.get("months", 6)), 12)
        include_charts = request.args.get("include_charts", "false").lower() == "true"

        db = SessionLocal()
        try:
            # Get current date and calculate start date
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)

            # Query extrato data
            extratos = (
                db.query(Extrato)
                .filter(
                    Extrato.created_at >= start_date, Extrato.created_at <= end_date
                )
                .order_by(Extrato.ano.desc(), Extrato.mes.desc())
                .all()
            )

            # Group by month/year
            monthly_data = {}
            for extrato in extratos:
                key = f"{extrato.ano}-{extrato.mes:02d}"
                if key not in monthly_data:
                    monthly_data[key] = {
                        "ano": extrato.ano,
                        "mes": extrato.mes,
                        "receita_total": 0,
                        "comissoes_total": 0,
                        "gastos_total": 0,
                        "lucro_total": 0,
                        "sessoes_count": 0,
                        "pagamentos_count": 0,
                    }

                # Aggregate data (assuming extrato has these fields)
                monthly_data[key]["receita_total"] += getattr(
                    extrato, "receita_total", 0
                )
                monthly_data[key]["comissoes_total"] += getattr(
                    extrato, "comissoes_total", 0
                )
                monthly_data[key]["gastos_total"] += getattr(extrato, "gastos_total", 0)
                monthly_data[key]["lucro_total"] += getattr(extrato, "lucro_total", 0)
                monthly_data[key]["sessoes_count"] += getattr(
                    extrato, "sessoes_count", 0
                )
                monthly_data[key]["pagamentos_count"] += getattr(
                    extrato, "pagamentos_count", 0
                )

            # Convert to list and sort chronologically
            comparison_data = list(monthly_data.values())
            comparison_data.sort(key=lambda x: (x["ano"], x["mes"]))

            result = {
                "success": True,
                "data": {
                    "comparison": comparison_data,
                    "summary": {
                        "total_months": len(comparison_data),
                        "avg_receita": (
                            sum(d["receita_total"] for d in comparison_data)
                            / len(comparison_data)
                            if comparison_data
                            else 0
                        ),
                        "avg_lucro": (
                            sum(d["lucro_total"] for d in comparison_data)
                            / len(comparison_data)
                            if comparison_data
                            else 0
                        ),
                        "total_receita": sum(
                            d["receita_total"] for d in comparison_data
                        ),
                        "total_lucro": sum(d["lucro_total"] for d in comparison_data),
                    },
                },
            }

            # Generate charts if requested
            if include_charts and comparison_data:
                charts = generate_comparison_charts(comparison_data)
                result["data"]["charts"] = charts

            logger.info(
                f"Admin {current_user.id} requested extrato comparison for {months} months"
            )
            return jsonify(result)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error generating extrato comparison: {str(e)}")
        return (
            jsonify(
                {"success": False, "message": "Erro ao gerar relatório de comparação"}
            ),
            500,
        )


@reports_bp.route("/extrato/trends", methods=["GET"])
@login_required
def get_revenue_trends():
    """
    Get revenue trends with percentage changes.

    Query parameters:
    - months: Number of months to analyze (default: 6, max: 12)
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        months = min(int(request.args.get("months", 6)), 12)

        db = SessionLocal()
        try:
            # Get current date and calculate start date
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)

            # Query extrato data
            extratos = (
                db.query(Extrato)
                .filter(
                    Extrato.created_at >= start_date, Extrato.created_at <= end_date
                )
                .order_by(Extrato.ano, Extrato.mes)
                .all()
            )

            # Group by month/year
            monthly_data = {}
            for extrato in extratos:
                key = f"{extrato.ano}-{extrato.mes:02d}"
                monthly_data[key] = {
                    "ano": extrato.ano,
                    "mes": extrato.mes,
                    "receita": getattr(extrato, "receita_total", 0),
                    "lucro": getattr(extrato, "lucro_total", 0),
                }

            # Calculate trends
            sorted_months = sorted(monthly_data.keys())
            trends = []

            for i, month_key in enumerate(sorted_months):
                current = monthly_data[month_key]

                if i > 0:
                    prev_key = sorted_months[i - 1]
                    prev = monthly_data[prev_key]

                    receita_change = (
                        ((current["receita"] - prev["receita"]) / prev["receita"] * 100)
                        if prev["receita"] > 0
                        else 0
                    )
                    lucro_change = (
                        ((current["lucro"] - prev["lucro"]) / prev["lucro"] * 100)
                        if prev["lucro"] > 0
                        else 0
                    )

                    trends.append(
                        {
                            "mes": current["mes"],
                            "ano": current["ano"],
                            "receita": current["receita"],
                            "lucro": current["lucro"],
                            "receita_change_pct": round(receita_change, 2),
                            "lucro_change_pct": round(lucro_change, 2),
                            "trend": (
                                "up"
                                if receita_change > 0
                                else "down" if receita_change < 0 else "stable"
                            ),
                        }
                    )
                else:
                    trends.append(
                        {
                            "mes": current["mes"],
                            "ano": current["ano"],
                            "receita": current["receita"],
                            "lucro": current["lucro"],
                            "receita_change_pct": 0,
                            "lucro_change_pct": 0,
                            "trend": "baseline",
                        }
                    )

            result = {
                "success": True,
                "data": {
                    "trends": trends,
                    "summary": {
                        "total_months": len(trends),
                        "positive_months": len(
                            [t for t in trends if t["receita_change_pct"] > 0]
                        ),
                        "negative_months": len(
                            [t for t in trends if t["receita_change_pct"] < 0]
                        ),
                        "avg_growth": (
                            sum(t["receita_change_pct"] for t in trends) / len(trends)
                            if trends
                            else 0
                        ),
                    },
                },
            }

            logger.info(
                f"Admin {current_user.id} requested revenue trends for {months} months"
            )
            return jsonify(result)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error generating revenue trends: {str(e)}")
        return (
            jsonify(
                {"success": False, "message": "Erro ao gerar tendências de receita"}
            ),
            500,
        )


def generate_comparison_charts(comparison_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Generate base64-encoded charts for comparison data.

    Args:
        comparison_data: List of monthly comparison data

    Returns:
        Dictionary with chart names as keys and base64-encoded images as values
    """
    charts = {}

    try:
        # Prepare data for plotting
        months = [f"{d['ano']}-{d['mes']:02d}" for d in comparison_data]
        receita = [d["receita_total"] for d in comparison_data]
        lucro = [d["lucro_total"] for d in comparison_data]
        gastos = [d["gastos_total"] for d in comparison_data]

        # Chart 1: Revenue vs Expenses
        plt.figure(figsize=(10, 6))
        plt.plot(months, receita, marker="o", label="Receita", color="green")
        plt.plot(months, gastos, marker="s", label="Gastos", color="red")
        plt.plot(months, lucro, marker="^", label="Lucro", color="blue")
        plt.title("Receita vs Gastos vs Lucro")
        plt.xlabel("Mês")
        plt.ylabel("Valor (R$)")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to base64
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100)
        buf.seek(0)
        charts["revenue_expenses"] = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()

        # Chart 2: Profit Margin Trend
        plt.figure(figsize=(10, 6))
        margins = [(l / r * 100) if r > 0 else 0 for l, r in zip(lucro, receita)]
        plt.plot(months, margins, marker="o", color="purple")
        plt.title("Margem de Lucro (%)")
        plt.xlabel("Mês")
        plt.ylabel("Margem (%)")
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to base64
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100)
        buf.seek(0)
        charts["profit_margin"] = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()

        return charts

    except Exception as e:
        logger.error(f"Error generating charts: {str(e)}")
        return {}


@reports_bp.route("/extrato/summary", methods=["GET"])
@login_required
def get_extrato_summary():
    """
    Get summary statistics for extrato data.

    Query parameters:
    - year: Year to analyze (default: current year)
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        year = int(request.args.get("year", datetime.now().year))

        db = SessionLocal()
        try:
            # Query extrato data for the year
            extratos = db.query(Extrato).filter(Extrato.ano == year).all()

            if not extratos:
                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "year": year,
                            "message": f"No extrato data found for {year}",
                            "summary": {
                                "total_receita": 0,
                                "total_gastos": 0,
                                "total_lucro": 0,
                                "avg_monthly_receita": 0,
                                "avg_monthly_lucro": 0,
                                "best_month": None,
                                "worst_month": None,
                            },
                        },
                    }
                )

            # Calculate summary statistics
            total_receita = sum(getattr(e, "receita_total", 0) for e in extratos)
            total_gastos = sum(getattr(e, "gastos_total", 0) for e in extratos)
            total_lucro = sum(getattr(e, "lucro_total", 0) for e in extratos)

            monthly_receitas = [getattr(e, "receita_total", 0) for e in extratos]
            monthly_lucros = [getattr(e, "lucro_total", 0) for e in extratos]

            avg_monthly_receita = total_receita / len(extratos)
            avg_monthly_lucro = total_lucro / len(extratos)

            # Find best and worst months
            best_month_idx = monthly_receitas.index(max(monthly_receitas))
            worst_month_idx = monthly_receitas.index(min(monthly_receitas))

            best_month = (
                f"{extratos[best_month_idx].ano}-{extratos[best_month_idx].mes:02d}"
            )
            worst_month = (
                f"{extratos[worst_month_idx].ano}-{extratos[worst_month_idx].mes:02d}"
            )

            result = {
                "success": True,
                "data": {
                    "year": year,
                    "summary": {
                        "total_receita": total_receita,
                        "total_gastos": total_gastos,
                        "total_lucro": total_lucro,
                        "avg_monthly_receita": avg_monthly_receita,
                        "avg_monthly_lucro": avg_monthly_lucro,
                        "best_month": best_month,
                        "worst_month": worst_month,
                        "total_months": len(extratos),
                    },
                },
            }

            logger.info(f"Admin {current_user.id} requested extrato summary for {year}")
            return jsonify(result)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error generating extrato summary: {str(e)}")
        return (
            jsonify({"success": False, "message": "Erro ao gerar relatório de resumo"}),
            500,
        )
