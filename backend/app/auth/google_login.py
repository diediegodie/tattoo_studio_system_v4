"""
Google Login Blueprint - User Authentication
Handles user login via Google OAuth with openid, email, and profile scopes.
"""

import logging
from flask import flash, redirect, url_for, current_app
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import make_google_blueprint
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_login import login_user, current_user

logger = logging.getLogger(__name__)


def create_google_login_blueprint(
    client_id, client_secret, redirect_url=None, storage=None
):
    """
    Create Google OAuth blueprint for user login.

    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_url: Optional custom redirect URL (defaults to http://127.0.0.1:5000/auth/google_login/authorized)
        storage: Optional Flask-Dance storage backend (CustomOAuthStorage or SQLAlchemyStorage)

    Returns:
        Flask-Dance Google blueprint configured for login
    """
    # Import provider constant
    from app.config.oauth_provider import PROVIDER_GOOGLE_LOGIN

    if not redirect_url:
        # Use absolute URL for local development
        # Flask-Dance creates /google routes, and we register with prefix /auth/google_login
        redirect_url = "http://127.0.0.1:5000/auth/google_login/google/authorized"

    # Create blueprint with login-only scopes
    blueprint = make_google_blueprint(
        client_id=client_id,
        client_secret=client_secret,
        scope=["openid", "email", "profile"],
        redirect_url=redirect_url,
        redirect_to="index",  # Where to redirect after successful login
        offline=False,  # No refresh token needed for login
        reprompt_consent=False,  # Only prompt once for login
        storage=storage,  # ✅ Pass storage during blueprint creation (CRITICAL FIX)
    )

    # Set blueprint name to match our provider constant
    blueprint.name = PROVIDER_GOOGLE_LOGIN

    # Note: Storage is now passed during blueprint creation, not assigned afterwards
    # This ensures Flask-Dance uses our CustomOAuthStorage during OAuth callbacks

    # Register signal handler for OAuth callback
    @oauth_authorized.connect_via(blueprint)
    def google_login_callback(blueprint_instance, token):
        """
        Handle successful Google login OAuth callback.
        Creates or updates user, then logs them in.
        """
        logger.debug(
            "Google Login OAuth callback triggered",
            extra={
                "context": {
                    "provider": blueprint_instance.name,
                    "has_token": bool(token),
                    "token_keys": list(token.keys()) if isinstance(token, dict) else [],
                }
            },
        )

        if not token:
            flash("Falha ao fazer login com Google.", category="error")
            return redirect(url_for("login_page"))

        # Get user info from Google
        try:
            resp = blueprint_instance.session.get("/oauth2/v2/userinfo")
            if not resp.ok:
                flash(
                    "Falha ao buscar informações do usuário do Google.",
                    category="error",
                )
                logger.error(
                    "Failed to fetch Google user info",
                    extra={"context": {"status_code": resp.status_code}},
                )
                return redirect(url_for("login_page"))

            google_info = resp.json()
            google_user_id = str(google_info["id"])
            google_email = google_info.get("email", "")

            logger.info(
                "Google user authenticated for login",
                extra={
                    "context": {
                        "provider": PROVIDER_GOOGLE_LOGIN,
                        "google_user_id": google_user_id,
                        "email": google_email,
                    }
                },
            )

            # Create or update user in database
            from app.db.session import SessionLocal
            from app.repositories.user_repo import UserRepository
            from app.services.user_service import UserService
            from app.core.security import create_user_token

            db = SessionLocal()
            try:
                repo = UserRepository(db)
                service = UserService(repo)

                # Create or update user from Google info
                service.create_or_update_from_google(google_info)

                # Get database user for Flask-Login
                db_user = repo.get_db_by_google_id(google_user_id)
                if not db_user:
                    # Fallback: try by email
                    db_user = repo.get_db_by_email(google_email)

                if not db_user:
                    flash(
                        "Erro ao processar login: usuário não encontrado.",
                        category="error",
                    )
                    logger.error(
                        "User not found after Google login",
                        extra={
                            "context": {
                                "google_user_id": google_user_id,
                                "email": google_email,
                            }
                        },
                    )
                    return redirect(url_for("login_page"))

                logger.info(
                    "User logged in successfully",
                    extra={
                        "context": {
                            "user_id": db_user.id,
                            "email": db_user.email,
                            "provider": PROVIDER_GOOGLE_LOGIN,
                        }
                    },
                )

                # Create JWT token for API access
                jwt_token = create_user_token(
                    getattr(db_user, "id"), getattr(db_user, "email")
                )

                # Log user in with Flask-Login
                login_user(db_user)

                # ✅ CRITICAL FIX: Manually store token using CustomOAuthStorage
                # Flask-Dance's automatic storage is not working, so we explicitly call storage.set()
                try:
                    blueprint_instance.storage.set(
                        blueprint=blueprint_instance,
                        token=token,
                        user=db_user,
                        user_id=db_user.id,
                    )
                    logger.info(
                        "✅ OAuth token stored successfully via manual storage.set() call",
                        extra={
                            "context": {
                                "provider": PROVIDER_GOOGLE_LOGIN,
                                "user_id": db_user.id,
                            }
                        },
                    )
                except Exception as e:
                    logger.error(
                        "❌ Failed to store OAuth token",
                        extra={
                            "context": {
                                "provider": PROVIDER_GOOGLE_LOGIN,
                                "user_id": db_user.id,
                                "error": str(e),
                            }
                        },
                        exc_info=True,
                    )
                    # Don't fail the login just because token storage failed

                flash(f"Bem-vindo, {db_user.name}!", category="success")

                # Redirect to index page
                response = redirect(url_for("index"))

                # Set JWT cookie
                secure_flag = current_app.config.get("SESSION_COOKIE_SECURE", False)
                response.set_cookie(
                    "access_token",
                    jwt_token,
                    max_age=604800,  # 7 days
                    httponly=True,
                    secure=secure_flag,
                    samesite="Lax",
                )

                logger.info(
                    "Google login completed successfully",
                    extra={
                        "context": {
                            "user_id": db_user.id,
                            "provider": PROVIDER_GOOGLE_LOGIN,
                        }
                    },
                )

                return response

            except Exception as e:
                logger.exception(
                    "Error during Google login callback",
                    extra={
                        "context": {"error": str(e), "provider": PROVIDER_GOOGLE_LOGIN}
                    },
                )
                db.rollback()
                flash("Erro interno durante o login.", category="error")
                return redirect(url_for("login_page"))
            finally:
                db.close()

        except Exception as e:
            logger.exception(
                "Error processing Google login",
                extra={"context": {"error": str(e), "provider": PROVIDER_GOOGLE_LOGIN}},
            )
            flash("Erro ao processar login com Google.", category="error")
            return redirect(url_for("login_page"))

    logger.info(
        "Google Login blueprint created",
        extra={
            "context": {
                "provider": PROVIDER_GOOGLE_LOGIN,
                "scopes": ["openid", "email", "profile"],
            }
        },
    )

    return blueprint
