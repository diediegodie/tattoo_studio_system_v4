"""
CSRF Protection Configuration (Task 2 - Production Security)

This module provides a centralized CSRFProtect instance that can be:
1. Initialized in main.py with the Flask app
2. Imported in controllers to use @csrf.exempt decorator

Usage in controllers:
    from app.core.csrf_config import csrf

    @csrf.exempt
    @api_bp.route("/endpoint", methods=["POST"])
    def json_api_endpoint():
        # This endpoint is exempt from CSRF (uses JWT auth instead)
        pass
"""

from flask_wtf.csrf import CSRFProtect

# Global CSRF instance - initialized in create_app()
csrf = CSRFProtect()
