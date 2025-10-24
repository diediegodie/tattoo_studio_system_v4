import json
import logging
import os
import sys

from dotenv import load_dotenv

# Get logger for this module
logger = logging.getLogger(__name__)
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app,
)
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import make_google_blueprint
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import select, text

# Load environment variables conditionally
# Only load from .env when DATABASE_URL is not already defined by the environment
if not os.getenv("DATABASE_URL"):
    load_dotenv()

# Resolve effective DATABASE_URL for the app (defaults to local sqlite in dev)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Set it in the environment so db.session.get_engine() will use this value
os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL


# Helper to mask password in URLs to avoid leaking secrets in logs
def _mask_url_password(url: str) -> str:
    try:
        import re

        return re.sub(r"(://[^:/?#]+):[^@]*@", r"\1:***@", url)
    except Exception:
        return url


# Early runtime check for effective DATABASE_URL visibility in logs (Render startup)
print(">>> DEBUG: DATABASE_URL efetiva:", _mask_url_password(SQLALCHEMY_DATABASE_URL))

# Import engine after environment is finalized
from app.db.session import engine

# Create Google OAuth blueprint at module level
# Flask-Dance setup for Google OAuth at module level (must be before create_app)
# IMPORTANT: The Google Cloud Console OAuth client must list
# http://127.0.0.1:5000/auth/google/authorized as an authorized redirect URI.
# This blueprint is registered with url_prefix="/auth", so the absolute callback
# will always resolve to /auth/google/authorized locally and in Docker.
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

if not google_client_id or not google_client_secret:
    logger.warning(
        "Google OAuth credentials missing",
        extra={
            "context": {
                "has_client_id": bool(google_client_id),
                "has_client_secret": bool(google_client_secret),
            }
        },
    )

google_oauth_bp = make_google_blueprint(
    client_id=google_client_id,
    client_secret=google_client_secret,
    scope=[
        "email",
        "profile",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ],
    redirect_url="/auth/google/authorized",
    # Request offline access to get refresh tokens
    offline=True,
    # Force consent to ensure refresh tokens are provided
    reprompt_consent=True,
)
# Set unique name immediately to avoid conflicts
google_oauth_bp.name = "google_oauth_calendar"


# OAuth authorized handler - must be at module level
@oauth_authorized.connect_via(google_oauth_bp)
def google_logged_in(blueprint, token):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(
        "OAuth callback triggered", extra={"context": {"has_token": bool(token)}}
    )
    if not token:
        flash("Falha ao fazer login com Google.", category="error")
        return redirect(url_for("login_page"))

    logger.debug(
        "OAuth token received",
        extra={"context": {"token_type": str(type(token).__name__)}},
    )

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Falha ao buscar informações do usuário do Google.", category="error")
        return redirect(url_for("login_page"))

    google_info = resp.json()
    google_user_id = str(google_info["id"])
    logger.info(
        "Google user authenticated",
        extra={
            "context": {
                "google_user_id": google_user_id,
                "email": google_info.get("email"),
            }
        },
    )

    from app.core.security import create_user_token
    from app.db.session import SessionLocal
    from app.repositories.user_repo import UserRepository
    from app.services.oauth_token_service import OAuthTokenService
    from app.services.user_service import UserService

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        service = UserService(repo)
        oauth_service = OAuthTokenService()

        # Create or update user from Google info (ensures user exists in database)
        service.create_or_update_from_google(google_info)

        # Get database user for Flask-Login
        print(">>> DEBUG: Looking up user by google_id:", google_user_id)
        db_user = repo.get_db_by_google_id(google_user_id)
        if not db_user:
            # Fallback: try by email
            db_user = repo.get_db_by_email(google_info.get("email"))

        if not db_user:
            flash("Erro ao processar login: usuário não encontrado.", category="error")
            return redirect(url_for("login_page"))

        logger.debug(
            "Database user found",
            extra={"context": {"user_id": db_user.id, "email": db_user.email}},
        )

        # Save OAuth token for Google Calendar access
            # Garante que o token é sempre um dict JSON
        import json
        token_to_save = token
        if isinstance(token, str):
            try:
                token_to_save = json.loads(token)
            except Exception:
                print(f">>> DEBUG: token recebido como string não pôde ser convertido: {token}")
        print(f">>> DEBUG: tipo do token a persistir: {type(token_to_save)} | conteúdo: {token_to_save}")
        token_saved = oauth_service.store_oauth_token(
            user_id=str(db_user.id),
            provider="google",
            provider_user_id=google_user_id,
            token=token_to_save,
        )
        logger.info(
            "OAuth token stored",
            extra={
                "context": {
                    "user_id": db_user.id,
                    "provider": "google",
                    "success": token_saved,
                }
            },
        )

        # Create JWT token for API access
        jwt_token = create_user_token(getattr(db_user, "id"), getattr(db_user, "email"))

        login_user(db_user)  # Use database model for Flask-Login
        flash(f"Bem-vindo, {db_user.name}!", category="success")

        # Determine where to redirect based on the OAuth purpose
        purpose = session.pop("oauth_purpose", None)  # Get and remove the purpose flag

        if purpose == "calendar_sync":
            next_url = url_for("calendar.calendar_page")  # Go back to calendar
        else:
            next_url = url_for("index")  # Default for general login

        # After successful OAuth login, redirect user to the appropriate page
        response = redirect(next_url)

        # Use global cookie config for secure flag (production vs development)
        secure_flag = current_app.config.get("SESSION_COOKIE_SECURE", False)
        response.set_cookie(
            "access_token",
            jwt_token,
            max_age=604800,  # 7 days (increased from 24 hours)
            httponly=True,
            secure=secure_flag,
            samesite="Lax",
        )
        return response
    except Exception as e:
        # Rollback in case repository/service raised after partial changes
        logger.exception(
            "OAuth callback failed",
            extra={"context": {"error": str(e)}},
        )
        db.rollback()
        flash("Erro interno durante o login.", category="error")
        return redirect(url_for("login_page"))
    finally:
        db.close()


