import json
import logging
import os
import sys

from dotenv import load_dotenv

# Get logger for this module
logger = logging.getLogger(__name__)
from flask import (  # noqa: E402
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (  # noqa: E402
    LoginManager,
    current_user,
    login_required,
    logout_user,
)

# Import custom OAuth storage to support provider_user_id field
from app.core.custom_oauth_storage import CustomOAuthStorage  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

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


# Early runtime check for effective DATABASE_URL visibility in logs
print(
    ">>> DEBUG: DATABASE_URL efetiva:",
    _mask_url_password(SQLALCHEMY_DATABASE_URL),
)

# Import engine after environment is finalized
from app.db.session import engine  # noqa: E402

# Import OAuth provider constants for consistency
from app.config.oauth_provider import (  # noqa: E402
    PROVIDER_GOOGLE_LOGIN,
    PROVIDER_GOOGLE_CALENDAR,
)

# Import blueprint creation functions
from app.auth.google_login import create_google_login_blueprint  # noqa: E402
from app.auth.google_calendar import (  # noqa: E402
    create_google_calendar_blueprint,
)

# Get Google OAuth credentials
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

# NOTE: OAuth blueprints are now created inside create_app() to pass storage
# This ensures Flask-Dance uses CustomOAuthStorage during OAuth callbacks

# Signal handlers are defined in the blueprint creation functions


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


def create_app():  # noqa: C901
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

    # Log timezone configuration (Task 2)
    from app.core.config import log_timezone_config, APP_TZ, HEALTH_CHECK_TOKEN

    log_timezone_config()
    logger.info(
        "Application timezone configured",
        extra={
            "context": {
                "timezone": str(APP_TZ),
                "tz_source": os.getenv("TZ", "UTC (default)"),
            }
        },
    )

    # Log extrato backup configuration (Task 3)
    from app.core.config import log_extrato_config, EXTRATO_REQUIRE_BACKUP

    log_extrato_config()
    logger.info(
        "Extrato backup configuration loaded",
        extra={
            "context": {
                "require_backup": EXTRATO_REQUIRE_BACKUP,
                "backup_env": os.getenv("EXTRATO_REQUIRE_BACKUP", "true (default)"),
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
    app.config["RATELIMIT_EXEMPT_PATHS"] = ["/metrics", "/pool-metrics"]
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
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # Tokens don't expire
    app.config["WTF_CSRF_SSL_STRICT"] = is_production  # HTTPS in prod
    app.config["WTF_CSRF_ENABLED"] = True  # Explicitly enable
    app.config["WTF_CSRF_CHECK_DEFAULT"] = (
        False  # Disable referrer check (breaks with no-referrer policy)
    )

    # HTTPS Enforcement with Talisman (Task 3 & 7 - Production Security)
    # Force HTTPS, add HSTS, XFO, XCTO, CSP, Referrer-Policy,
    # and Permissions-Policy headers
    if is_production:
        from flask_talisman import Talisman

        # Content Security Policy as required for Task 7
        csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "object-src": ["'none'"],
            "style-src": [
                "'self'",
                "https://fonts.googleapis.com",
                "https://cdnjs.cloudflare.com",
            ],
            "font-src": [
                "'self'",
                "https://fonts.gstatic.com",
                "https://cdnjs.cloudflare.com",
            ],
            # Allow external profile pictures (Google) and inline images via data URIs
            "img-src": ["'self'", "https://lh3.googleusercontent.com", "data:"],
        }

        # Initialize Talisman with most headers
        Talisman(
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

    # Surface DATABASE_URL in Flask config
    # Allows other components (e.g., JSON vs JSONB) to infer dialect
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "")
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
    app.config["LOGIN_DISABLED"] = (
        os.getenv("LOGIN_DISABLED", "false").lower() == "true"
    )
    app.config["SHOW_API_DOCS"] = os.getenv("SHOW_API_DOCS", "false").lower() == "true"
    app.config["GIT_SHA"] = os.getenv("GIT_SHA", "")
    app.config["HEALTH_CHECK_TOKEN"] = HEALTH_CHECK_TOKEN

    # Provide safe defaults for Google OAuth credentials in test mode
    # so unit tests that exercise token refresh/validation can run without
    # requiring real environment secrets.
    if app.config.get("TESTING"):
        if not app.config.get("GOOGLE_OAUTH_CLIENT_ID"):
            app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv(
                "GOOGLE_CLIENT_ID", "test-google-client-id"
            )
        if not app.config.get("GOOGLE_OAUTH_CLIENT_SECRET"):
            app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv(
                "GOOGLE_CLIENT_SECRET", "test-google-client-secret"
            )

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

    # If primary DB is unreachable (e.g., Postgres password mismatch or
    # container not ready), provide a development-friendly fallback to the
    # local SQLite DB to avoid blocking login/UI.
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

    # Ensure service account user exists for GitHub Actions automation
    from app.db.seed import ensure_service_account_user

    ensure_service_account_user()

    @login_manager.user_loader
    def load_user(user_id):
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            return db.get(User, int(user_id))

    @login_manager.request_loader
    def load_user_from_request(request):
        """
        Load user from Authorization header Bearer token.
        This enables GitHub Actions service account authentication.
        """
        # Try to get Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        # Extract token
        token = auth_header.split(" ")[1]

        # Decode and validate JWT
        from app.core.security import decode_access_token

        payload = decode_access_token(token)
        if not payload:
            return None

        # Extract user_id from payload
        user_id = payload.get("user_id")
        if not user_id:
            return None

        # Load user from database
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            user = db.get(User, int(user_id))
            if user and user.is_active:
                return user

        return None

    @app.route("/")
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/auth/login")
    def google_login():
        """Redirect to Google Login blueprint"""
        return redirect(url_for(f"{PROVIDER_GOOGLE_LOGIN}.login"))

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
            bootstrap_message=(
                "Selecione o mês e o ano para visualizar o extrato mensal."
            ),
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

            # Parse the status string
            # Format: "Pool size: X  Connections in pool: Y
            #          Current Overflow: Z Current Checked out connections: W"
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
                "Sentry test route triggered",
                extra={
                    "context": {
                        "route": "/__sentry-test",
                        "purpose": "testing",
                    }
                },
            )
            raise RuntimeError(
                "Sentry test exception - if you see this in Sentry, "
                "integration is working!"
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

    @app.route("/debug/oauth-providers")
    def oauth_provider_counts():
        """
        Diagnostic endpoint to check OAuth provider distribution in database.

        Returns counts grouped by provider name to verify token storage.
        Only available in non-production environments for security.

        Usage:
            GET /debug/oauth-providers

        Returns:
            JSON with provider counts and sample records
        """
        # Security: Only allow in development/staging
        if os.getenv("FLASK_ENV") == "production":
            return jsonify({"error": "Not available in production"}), 403

        try:
            from sqlalchemy import func

            with SessionLocal() as db:
                # Count by provider
                counts = (
                    db.query(OAuth.provider, func.count(OAuth.id))
                    .group_by(OAuth.provider)
                    .all()
                )

                # Get sample records (limit 5 per provider, exclude token values)
                samples = []
                for provider_name, _ in counts:
                    provider_samples = (
                        db.query(
                            OAuth.id,
                            OAuth.provider,
                            OAuth.user_id,
                            OAuth.provider_user_id,
                            OAuth.created_at,
                        )
                        .filter(OAuth.provider == provider_name)
                        .limit(5)
                        .all()
                    )
                    samples.extend(
                        [
                            {
                                "id": s.id,
                                "provider": s.provider,
                                "user_id": s.user_id,
                                "provider_user_id": s.provider_user_id,
                                "created_at": (
                                    s.created_at.isoformat() if s.created_at else None
                                ),
                            }
                            for s in provider_samples
                        ]
                    )

                return jsonify(
                    {
                        "provider_counts": [
                            {"provider": p, "count": c} for p, c in counts
                        ],
                        "total_records": sum(c for _, c in counts),
                        "expected_providers": [
                            PROVIDER_GOOGLE_LOGIN,
                            PROVIDER_GOOGLE_CALENDAR,
                        ],
                        "sample_records": samples,
                    }
                )
        except Exception as e:
            logger.error(f"Error querying OAuth providers: {str(e)}")
            return jsonify({"error": str(e)}), 500

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
    from app.controllers.health_controller import health_bp
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
    app.register_blueprint(health_bp)
    app.register_blueprint(admin_alerts_bp)
    app.register_blueprint(admin_extrato_bp)
    app.register_blueprint(reports_bp)

    # CRITICAL FIX: Configure SQLAlchemy storage for Flask-Dance
    # BEFORE registering blueprint. This ensures OAuth tokens are stored
    # in the database using our OAuth model with JSONB. Without this,
    # Flask-Dance uses default SessionStorage (serializes tokens as strings)
    from app.db.base import OAuth  # noqa: E402
    from app.db.session import SessionLocal  # noqa: E402

    print(
        ">>> DEBUG: [create_app] Configuring Flask-Dance SQLAlchemy "
        "storage for both blueprints"
    )

    # ✅ CRITICAL FIX: Create blueprints WITH storage passed during creation
    # Previously, blueprints were created at module level and storage
    # assigned afterwards. This caused Flask-Dance to use default storage
    # (MemoryStorage) during OAuth callbacks. Now we create blueprints here
    # and pass CustomOAuthStorage during make_google_blueprint()

    # Create CustomOAuthStorage instances for both blueprints
    google_login_storage = CustomOAuthStorage(
        OAuth,
        SessionLocal,  # ✅ Pass the factory function, NOT SessionLocal()
        user=lambda: current_user,
        # Allow tokens without Flask-Login user (we handle manually)
        user_required=False,
    )

    google_calendar_storage = CustomOAuthStorage(
        OAuth,
        SessionLocal,  # ✅ Pass the factory function, NOT SessionLocal()
        user=lambda: current_user,
        # Require authenticated user for calendar authorization
        user_required=True,
    )

    # Create Google Login Blueprint with storage passed during creation
    google_login_bp = create_google_login_blueprint(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        redirect_url=("http://127.0.0.1:5000/auth/google_login/google/authorized"),
        storage=google_login_storage,  # ✅ Pass storage here, not afterwards
    )
    print(">>> DEBUG: google_login_bp.storage =", type(google_login_bp.storage))

    # Create Google Calendar Blueprint with storage passed during creation
    google_calendar_bp = create_google_calendar_blueprint(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        redirect_url=(
            "http://127.0.0.1:5000/auth/calendar/google_calendar/" "google/authorized"
        ),
        storage=google_calendar_storage,  # ✅ Pass storage here
    )
    print(
        ">>> DEBUG: google_calendar_bp.storage =",
        type(google_calendar_bp.storage),
    )
    print(
        ">>> DEBUG: [create_app] Flask-Dance storage configured "
        "successfully for both blueprints"
    )

    # Diagnostic: Log OAuth blueprint configurations for debugging
    logger.info(
        "Google Login blueprint configured",
        extra={
            "context": {
                "blueprint_name": google_login_bp.name,
                "provider": PROVIDER_GOOGLE_LOGIN,
                "storage_type": type(google_login_bp.storage).__name__,
                "user_required": False,
                "scopes": ["openid", "email", "profile"],
            }
        },
    )

    logger.info(
        "Google Calendar blueprint configured",
        extra={
            "context": {
                "blueprint_name": google_calendar_bp.name,
                "provider": PROVIDER_GOOGLE_CALENDAR,
                "storage_type": type(google_calendar_bp.storage).__name__,
                "user_required": True,
                "scopes": [
                    "https://www.googleapis.com/auth/calendar.readonly",
                    "https://www.googleapis.com/auth/calendar.events",
                ],
            }
        },
    )

    # Register both OAuth blueprints with url_prefix
    # Flask-Dance creates /google routes, so we prefix them
    app.register_blueprint(google_login_bp, url_prefix="/auth/google_login")
    logger.info(
        "Google Login blueprint registered",
        extra={
            "context": {
                "blueprint_name": google_login_bp.name,
                "provider": PROVIDER_GOOGLE_LOGIN,
                "url_prefix": "/auth/google_login",
                "login_route": "/auth/google_login/google",
                "callback_route": ("/auth/google_login/google/authorized"),
            }
        },
    )

    app.register_blueprint(
        google_calendar_bp, url_prefix="/auth/calendar/google_calendar"
    )
    logger.info(
        "Google Calendar blueprint registered",
        extra={
            "context": {
                "blueprint_name": google_calendar_bp.name,
                "provider": PROVIDER_GOOGLE_CALENDAR,
                "url_prefix": "/auth/calendar/google_calendar",
                "login_route": "/auth/calendar/google_calendar/google",
                "callback_route": ("/auth/calendar/google_calendar/google/authorized"),
            }
        },
    )

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
        from apscheduler.triggers.cron import CronTrigger

        logger = logging.getLogger(__name__)

        def refresh_all_tokens():
            """Background job to refresh all Google OAuth tokens"""
            logger.info("Starting background token refresh for all users")
            try:
                with SessionLocal() as db:
                    # Query both login and calendar tokens
                    stmt = select(OAuth).where(
                        OAuth.provider.in_(
                            [PROVIDER_GOOGLE_LOGIN, PROVIDER_GOOGLE_CALENDAR]
                        )
                    )
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
                                    "Token atualizado com sucesso "
                                    f"para o usuário {user_id}"
                                )
                            else:
                                failed_count += 1
                                logger.warning(
                                    f"Failed to refresh token " f"for user {user_id}"
                                )
                        except Exception as e:
                            failed_count += 1
                            logger.error(
                                "Error refreshing token for user "
                                f"{oauth_record.user_id}: {str(e)}"
                            )

                    logger.info(
                        "Background token refresh completed: "
                        f"{refreshed_count} successful, {failed_count} failed"
                    )

            except Exception as e:
                logger.error(f"Error in background token refresh: {str(e)}")

        def generate_monthly_extrato_job():
            """Scheduled monthly extrato snapshot generation.

            Runs on the 1st of each month at 02:00 AM to generate
            the previous month's extrato snapshot automatically.

            Note (Task 2 - Timezone):
                Uses timezone-aware datetime operations via APP_TZ from core.config.
                Threshold set to day 2 (min_day_threshold=2) to allow 1-day buffer
                for end-of-month data ingestion. Job runs on day 1, but respects
                threshold for data completeness.

            Note (Task 3 - Backup):
                Uses atomic transaction with backup verification.
                Backup requirement controlled by EXTRATO_REQUIRE_BACKUP env var.
                Routes through check_and_generate_extrato_with_transaction() for
                full transaction safety and backup validation.
            """
            from datetime import datetime
            from app.services.extrato_core import get_previous_month
            from app.core.config import APP_TZ, EXTRATO_REQUIRE_BACKUP

            # Get target month/year for logging
            target_month, target_year = get_previous_month()
            execution_time = datetime.now(APP_TZ).isoformat()

            logger.info(
                f"Running scheduled monthly_extrato generation for target_month={target_month}, target_year={target_year}",
                extra={
                    "context": {
                        "job": "monthly_extrato",
                        "target_month": target_month,
                        "target_year": target_year,
                        "execution_time": execution_time,
                        "timezone": str(APP_TZ),
                        "require_backup": EXTRATO_REQUIRE_BACKUP,
                    }
                },
            )

            try:
                # Resolve the function at call time so tests that patch app.services.extrato_atomic.check_and_generate_extrato_with_transaction are effective
                import importlib

                extrato_atomic = importlib.import_module("app.services.extrato_atomic")

                # Use atomic version with backup check (Task 3)
                # No args → previous month by default inside the service
                success = extrato_atomic.check_and_generate_extrato_with_transaction()

                if success:
                    logger.info(
                        "Monthly extrato generation completed successfully",
                        extra={
                            "context": {
                                "job": "monthly_extrato",
                                "target_month": target_month,
                                "target_year": target_year,
                                "status": "success",
                            }
                        },
                    )
                else:
                    logger.error(
                        "Monthly extrato generation failed",
                        extra={
                            "context": {
                                "job": "monthly_extrato",
                                "target_month": target_month,
                                "target_year": target_year,
                                "status": "failed",
                                "reason": "check_and_generate_extrato_with_transaction returned False",
                            }
                        },
                    )
            except Exception as e:
                logger.error(
                    "Error in scheduled extrato generation",
                    extra={
                        "context": {
                            "job": "monthly_extrato",
                            "target_month": target_month,
                            "target_year": target_year,
                            "status": "error",
                            "error": str(e),
                        }
                    },
                    exc_info=True,
                )

        # Start background scheduler for token refresh
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            refresh_all_tokens,
            trigger=IntervalTrigger(hours=1),  # Run every hour
            id="token_refresh",
            name="Refresh Google OAuth tokens",
            replace_existing=True,
        )

        # Add monthly extrato generation job (controlled by environment variable)
        enable_extrato_job = (
            os.getenv("ENABLE_MONTHLY_EXTRATO_JOB", "true").lower() == "true"
        )

        if enable_extrato_job:
            scheduler.add_job(
                generate_monthly_extrato_job,
                trigger=CronTrigger(
                    day=1, hour=2, minute=0
                ),  # 1st of month at 02:00 AM
                id="monthly_extrato",
                name="Generate monthly extrato snapshot",
                replace_existing=True,
            )
            logger.info(
                "Monthly extrato job registered",
                extra={
                    "context": {
                        "job_id": "monthly_extrato",
                        "schedule": "day 1 at 02:00 AM",
                    }
                },
            )
        else:
            logger.info(
                "Monthly extrato job disabled by environment variable",
                extra={"context": {"ENABLE_MONTHLY_EXTRATO_JOB": "false"}},
            )

        scheduler.start()
        logger.info(
            "Background scheduler started with token refresh and monthly extrato jobs"
        )

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
