import logging
from datetime import datetime
from decimal import Decimal
from typing import Tuple, Union

from app.controllers.financeiro_helpers import (
    _get_user_service,
    _maybe_await,
    _safe_redirect,
    _safe_render,
)
from app.db.base import Client, Comissao, Pagamento, Sessao
from app.db.session import SessionLocal
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from werkzeug.wrappers import Response

# Configure logger
logger = logging.getLogger(__name__)

# Import the blueprint from financeiro_controller instead of creating a new one
from app.controllers.financeiro_controller import financeiro_bp
