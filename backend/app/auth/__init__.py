"""
Authentication module for Google OAuth.

This module provides separate blueprints for:
- Google Login (user authentication)
- Google Calendar (calendar token authorization)
"""

from app.auth.google_login import create_google_login_blueprint
from app.auth.google_calendar import create_google_calendar_blueprint

__all__ = ["create_google_login_blueprint", "create_google_calendar_blueprint"]
