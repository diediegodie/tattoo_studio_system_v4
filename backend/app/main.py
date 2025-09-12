from flask import Flask, render_template, jsonify, redirect, url_for, flash, session
import os
from sqlalchemy import text
from app.db.session import engine
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Google OAuth blueprint at module level
# Flask-Dance setup for Google OAuth at module level (must be before create_app)
google_oauth_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_[REDACTED_SECRET]"GOOGLE_CLIENT_SECRET"),
    scope=[
        "email",
        "profile",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ],
    redirect_url="/auth/google/authorized",
)
# Set unique name immediately to avoid conflicts
google_oauth_bp.name = "google_oauth_calendar"


# OAuth authorized handler - must be at module level
@oauth_authorized.connect_via(google_oauth_bp)
def google_logged_in(blueprint, token):
    print(f"[DEBUG] OAuth callback triggered with token: {bool(token)}")
    if not token:
        flash("Falha ao fazer login com Google.", category="error")
        return redirect(url_for("login_page"))

    print(f"[DEBUG] Token type: {type(token)}, content: {token}")

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Falha ao buscar informações do usuário do Google.", category="error")
        return redirect(url_for("login_page"))

    google_info = resp.json()
    google_user_id = str(google_info["id"])
    print(
        f"[DEBUG] Google user ID: {google_user_id}, email: {google_info.get('email')}"
    )

    from app.db.session import SessionLocal
    from app.repositories.user_repo import UserRepository
    from app.services.user_service import UserService
    from app.services.oauth_token_service import OAuthTokenService
    from app.core.security import create_user_token

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

        print(f"[DEBUG] Found DB user: {db_user.id}")

        # Save OAuth token for Google Calendar access
        token_saved = oauth_service.store_oauth_token(
            user_id=str(db_user.id),
            provider="google",
            provider_user_id=google_user_id,
            token=token,
        )
        print(f"[DEBUG] Token saved: {token_saved}")

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
        print(f"[ERROR] Exception in OAuth callback: {str(e)}")
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
        print(f"Database connection error: {e}")
        return False


def create_app():
    # Calculate paths based on the actual file system structure
    script_dir = os.path.dirname(
        os.path.abspath(__file__)
    )  # backend/app (local) or /app/app (Docker)

    # Check if we're in Docker by looking for the /app mount point
    if script_dir.startswith("/app"):
        # Running in Docker container
        # In Docker: script is at /app/app/main.py, frontend is at /app/frontend
        template_folder = "/app/frontend/templates"
        static_folder = "/app/frontend/assets"
        print("[DEBUG] Detected Docker environment")
    else:
        # Running locally
        # Local: script is at /path/to/project/backend/app/main.py
        # Need to go up: backend/app -> backend -> project-root -> frontend
        backend_dir = os.path.dirname(script_dir)  # backend
        project_root = os.path.dirname(backend_dir)  # project-root
        template_folder = os.path.join(project_root, "frontend", "templates")
        static_folder = os.path.join(project_root, "frontend", "assets")
        print("[DEBUG] Detected local environment")

    print(f"[DEBUG] Script dir: {script_dir}")
    print(f"[DEBUG] Template folder: {template_folder}")
    print(f"[DEBUG] Static folder: {static_folder}")
    print(f"[DEBUG] Current working directory: {os.getcwd()}")
    print(f"[DEBUG] Template folder exists: {os.path.exists(template_folder)}")

    if os.path.exists(template_folder):
        print(
            f"[DEBUG] Index.html exists: {os.path.exists(os.path.join(template_folder, 'index.html'))}"
        )
        print(
            f"[DEBUG] Contents of template folder: {os.listdir(template_folder)[:5]}..."
        )  # Show first 5 files
    else:
        print(f"[DEBUG] Template folder does not exist at: {template_folder}")
        # Try to find it in alternative locations
        alt_paths = [
            "/app/frontend/templates",
            "../frontend/templates",
            "./frontend/templates",
            os.path.join(os.getcwd(), "frontend", "templates"),
        ]
        for alt_path in alt_paths:
            exists = os.path.exists(alt_path)
            print(f"[DEBUG] Alternative path {alt_path} exists: {exists}")

    # Configure logging
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging configured with INFO level")

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
    )

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
    app.config["LOGIN_DISABLED"] = (
        os.getenv("LOGIN_DISABLED", "false").lower() == "true"
    )

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"  # type: ignore[assignment]
    login_manager.login_message = "Por favor, faça login para acessar esta página."

    # Import models after app creation
    from app.db.base import User, OAuth

    @login_manager.user_loader
    def load_user(user_id):
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            return db.query(User).get(int(user_id))
        finally:
            db.close()

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
        from app.services.user_service import UserService
        from app.repositories.user_repo import UserRepository
        from app.db.session import SessionLocal

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
        from app.repositories.inventory_repository import InventoryRepository
        from app.services.inventory_service import InventoryService
        from app.db.session import SessionLocal

        db = SessionLocal()
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        items = service.list_items()
        db.close()
        return render_template("estoque.html", inventory_items=items)

    @app.route("/estoque/novo", endpoint="novo_item")
    @login_required
    def novo_item():
        return render_template("novo_item.html")

    @app.route("/extrato")
    @login_required
    def extrato():
        # Generate extrato for previous month in background thread
        from app.services.extrato_service import run_extrato_in_background

        run_extrato_in_background()
        return render_template("extrato.html")

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
        return redirect(url_for("sessoes.list_sessoes"))

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
                    "message": "Database Connected Successfully!",
                    "database_url": os.getenv("DATABASE_URL", "Not set"),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "message": "Database Connection Failed!",
                        "database_url": os.getenv("DATABASE_URL", "Not set"),
                    }
                ),
                500,
            )

    # Register blueprints/controllers here

    from app.controllers.api_controller import api_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.client_controller import client_bp
    from app.controllers.sessoes_controller import sessoes_bp
    from app.controllers.artist_controller import artist_bp
    from app.controllers.calendar_controller import calendar_bp
    from app.controllers.inventory_controller import inventory_bp
    from app.controllers.drag_drop_controller import drag_drop_bp
    from app.controllers.financeiro_controller import financeiro_bp
    from app.controllers.historico_controller import historico_bp
    from app.controllers.extrato_controller import extrato_bp
    from app.controllers.search_controller import search_bp
    from app.controllers.gastos_controller import gastos_bp
    from app.controllers.admin_extrato_controller import admin_extrato_bp
    from app.controllers.reports_controller import reports_bp

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
    app.register_blueprint(admin_extrato_bp)
    app.register_blueprint(reports_bp)

    # Register OAuth blueprint - name already set at creation
    app.register_blueprint(google_oauth_bp, url_prefix="/auth")

    # Initialize background token refresh scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from app.services.oauth_token_service import OAuthTokenService
        from app.db.session import SessionLocal
        from app.db.base import OAuth
        import logging

        logger = logging.getLogger(__name__)

        def refresh_all_tokens():
            """Background job to refresh all Google OAuth tokens"""
            logger.info("Starting background token refresh for all users")
            db = SessionLocal()
            try:
                # Get all users with Google OAuth tokens
                oauth_records = db.query(OAuth).filter(OAuth.provider == "google").all()
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
                                f"Successfully refreshed token for user {user_id}"
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
            finally:
                db.close()

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
        print(f"Warning: APScheduler not available for background token refresh: {e}")
    except Exception as e:
        print(f"Warning: Failed to initialize background token refresh: {e}")

    return app
