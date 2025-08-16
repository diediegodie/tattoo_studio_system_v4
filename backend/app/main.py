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
        redirect_url="http://localhost:5000/auth/google/authorized",
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

        db = SessionLocal()
        try:
            # Check if user already exists
            user = db.query(User).filter_by(google_id=google_user_id).first()

            if not user:
                # Create new user
                user = User(
                    email=google_info["email"],
                    name=google_info["name"],
                    avatar_url=google_info.get("picture"),
                    google_id=google_user_id,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            login_user(user)
            flash(f"Bem-vindo, {user.name}!", category="success")
            return redirect(url_for("index"))
        except Exception as e:
            db.rollback()
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
        return redirect(url_for("login_page"))

    @app.route("/index")
    @login_required
    def index():
        return render_template("index.html", user=current_user)

    @app.route("/cadastro_interno")
    @login_required
    def cadastro_interno():
        return render_template("cadastro_interno.html")

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
        return render_template("sessoes.html")

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
    # e.g. from .controllers.user_controller import user_bp
    # app.register_blueprint(user_bp)

    return app
