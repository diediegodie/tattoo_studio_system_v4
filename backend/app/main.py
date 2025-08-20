from flask import Flask, render_template, jsonify, redirect, url_for, flash
import os
from sqlalchemy import text
from db.session import engine
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
    # Use absolute paths for Docker container
    template_folder = "/app/frontend/templates"
    static_folder = "/app/frontend/assets"
    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
    )

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"  # type: ignore[assignment]
    login_manager.login_message = "Por favor, faça login para acessar esta página."

    # Import models after app creation
    from db.base import User, OAuth

    # Create Google OAuth blueprint
    google_bp = make_google_blueprint(
        client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
        client_[REDACTED_SECRET]"GOOGLE_OAUTH_CLIENT_SECRET"],
        scope=["openid", "email", "profile"],
        redirect_url=os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URL", "http://localhost:5000/auth/google/authorized"
        ),
        redirect_to="index",
    )
    app.register_blueprint(google_bp, url_prefix="/auth")

    @login_manager.user_loader
    def load_user(user_id):
        from db.session import SessionLocal

        db = SessionLocal()
        try:
            return db.query(User).get(int(user_id))
        finally:
            db.close()

    # OAuth authorized handler
    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        if not token:
            flash("Falha ao fazer login com Google.", category="error")
            return redirect(url_for("login_page"))

        resp = blueprint.session.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash("Falha ao buscar informações do usuário do Google.", category="error")
            return redirect(url_for("login_page"))

        google_info = resp.json()
        google_user_id = str(google_info["id"])

        from db.session import SessionLocal
        from repositories.user_repo import UserRepository
        from services.user_service import UserService
        from core.security import create_user_token

        db = SessionLocal()
        try:
            repo = UserRepository(db)
            service = UserService(repo)

            user = service.create_or_update_from_google(google_info)

            # Create JWT token for API access
            jwt_token = create_user_token(user.id, user.email)  # type: ignore

            login_user(user)
            flash(f"Bem-vindo, {user.name}!", category="success")  # type: ignore            # Set JWT token as httpOnly cookie for API access
            response = redirect(url_for("index"))
            response.set_cookie(
                "access_token",
                jwt_token,
                max_age=24 * 60 * 60,  # 24 hours
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="Lax",
            )
            return response
        except Exception as e:
            # Rollback in case repository/service raised after partial changes
            try:
                db.rollback()
            except Exception:
                pass
            flash(f"Erro ao processar login: {str(e)}", category="error")
            return redirect(url_for("login_page"))
        finally:
            db.close()

    @app.route("/")
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/auth/login")
    def google_login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        return redirect(url_for("google.login"))

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
        from services.user_service import UserService
        from repositories.user_repo import UserRepository
        from db.session import SessionLocal

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
        return render_template("estoque.html")

    @app.route("/extrato")
    @login_required
    def extrato():
        return render_template("extrato.html")

    @app.route("/financeiro")
    @login_required
    def financeiro():
        return render_template("financeiro.html")

    @app.route("/historico")
    @login_required
    def historico():
        return render_template("historico.html")

    @app.route("/registrar_pagamento")
    @login_required
    def registrar_pagamento():
        return render_template("registrar_pagamento.html")

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

    from controllers.api_controller import api_bp
    from controllers.auth_controller import auth_bp
    from controllers.client_controller import client_bp
    from controllers.sessoes_controller import sessoes_bp
    from controllers.artist_controller import artist_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(sessoes_bp)
    app.register_blueprint(artist_bp)

    return app
