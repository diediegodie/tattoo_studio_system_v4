from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from typing import Union, Tuple
from werkzeug.wrappers import Response
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.base import Client, Pagamento, Comissao, Sessao
from app.controllers.financeiro_helpers import (
    _safe_render,
    _safe_redirect,
    _get_user_service,
    _maybe_await,
)

# Configure logger
logger = logging.getLogger(__name__)

# Import the blueprint from financeiro_controller instead of creating a new one
from app.controllers.financeiro_controller import financeiro_bp
