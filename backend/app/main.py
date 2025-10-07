import json
import logging
import os
import sys

from app.db.session import engine
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
    session,
    url_for,
)
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import google, make_google_blueprint
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import select, text

# Load environment variables
load_dotenv()

# Create Google OAuth blueprint at module level
# Flask-Dance setup for Google OAuth at module level (must be before create_app)
# IMPORTANT: The Google Cloud Console OAuth client must list
# http://127.0.0.1:5000/auth/google/authorized as an authorized redirect URI.
# This blueprint is registered with url_prefix="/auth", so the absolute callback
# will always resolve to /auth/google/authorized locally and in Docker.
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_[REDACTED_SECRET]"GOOGLE_CLIENT_SECRET")

if not google_client_id or not google_client_[REDACTED_SECRET]
        "Google OAuth credentials missing",
        extra={
            "context": {
                "has_client_id": bool(google_client_id),
                "has_client_[REDACTED_SECRET]
            }
        },
    )

google_oauth_bp = make_google_blueprint(
    client_id=google_client_id,
    client_[REDACTED_SECRET]
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

        # Get domain user for business logic
        domain_user = service.create_or_update_from_google(google_info)

        # Get database user for Flask-Login
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
        token_saved = oauth_service.store_oauth_token(
            user_id=str(db_user.id),
            provider="google",
            provider_user_id=google_user_id,
            token=token,
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
        response.set_cookie(
            "access_token",
            jwt_token,
            max_age=604800,  # 7 days (increased from 24 hours)
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
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
            result = connection.execute(text("SELECT 1"))
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

    # Configure structured logging (after app creation so we can register hooks)
    from app.core.logging_config import setup_logging
    import logging

    setup_logging(
        app=app,  # Pass app to register request/response hooks
        log_level=logging.INFO if is_production else logging.DEBUG,
        enable_sql_echo=not is_production,  # SQL echo in dev only
        log_to_file=True,
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

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
    app.config["LOGIN_DISABLED"] = (
        os.getenv("LOGIN_DISABLED", "false").lower() == "true"
    )
    app.config["SHOW_API_DOCS"] = os.getenv("SHOW_API_DOCS", "false").lower() == "true"

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"  # type: ignore[assignment]
    login_manager.login_message = "Por favor, faça login para acessar esta página."

    # Import models after app creation
    from app.db.base import OAuth, User

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
        response.set_cookie("access_token", "", expires=0)
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
        from app.services.extrato_automation import run_extrato_in_background

        if mes < 1 or mes > 12 or ano < 2000 or ano > 2100:
            abort(404)

        run_extrato_in_background()

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
                    feedback_message = f"Extrato de {record_mes_nome}/{record_ano} carregado automaticamente."
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
                                f"Error refreshing token for user {oauth_record.user_id}: {str(e)}"
                            )

                    logger.info(
                        f"Background token refresh completed: {refreshed_count} successful, {failed_count} failed"
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
