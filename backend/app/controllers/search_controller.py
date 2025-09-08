from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required
from app.services.search_service import SearchService
from app.db.session import SessionLocal

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
        return jsonify({"error": 'Query parameter "q" is required'}), 400

    # Limit query length for security
    if len(query) > 100:
        return jsonify({"error": "Query too long (max 100 characters)"}), 400

    db = SessionLocal()
    try:
        service = SearchService(db)
        results = service.search(query)

        return jsonify(
            {
                "query": query,
                "results": results,
                "total_results": sum(len(v) for v in results.values()),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500
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
            query="",
            results={},
            total_results=0,
            error='Query parameter "q" is required',
        )

    # Limit query length for security
    if len(query) > 100:
        return render_template(
            "search_results.html",
            query=query,
            results={},
            total_results=0,
            error="Query too long (max 100 characters)",
        )

    db = SessionLocal()
    try:
        service = SearchService(db)
        results = service.search(query)

        total_results = sum(len(v) for v in results.values())

        return render_template(
            "search_results.html",
            query=query,
            results=results,
            total_results=total_results,
            error=None,
        )
    except Exception as e:
        return render_template(
            "search_results.html",
            query=query,
            results={},
            total_results=0,
            error=f"Search failed: {str(e)}",
        )
    finally:
        db.close()