def test_database_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(
            "Database connection failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False


def create_app():
    # Calculate paths based on the actual file system structure
    script_dir = os.path.dirname(
        os.path.abspath(__file__)
    )  # backend/app (local) or /app/app (Docker)

    # Configure early logger for path detection (before setup_logging)
    import logging

    early_logger = logging.getLogger(__name__)
    if not early_logger.handlers:
        logging.basicConfig(level=logging.DEBUG)

    # Check if we're in Docker by looking for the /app mount point
    if script_dir.startswith("/app"):
        # Running in Docker container
        # In Docker: script is at /app/app/main.py, frontend is at /app/frontend
        template_folder = "/app/frontend/templates"
        static_folder = "/app/frontend/assets"
        environment = "docker"
    else:
        # Running locally
        # Local: script is at /path/to/project/backend/app/main.py
        # Need to go up: backend/app -> backend -> project-root -> frontend
        backend_dir = os.path.dirname(script_dir)  # backend
        project_root = os.path.dirname(backend_dir)  # project-root
        template_folder = os.path.join(project_root, "frontend", "templates")
        static_folder = os.path.join(project_root, "frontend", "assets")
        environment = "local"

    early_logger.debug(
        "Path detection complete",
        extra={
            "context": {
                "environment": environment,
                "script_dir": script_dir,
                "template_folder": template_folder,
                "static_folder": static_folder,
                "cwd": os.getcwd(),
                "template_exists": os.path.exists(template_folder),
            }
        },
    )

    if os.path.exists(template_folder):
        index_exists = os.path.exists(os.path.join(template_folder, "index.html"))
        contents = os.listdir(template_folder)[:5]
        early_logger.debug(
            "Template folder verification",
            extra={
                "context": {
                    "template_folder": template_folder,
                    "index_exists": index_exists,
                    "contents_sample": contents,
                }
            },
        )
    else:
        early_logger.warning(
            "Template folder does not exist",
            extra={"context": {"template_folder": template_folder}},
        )
        # Try to find it in alternative locations
        alt_paths = [
            "/app/frontend/templates",
            "../frontend/templates",
            "./frontend/templates",
            os.path.join(os.getcwd(), "frontend", "templates"),
        ]
        for alt_path in alt_paths:
            exists = os.path.exists(alt_path)
            early_logger.debug(
                "Checking alternative template path",
                extra={"context": {"path": alt_path, "exists": exists}},
            )

    # Determine environment
    env = os.getenv("FLASK_ENV", "development")
    is_production = env == "production"

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
    )

    # Set TESTING config from environment variable (before any other configuration)
    # This ensures test mode is properly detected even when tests create app directly
    testing_env = os.getenv("TESTING", "").lower().strip()
    if testing_env in ("true", "1", "yes"):
        app.config["TESTING"] = True

    # Add long-lived cache headers for static assets
    @app.after_request
    def add_cache_headers(response):
        p = request.path or ""
        # long cache for versioned static assets
        if p.startswith("/assets/") or p.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    # Configure structured logging (after app creation so we can register hooks)
    from app.core.logging_config import setup_logging
    import logging

    setup_logging(
        app=app,  # Pass app to register request/response hooks
        log_level=logging.INFO if is_production else logging.DEBUG,
        enable_sql_echo=not is_production,  # SQL echo in dev only
        # log_to_file controlled by LOG_TO_FILE env var (1=files, 0=stdout only)
        use_json_format=is_production,  # JSON logs in production, colored in dev
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "context": {
                "environment": env,
                "json_format": is_production,
                "sql_echo": not is_production,
            }
        },
    )

    # Sentry Integration (Task 9 - Logging and Observability)
    # Initialize Sentry for error tracking and performance monitoring
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=env,
            release=os.getenv("GIT_SHA", "unknown"),
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,  # 10% of transactions for profiling
            send_default_pii=False,  # Don't send PII by default
        )
        logger.info(
            "Sentry initialized",
            extra={
                "context": {
                    "environment": env,
                    "release": os.getenv("GIT_SHA", "unknown"),
                    "traces_sample_rate": 0.1,
                }
            },
        )
    else:
        logger.info(
            "Sentry not initialized (SENTRY_DSN not set)",
            extra={"context": {"environment": env}},
        )

    # Prometheus Metrics (Task 9 - Logging and Observability)
    # Expose /metrics endpoint for Prometheus scraping
    # MUST be initialized BEFORE limiter to avoid being rate-limited
    from prometheus_flask_exporter import PrometheusMetrics

    metrics = PrometheusMetrics(app)
    # Add custom app_info metric with version (only if not already registered)
    try:
        metrics.info(
            "app_info",
            "Application information",
            version=os.getenv("GIT_SHA", "unknown"),
            environment=env,
        )
    except ValueError as e:
        # Metric already registered (happens when create_app called multiple times)
        logger.debug(
            "app_info metric already registered",
            extra={"context": {"error": str(e)}},
        )
    logger.info(
        "Prometheus metrics initialized",
        extra={"context": {"metrics_endpoint": "/metrics"}},
    )

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # Initialize Flask-Limiter (rate limiting) with environment-aware storage
    # Import global limiter instance configured for decorators
    from app.core.limiter_config import limiter

    storage_uri = (
        "redis://redis:6379/3"
        if is_production
        else os.getenv("LIMITER_STORAGE_URI", "memory://")
    )
    # Configure storage URI via app config and bind limiter
    app.config["RATELIMIT_STORAGE_URI"] = storage_uri
    # Exempt monitoring endpoints from rate limiting (Prometheus scraper access)
    app.config["RATELIMIT_EXEMPT_PATHS"] = ["/metrics", "/health", "/pool-metrics"]
    limiter.init_app(app)

    # Disable rate limiting in test mode if RATE_LIMIT_ENABLED=0
    # This is evaluated at app creation time (after pytest is loaded)
    def _is_test_mode_for_limiter():
        """Check if we're in test mode for limiter configuration."""
        testing_val = os.getenv("TESTING", "").lower().strip()
        if testing_val in ("true", "1", "yes"):
            return True
        if "pytest" in sys.modules:
            return True
        if os.getenv("PYTEST_CURRENT_TEST"):
            return True
        if app.config.get("TESTING"):
            return True
        return False

    if _is_test_mode_for_limiter() and os.getenv("RATE_LIMIT_ENABLED", "1") == "0":
        limiter.enabled = False
        logger.info(
            "Rate limiting disabled for testing", extra={"context": {"test_mode": True}}
        )

    # Production validation: fail fast if weak secrets are used
    if is_production:
        weak_secrets = ["dev-secret-change-me", "dev-jwt-secret-change-me", "secret123"]
        secret_key = app.config["SECRET_KEY"]
        if secret_key in weak_secrets or len(secret_key) < 32:
            raise ValueError(
                "Production deployment requires strong SECRET_KEY (min 32 chars). "
                "Set FLASK_SECRET_KEY environment variable."
            )

    # HTTPS Enforcement (Task 3 - Production Security)
    # Fail fast if insecure OAuth transport is enabled in production
    if is_production and os.getenv("OAUTHLIB_INSECURE_TRANSPORT") == "1":
        raise RuntimeError(
            "OAUTHLIB_INSECURE_TRANSPORT must not be enabled in production. "
            "Set to 0 or remove from environment."
        )

    # Cookie and Session Hardening (Task 1 - Production Security)
    # In production (FLASK_ENV=production), cookies should use secure flag
    app.config.setdefault("SESSION_COOKIE_SECURE", is_production)
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("REMEMBER_COOKIE_SECURE", is_production)
    app.config.setdefault("REMEMBER_COOKIE_HTTPONLY", True)

    # CSRF Protection (Task 2 - Production Security)
    # Protect all forms from Cross-Site Request Forgery attacks
    from app.core.csrf_config import csrf

    csrf.init_app(app)

    # CSRF Configuration
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # Tokens don't expire (better UX)
    app.config["WTF_CSRF_SSL_STRICT"] = is_production  # Require HTTPS in production
    app.config["WTF_CSRF_ENABLED"] = True  # Explicitly enable (default, but clear)

    # HTTPS Enforcement with Talisman (Task 3 & 7 - Production Security)
    # Force HTTPS, add HSTS, XFO, XCTO, CSP, Referrer-Policy, and Permissions-Policy headers
    if is_production:
        from flask_talisman import Talisman

        # Content Security Policy as required for Task 7
        csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "object-src": ["'none'"],
        }

        # Initialize Talisman with most headers
        talisman = Talisman(
            app,
            # Content Security Policy
            content_security_policy=csp,
            content_security_policy_nonce_in=["script-src"],
            # HTTPS enforcement
            force_https=True,  # Enforce HTTPS in production
            # Strict-Transport-Security (HSTS)
            # Note: HSTS header only appears on HTTPS responses, not HTTP redirects
            strict_transport_security=True,
            strict_transport_security_max_age=63072000,  # 2 years (as required)
            strict_transport_security_include_subdomains=True,
            strict_transport_security_preload=True,
            # X-Frame-Options
            frame_options="DENY",
            # Referrer-Policy
            referrer_policy="no-referrer",
        )

        # WSGI middleware to override Permissions-Policy header
        # Talisman hardcodes browsing-topics=() with no option to customize
        # This middleware runs AFTER all Flask processing including Talisman
        original_wsgi_app = app.wsgi_app

        def permissions_policy_middleware(environ, start_response):
            def custom_start_response(status, headers, exc_info=None):
                # Override Permissions-Policy header in response
                headers_list = list(headers)
                for i, (name, value) in enumerate(headers_list):
                    if name.lower() == "permissions-policy":
                        headers_list[i] = (
                            "Permissions-Policy",
                            "camera=(), microphone=(), geolocation=()",
                        )
                        break
                return start_response(status, headers_list, exc_info)

            return original_wsgi_app(environ, custom_start_response)

        app.wsgi_app = permissions_policy_middleware

    # Surface DATABASE_URL in Flask config so other components (e.g., JSON vs JSONB chooser)
    # can correctly infer the active dialect. This also helps debugging.
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "")
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
    app.config["LOGIN_DISABLED"] = (
        os.getenv("LOGIN_DISABLED", "false").lower() == "true"
    )
    app.config["SHOW_API_DOCS"] = os.getenv("SHOW_API_DOCS", "false").lower() == "true"
    app.config["GIT_SHA"] = os.getenv("GIT_SHA", "")

    # Ensure database tables exist early to avoid runtime failures like
    # "relation 'users' does not exist" or "no such table: extratos".
    # This is idempotent and safe across SQLite/PostgreSQL in dev/test.
    try:
        from app.db.session import create_tables, get_engine

        create_tables()
        try:
            # Log basic DB connectivity and target for visibility
            eng = get_engine()
            logger.info(
                "Database ready",
                extra={
                    "context": {
                        "url": str(getattr(eng, "url", "")),
                        "driver": getattr(
                            getattr(eng, "dialect", None), "name", "unknown"
                        ),
                    }
                },
            )
        except Exception:
            # Non-fatal: table creation succeeded but introspection/logging failed
            logger.debug("Engine inspection skipped", exc_info=True)
    except Exception as e:
        logger.warning(
            "Failed to auto-create tables",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )

    # If primary DB is unreachable (e.g., Postgres password mismatch or container not ready),
    # provide a development-friendly fallback to the local SQLite DB to avoid blocking login/UI.
    if not test_database_connection():
        if not is_production:
            try:
                # Compute project_root again from script_dir
                backend_dir = os.path.dirname(script_dir)
                project_root = os.path.dirname(backend_dir)
                sqlite_path = os.path.join(project_root, "tattoo_studio_dev.db")
                os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path}"
                # Update Flask config reference so JSON type selection is consistent
                app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
                logger.warning(
                    "Primary DB unavailable; falling back to SQLite dev database",
                    extra={"context": {"sqlite_path": sqlite_path}},
                )
                from app.db.session import create_tables as _ct, get_engine as _ge

                _ct()
                eng = _ge()
                logger.info(
                    "Fallback database ready",
                    extra={
                        "context": {
                            "url": str(getattr(eng, "url", "")),
                            "driver": getattr(
                                getattr(eng, "dialect", None), "name", "unknown"
                            ),
                        }
                    },
                )
            except Exception as _e:
                logger.error(
                    "Failed to initialize fallback SQLite database",
                    extra={"context": {"error": str(_e)}},
                    exc_info=True,
                )

    # HTTP → HTTPS Redirect Fallback (Task 3 - Production Security)
    # Render terminates TLS at edge and sets X-Forwarded-Proto header
    # This ensures any HTTP requests are redirected to HTTPS
    @app.before_request
    def enforce_https_redirect():
        if (
            is_production
            and request.headers.get("X-Forwarded-Proto", "http") != "https"
        ):
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"  # type: ignore[assignment]
    login_manager.login_message = "Por favor, faça login para acessar esta página."

    # Helper function to detect test mode
    def _is_test_mode():
        """Check if we're running in test mode (pytest/CI)."""
        # Check TESTING env var (set in conftest.py and CI)
        testing_val = os.getenv("TESTING", "").lower().strip()
        if testing_val in ("true", "1", "yes"):
            return True
        # Check if pytest is running
        if "pytest" in sys.modules:
            return True
        # Check PYTEST_CURRENT_TEST (set by pytest during execution)
        if os.getenv("PYTEST_CURRENT_TEST"):
            return True
        # Check app.config for TESTING flag
        if app.config.get("TESTING"):
            return True
        return False

    # Test mode: Disable auth redirects when in test mode AND DISABLE_AUTH_REDIRECTS=1
    # This allows integration tests to receive 401 responses instead of 302 redirects
    # ONLY applies during testing - normal dev/prod behavior is unchanged
    disable_auth_redirects = (
        _is_test_mode() and os.getenv("DISABLE_AUTH_REDIRECTS", "0") == "1"
    )

    if disable_auth_redirects:

        @login_manager.unauthorized_handler
        def unauthorized():
            """Return 401 instead of redirecting to login during tests."""
            return (
                jsonify(
                    {"error": "Unauthorized", "message": "Authentication required"}
                ),
                401,
            )

    # Import models after app creation
    from app.db.base import User

    @login_manager.user_loader
    def load_user(user_id):
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            return db.get(User, int(user_id))

    @app.route("/")
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/auth/login")
    def google_login():
        return redirect(url_for("google_oauth_calendar.login"))

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Você foi desconectado com sucesso.", category="info")

        # Clear JWT cookie as well
        response = redirect(url_for("login_page"))
        # Use environment-aware secure flag consistent with global config
        secure_flag = app.config.get("SESSION_COOKIE_SECURE", False)
        response.set_cookie(
            "access_token",
            "",
            expires=0,
            httponly=True,
            secure=secure_flag,
            samesite="Lax",
        )
        return response

    @app.route("/index")
    @login_required
    def index():
        return render_template("index.html", user=current_user)

    @app.route("/cadastro_interno")
    @login_required
    def cadastro_interno():
        # Load artists to display in the table
        from app.db.session import SessionLocal
        from app.repositories.user_repo import UserRepository
        from app.services.user_service import UserService

        db_session = SessionLocal()
        try:
            user_repo = UserRepository(db_session)
            user_service = UserService(user_repo)
            artists = user_service.list_artists()
            return render_template("cadastro_interno.html", artists=artists)
        finally:
            db_session.close()

    @app.route("/calculadora")
    @login_required
    def calculadora():
        return render_template("calculadora.html")

    @app.route("/estoque")
    @login_required
    def estoque():
        from app.db.session import SessionLocal
        from app.repositories.inventory_repository import InventoryRepository
        from app.services.inventory_service import InventoryService

        with SessionLocal() as db:
            repository = InventoryRepository(db)
            service = InventoryService(repository)
            items = service.list_items()
        return render_template("estoque.html", inventory_items=items)

    @app.route("/estoque/novo", endpoint="novo_item")
    @login_required
    def novo_item():
        return render_template("novo_item.html")

    @app.route("/extrato")
    @login_required
    def extrato():
        # Generate extrato for previous month in background thread
        from app.services.extrato_automation import run_extrato_in_background

        run_extrato_in_background()
        return render_template(
            "extrato.html",
            initial_mes="",
            initial_ano="",
            bootstrap_extrato=None,
            bootstrap_message="Selecione o mês e o ano para visualizar o extrato mensal.",
            bootstrap_state="info",
        )

    @app.route("/extrato/<int:ano>/<int:mes>")
    @login_required
    def extrato_for_period(ano, mes):
        from app.db.base import Extrato
        from app.db.session import SessionLocal

        if mes < 1 or mes > 12 or ano < 2000 or ano > 2100:
            abort(404)

        requested_mes_str = f"{mes:02d}"
        selected_mes_str = requested_mes_str
        selected_ano_str = str(ano)
        bootstrap_data = None

        bootstrap_mes_nome = None
        feedback_state = "warning"
        feedback_message = f"Nenhum extrato encontrado para {requested_mes_str}/{ano}."

        month_names_pt = {
            1: "Janeiro",
            2: "Fevereiro",
            3: "Março",
            4: "Abril",
            5: "Maio",
            6: "Junho",
            7: "Julho",
            8: "Agosto",
            9: "Setembro",
            10: "Outubro",
            11: "Novembro",
            12: "Dezembro",
        }

        with SessionLocal() as db:
            stmt = select(Extrato).where(Extrato.mes == mes, Extrato.ano == ano)
            extrato_record = db.execute(stmt).scalar_one_or_none()

            if extrato_record:
                try:
                    record_mes = extrato_record.mes
                    record_ano = extrato_record.ano
                    record_mes_str = f"{record_mes:02d}"
                    record_mes_nome = month_names_pt.get(
                        record_mes, f"Mês {record_mes_str}"
                    )
                    bootstrap_data = {
                        "mes": record_mes,
                        "mes_nome": record_mes_nome,
                        "ano": record_ano,
                        "pagamentos": json.loads(extrato_record.pagamentos or "[]"),
                        "sessoes": json.loads(extrato_record.sessoes or "[]"),
                        "comissoes": json.loads(extrato_record.comissoes or "[]"),
                        "gastos": json.loads(extrato_record.gastos or "[]"),
                        "totais": json.loads(extrato_record.totais or "{}"),
                    }
                    selected_mes_str = record_mes_str
                    selected_ano_str = str(record_ano)
                    bootstrap_mes_nome = record_mes_nome
                    feedback_state = "success"
                    feedback_message = (
                        f"Extrato de {record_mes_nome}/{record_ano} "
                        "carregado automaticamente."
                    )
                except json.JSONDecodeError as err:
                    app.logger.error(
                        "Erro ao desserializar extrato para exibição: %s", err
                    )
                    bootstrap_data = None
                    feedback_state = "error"
                    feedback_message = (
                        "Erro ao carregar dados do extrato para exibição."
                    )

        return render_template(
            "extrato.html",
            initial_mes=selected_mes_str,
            initial_ano=selected_ano_str,
            bootstrap_extrato=bootstrap_data,
            bootstrap_message=feedback_message,
            bootstrap_state=feedback_state,
            bootstrap_mes_nome=bootstrap_mes_nome,
        )

    @app.route("/financeiro")
    @login_required
    def financeiro():
        # Redirect to the SOLID-compliant financeiro controller
        return redirect(url_for("financeiro.financeiro_home"))

    @app.route("/historico")
    @login_required
    def historico():
        # Redirect to the SOLID-compliant historico controller
        return redirect(url_for("historico.historico_home"))

    @app.route("/registrar_pagamento")
    @login_required
    def registrar_pagamento():
        # Redirect to the SOLID-compliant registrar_pagamento controller
        return redirect(url_for("financeiro.registrar_pagamento"))

    @app.route("/sessoes")
    @login_required
    def sessoes():
        # Redirect to the SOLID-compliant sessions list controller
        return redirect(url_for("sessoes.sessoes_home"))

    @app.route("/agenda")
    @login_required
    def agenda():
        # Redirect to the calendar page (Google Agenda)
        return redirect(url_for("calendar.calendar_page"))

    @app.route("/health")
    def health_check():
        """Health check endpoint for Docker"""
        db_status = test_database_connection()
        return jsonify(
            {
                "status": "healthy" if db_status else "unhealthy",
                "database": "connected" if db_status else "disconnected",
            }
        ), (200 if db_status else 503)

    @app.route("/pool-metrics")
    def pool_metrics():
        """
        SQLAlchemy connection pool metrics endpoint (Task 9).

        Returns JSON with pool statistics for monitoring.
        Useful for tracking connection usage, detecting leaks, and capacity planning.
        """
        from app.db.session import get_engine

        try:
            engine = get_engine()
            pool = engine.pool

            # Get pool status string and parse it
            status_str = pool.status()

            # Parse the status string (format: "Pool size: X  Connections in pool: Y Current Overflow: Z Current Checked out connections: W")
            # Use Dict[str, Union[str, int, float]] to allow mixed types
            from typing import Dict, Union

            pool_stats: Dict[str, Union[str, int, float]] = {
                "status": "healthy",
                "pool_status": status_str,
            }

            # Extract metrics from status string
            import re

            size_match = re.search(r"Pool size:\s*(\d+)", status_str)
            in_pool_match = re.search(r"Connections in pool:\s*(\d+)", status_str)
            overflow_match = re.search(r"Current Overflow:\s*(-?\d+)", status_str)
            checked_out_match = re.search(
                r"Current Checked out connections:\s*(\d+)", status_str
            )

            if size_match:
                pool_stats["pool_size"] = int(size_match.group(1))
            if in_pool_match:
                pool_stats["connections_in_pool"] = int(in_pool_match.group(1))
            if overflow_match:
                pool_stats["overflow"] = int(overflow_match.group(1))
            if checked_out_match:
                pool_stats["checked_out"] = int(checked_out_match.group(1))

            # Calculate utilization if we have the data
            if "pool_size" in pool_stats and "checked_out" in pool_stats:
                pool_size_val = pool_stats["pool_size"]
                checked_out_val = pool_stats["checked_out"]
                if isinstance(pool_size_val, int) and isinstance(checked_out_val, int):
                    if pool_size_val > 0:
                        pool_stats["utilization_percent"] = round(
                            (checked_out_val / pool_size_val) * 100, 2
                        )
                    else:
                        pool_stats["utilization_percent"] = 0.0

            return jsonify(pool_stats), 200

        except Exception as e:
            logger.error(
                "Failed to retrieve pool metrics",
                extra={"context": {"error": str(e)}},
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Failed to retrieve pool metrics",
                        "error": str(e),
                    }
                ),
                500,
            )

    # Sentry Test Route (Staging Only)
    # Only available when DEBUG_SENTRY_TEST=1 and not in production
    # Used to validate Sentry integration before production deployment
    if os.getenv("DEBUG_SENTRY_TEST") == "1" and os.getenv("FLASK_ENV") != "production":

        @app.route("/__sentry-test")
        def sentry_test():
            """
            Staging-only route to test Sentry error tracking.

            Raises a RuntimeError to verify that exceptions are properly
            captured and reported to Sentry dashboard.

            Usage:
                1. Set DEBUG_SENTRY_TEST=1 in staging environment
                2. Set SENTRY_DSN to your Sentry project DSN
                3. Access /__sentry-test endpoint
                4. Verify event appears in Sentry dashboard

            Security: This route is NOT registered in production (ENV=production)
            """
            logger.warning(
                "Sentry test route triggered - this should appear in Sentry",
                extra={"context": {"route": "/__sentry-test", "purpose": "testing"}},
            )
            raise RuntimeError(
                "Sentry test exception - if you see this in Sentry, integration is working!"
            )

    @app.route("/db-test")
    def database_test():
        """Test database connection endpoint"""
        if test_database_connection():
            return jsonify(
                {
                    "message": "Conexão com banco de dados estabelecida com sucesso!",
                    "database_url": os.getenv("DATABASE_URL", "Not set"),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "message": "Falha na conexão com banco de dados!",
                        "database_url": os.getenv("DATABASE_URL", "Not set"),
                    }
                ),
                500,
            )

    # Register blueprints/controllers here

    from app.controllers.admin_alerts_controller import admin_alerts_bp
    from app.controllers.admin_extrato_controller import admin_extrato_bp
    from app.controllers.api_controller import api_bp
    from app.controllers.artist_controller import artist_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.calendar_controller import calendar_bp
    from app.controllers.client_controller import client_bp
    from app.controllers.drag_drop_controller import drag_drop_bp
    from app.controllers.extrato_controller import extrato_bp
    from app.controllers.financeiro_controller import financeiro_bp
    from app.controllers.gastos_controller import gastos_bp
    from app.controllers.historico_controller import historico_bp
    from app.controllers.inventory_controller import inventory_bp
    from app.controllers.reports_controller import reports_bp
    from app.controllers.search_controller import search_bp
    from app.controllers.sessoes_controller import sessoes_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(sessoes_bp)
    app.register_blueprint(artist_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(drag_drop_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(historico_bp)
    app.register_blueprint(extrato_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(admin_alerts_bp)
    app.register_blueprint(admin_extrato_bp)
    app.register_blueprint(reports_bp)

    # Register OAuth blueprint - name already set at creation
    app.register_blueprint(google_oauth_bp, url_prefix="/auth")

    # Register template helper functions
    from app.utils.template_helpers import (
        format_client_name,
        format_currency,
        format_currency_dot,
        format_date_br,
        safe_attr,
    )

    app.jinja_env.globals.update(
        {
            "format_client_name": format_client_name,
            "format_currency": format_currency,
            "format_currency_dot": format_currency_dot,
            "format_date_br": format_date_br,
            "safe_attr": safe_attr,
        }
    )

    logger.info("Template helper functions registered")

    # Initialize background token refresh scheduler
    try:
        import logging

        from app.db.base import OAuth
        from app.db.session import SessionLocal
        from app.services.oauth_token_service import OAuthTokenService
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        logger = logging.getLogger(__name__)

        def refresh_all_tokens():
            """Background job to refresh all Google OAuth tokens"""
            logger.info("Starting background token refresh for all users")
            try:
                with SessionLocal() as db:
                    stmt = select(OAuth).where(OAuth.provider == "google")
                    oauth_records = db.execute(stmt).scalars().all()
                    refreshed_count = 0
                    failed_count = 0

                    for oauth_record in oauth_records:
                        try:
                            user_id = str(oauth_record.user_id)
                            oauth_service = OAuthTokenService()
                            new_token = oauth_service.refresh_access_token(user_id)
                            if new_token:
                                refreshed_count += 1
                                logger.info(
                                    f"Token atualizado com sucesso para o usuário {user_id}"
                                )
                            else:
                                failed_count += 1
                                logger.warning(
                                    f"Failed to refresh token for user {user_id}"
                                )
                        except Exception as e:
                            failed_count += 1
                            logger.error(
                                f"Error refreshing token for user "
                                f"{oauth_record.user_id}: {str(e)}"
                            )

                    logger.info(
                        f"Background token refresh completed: "
                        f"{refreshed_count} successful, {failed_count} failed"
                    )

            except Exception as e:
                logger.error(f"Error in background token refresh: {str(e)}")

        # Start background scheduler for token refresh
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            refresh_all_tokens,
            trigger=IntervalTrigger(hours=1),  # Run every hour
            id="token_refresh",
            name="Refresh Google OAuth tokens",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Background token refresh scheduler started")

        # Store scheduler reference to prevent garbage collection
        app.config["SCHEDULER"] = scheduler

    except ImportError as e:
        logger.warning(
            "APScheduler not available for background token refresh",
            extra={"context": {"error": str(e)}},
        )
    except Exception as e:
        logger.warning(
            "Failed to initialize background token refresh",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )

    # Add CLI commands
    @app.cli.command("reset-seed-test")
    def reset_seed_test_command():
        """Reset database, seed test data, and run tests."""
        from scripts.reset_seed_test import main

        sys.exit(main())

    return app
