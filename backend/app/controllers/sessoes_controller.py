"""
Sessions Controller - SOLID-compliant HTTP route handlers for session operations.

Following SOLID principles:
- Single Responsibility: Only handles HTTP request/response for session operations
- Dependency Inversion: Uses services instead of direct database access
"""

import logging
from flask import Blueprint

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint FIRST (before imports to avoid circular imports)
sessoes_bp = Blueprint("sessoes", __name__, url_prefix="/sessoes")

from app.controllers.sessoes_helpers import (
    _get_user_service,
    api_response,
)  # noqa: E402, F401
from app.controllers.sessoes_api import *  # noqa: E402, F401, F403

# Import from split modules
from app.controllers.sessoes_routes import *  # noqa: E402, F401, F403
