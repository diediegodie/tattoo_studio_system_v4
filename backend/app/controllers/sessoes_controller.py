"""
Sessions Controller - SOLID-compliant HTTP route handlers for session operations.

Following SOLID principles:
- Single Responsibility: Only handles HTTP request/response for session operations
- Dependency Inversion: Uses services instead of direct database access
"""

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Union

from app.db.base import Client, Sessao
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.wrappers.response import Response

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint FIRST (before imports to avoid circular imports)
sessoes_bp = Blueprint("sessoes", __name__, url_prefix="/sessoes")

from app.controllers.sessoes_api import *

# Import from split modules
from app.controllers.sessoes_helpers import _get_user_service, api_response
from app.controllers.sessoes_routes import *
