"""
Google Calendar Blueprint - Calendar Authorization
Handles Google Calendar token authorization separately from user login.
"""

import logging
from flask import flash, redirect, url_for
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import make_google_blueprint
from flask_login import current_user

logger = logging.getLogger(__name__)


def create_google_calendar_blueprint(
    client_id, client_secret, redirect_url=None, storage=None
):
    """
    Create Google OAuth blueprint for calendar authorization.

    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_url: Optional custom redirect URL (defaults to http://127.0.0.1:5000/auth/calendar/google_calendar/authorized)
        storage: Optional Flask-Dance storage backend (CustomOAuthStorage or SQLAlchemyStorage)

    Returns:
        Flask-Dance Google blueprint configured for calendar access
    """
    # Import provider constant
    from app.config.oauth_provider import PROVIDER_GOOGLE_CALENDAR

    if not redirect_url:
        # Use absolute URL for local development
        # Flask-Dance creates /google routes, and we register with prefix /auth/calendar/google_calendar
        redirect_url = (
            "http://127.0.0.1:5000/auth/calendar/google_calendar/google/authorized"
        )

    # Create blueprint with calendar-only scopes
    blueprint = make_google_blueprint(
        client_id=client_id,
        client_secret=client_secret,
        scope=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        redirect_url=redirect_url,
        redirect_to="calendar_controller.calendar_view",  # Where to redirect after authorization
        offline=True,  # Request refresh token for calendar access
        reprompt_consent=True,  # Force consent to ensure refresh tokens
        storage=storage,  # ✅ Pass storage during blueprint creation (CRITICAL FIX)
    )

    # Set blueprint name to match our provider constant
    blueprint.name = PROVIDER_GOOGLE_CALENDAR

    # Note: Storage is now passed during blueprint creation, not assigned afterwards
    # This ensures Flask-Dance uses our CustomOAuthStorage during OAuth callbacks

    # Register signal handler for OAuth callback
    @oauth_authorized.connect_via(blueprint)
    def google_calendar_callback(blueprint_instance, token):
        """
        Handle successful Google Calendar OAuth callback.
        Confirms token persistence and logs authorization.
        """
        logger.debug(
            "Google Calendar OAuth callback triggered",
            extra={
                "context": {
                    "provider": blueprint_instance.name,
                    "has_token": bool(token),
                    "token_keys": list(token.keys()) if isinstance(token, dict) else [],
                    "user_id": (
                        current_user.id if current_user.is_authenticated else None
                    ),
                }
            },
        )

        if not token:
            flash("Falha ao autorizar Google Calendar.", category="error")
            logger.warning(
                "Google Calendar authorization failed - no token received",
                extra={"context": {"provider": PROVIDER_GOOGLE_CALENDAR}},
            )
            return redirect(url_for("calendar.calendar_page"))

        if not current_user.is_authenticated:
            flash(
                "Você precisa estar logado para conectar o Google Calendar.",
                category="error",
            )
            logger.warning(
                "Google Calendar authorization attempted without logged-in user",
                extra={"context": {"provider": PROVIDER_GOOGLE_CALENDAR}},
            )
            return redirect(url_for("login_page"))

        # ✅ CRITICAL FIX: Manually store token using CustomOAuthStorage
        # Flask-Dance's automatic storage is not working, so we explicitly call storage.set()
        try:
            blueprint_instance.storage.set(
                blueprint=blueprint_instance,
                token=token,
                user=current_user,
                user_id=current_user.id,
            )
            logger.info(
                "✅ OAuth token stored successfully via manual storage.set() call",
                extra={
                    "context": {
                        "provider": PROVIDER_GOOGLE_CALENDAR,
                        "user_id": current_user.id,
                        "token_keys": (
                            list(token.keys()) if isinstance(token, dict) else []
                        ),
                        "has_access_token": (
                            "access_token" in token
                            if isinstance(token, dict)
                            else False
                        ),
                        "has_refresh_token": (
                            "refresh_token" in token
                            if isinstance(token, dict)
                            else False
                        ),
                    }
                },
            )
        except Exception as e:
            logger.error(
                "❌ Failed to store OAuth token",
                extra={
                    "context": {
                        "provider": PROVIDER_GOOGLE_CALENDAR,
                        "user_id": current_user.id,
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            flash("Erro ao salvar token do Google Calendar.", category="error")
            return redirect(url_for("calendar.calendar_page"))

        # Get provider_user_id from Google for logging
        try:
            resp = blueprint_instance.session.get("/oauth2/v2/userinfo")
            if resp.ok:
                google_info = resp.json()
                google_user_id = str(google_info.get("id", "unknown"))
                logger.info(
                    "Google Calendar authorization completed",
                    extra={
                        "context": {
                            "provider": PROVIDER_GOOGLE_CALENDAR,
                            "user_id": current_user.id,
                            "google_user_id": google_user_id,
                        }
                    },
                )
            else:
                logger.warning(
                    "Could not fetch Google user info after calendar authorization",
                    extra={
                        "context": {
                            "provider": PROVIDER_GOOGLE_CALENDAR,
                            "status_code": resp.status_code,
                        }
                    },
                )
        except Exception as e:
            logger.warning(
                "Error fetching Google user info for calendar authorization",
                extra={
                    "context": {
                        "provider": PROVIDER_GOOGLE_CALENDAR,
                        "error": str(e),
                    }
                },
            )

        flash("Google Calendar conectado com sucesso!", category="success")

        # Redirect back to calendar page
        return redirect(url_for("calendar.calendar_page"))

    logger.info(
        "Google Calendar blueprint created",
        extra={
            "context": {
                "provider": PROVIDER_GOOGLE_CALENDAR,
                "scopes": [
                    "https://www.googleapis.com/auth/calendar.readonly",
                    "https://www.googleapis.com/auth/calendar.events",
                ],
            }
        },
    )

    return blueprint
