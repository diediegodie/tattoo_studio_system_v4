from app.db.session import SessionLocal
from app.services.search_service import SearchService
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

# Create blueprint for search routes
search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.route("", methods=["GET"])
@login_required
def search_api():
    """API endpoint for global search.

    Query parameters:
    - q: search query string
    """
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"error": 'Parâmetro de consulta "q" é obrigatório'}), 400

    # Limit query length for security
    if len(query) > 100:
        return jsonify({"error": "Consulta muito longa (máximo 100 caracteres)"}), 400

    db = SessionLocal()
    try:
        service = SearchService(db)
        results = service.search(query)

        # Calculate total excluding the unified list to avoid double counting
        category_totals = sum(
            len(v) for k, v in results.items() if k != "all_results_sorted"
        )

        return jsonify(
            {
                "query": query,
                "results": results,
                "total_results": category_totals,
                "unified_results": results.get("all_results_sorted", []),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Pesquisa falhou: {str(e)}"}), 500
    finally:
        db.close()


@search_bp.route("/results", methods=["GET"])
@login_required
def search_results_page():
    """Render search results page.

    Query parameters:
    - q: search query string
    """
    query = request.args.get("q", "").strip()

    if not query:
        return render_template(
            "search_results.html",
            search_query="",
            results={},
            total_results=0,
            error='Parâmetro de consulta "q" é obrigatório',
        )

    # Limit query length for security
    if len(query) > 100:
        return render_template(
            "search_results.html",
            search_query=query,
            results={},
            total_results=0,
            error="Consulta muito longa (máximo 100 caracteres)",
        )

    db = SessionLocal()
    try:
        service = SearchService(db)
        results = service.search(query)

        # Calculate total excluding the unified list to avoid double counting
        total_results = sum(
            len(v) for k, v in results.items() if k != "all_results_sorted"
        )

        return render_template(
            "search_results.html",
            search_query=query,
            results=results,
            total_results=total_results,
            unified_results=results.get("all_results_sorted", []),
            error=None,
        )
    except Exception as e:
        return render_template(
            "search_results.html",
            search_query=query,
            results={},
            total_results=0,
            error=f"Pesquisa falhou: {str(e)}",
        )
    finally:
        db.close()
