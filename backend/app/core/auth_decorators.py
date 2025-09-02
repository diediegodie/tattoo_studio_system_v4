"""
Authentication helpers for this application.

This project standardizes on Flask-Login session-based authentication.
Use the decorator `@login_required` from `flask_login` on routes that require
authentication and `current_user` to access the logged-in user.

Notes:
- JWT-based decorators were removed to avoid mixed auth models. If an API
  token-based flow is needed in the future, add a dedicated adapter that
  converts token auth into a Flask-Login user before request handling.
"""

from typing import Any
from flask import g
from flask_login import current_user


def get_current_user() -> Any:
    """Return current authenticated user, preferring Flask `g.current_user` if set.

    Controllers should prefer `from flask_login import current_user` but this
    helper remains for compatibility with a small number of call sites.
    """
    # Prefer user stored in request-local g (if some adapter set it)
    if hasattr(g, "current_user") and g.current_user:
        return g.current_user

    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user

    return None
