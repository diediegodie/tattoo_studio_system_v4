import asyncio
import inspect
import logging

from app.db.session import SessionLocal
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from flask import redirect, render_template, url_for

# Configure logger
logger = logging.getLogger(__name__)


def _safe_render(template_name: str, **context):
    """Render template but fall back to empty string when template not found (useful in unit tests)."""
    try:
        return render_template(template_name, **context)
    except Exception:
        return ""


def _safe_redirect(endpoint_or_path: str):
    """Redirect using a path or endpoint; if endpoint building fails, assume it's a path and redirect directly."""
    try:
        # If it looks like an endpoint (contains a dot), try url_for
        if "." in endpoint_or_path:
            return redirect(url_for(endpoint_or_path))
        # Otherwise try to treat as a path
        return redirect(endpoint_or_path)
    except Exception:
        # Fallback to direct path redirect
        return redirect(endpoint_or_path)


def _get_user_service():
    """Dependency injection factory for UserService."""
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        return UserService(user_repo)
    finally:
        db.close()


def _maybe_await(value):
    """If value is a coroutine, await it; otherwise return as-is."""
    if inspect.iscoroutine(value):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't use await
                # This is common in Flask applications
                return value
            else:
                return loop.run_until_complete(value)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(value)
    return value
