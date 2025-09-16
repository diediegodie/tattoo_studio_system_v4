"""
Sessions Controller - SOLID-compliant HTTP route handlers for session operations.

Following SOLID principles:
- Single Responsibility: Only handles HTTP request/response for session operations
- Dependency Inversion: Uses services instead of direct database access
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from werkzeug.wrappers.response import Response
from flask_login import login_required, current_user
from typing import Union
import logging

from app.db.base import Client, Sessao
from decimal import Decimal
from datetime import datetime, date, time
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.db.base import Client, Sessao
from decimal import Decimal
from datetime import datetime, date, time
from sqlalchemy.exc import IntegrityError

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint FIRST (before imports to avoid circular imports)
sessoes_bp = Blueprint("sessoes", __name__, url_prefix="/sessoes")

# Import from split modules
from app.controllers.sessoes_helpers import api_response, _get_user_service
from app.controllers.sessoes_routes import *
from app.controllers.sessoes_api import *
from app.controllers.sessoes_legacy import *
