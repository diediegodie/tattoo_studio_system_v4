from flask import Flask, render_template
import os

def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # <-- Only one dirname
    template_folder = os.path.join(base_dir, '../../frontend/templates')
    static_folder = os.path.join(base_dir, '../../frontend/assets')
    app = Flask(
        __name__,
        template_folder=os.path.abspath(template_folder),
        static_folder=os.path.abspath(static_folder)
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/cadastro_interno")
    def cadastro_interno():
        return render_template("cadastro_interno.html")

    @app.route("/calculadora")
    def calculadora():
        return render_template("calculadora.html")

    @app.route("/estoque")
    def estoque():
        return render_template("estoque.html")

    @app.route("/extrato")
    def extrato():
        return render_template("extrato.html")

    @app.route("/financeiro")
    def financeiro():
        return render_template("financeiro.html")

    @app.route("/historico")
    def historico():
        return render_template("historico.html")

    @app.route("/registrar_pagamento")
    def registrar_pagamento():
        return render_template("registrar_pagamento.html")

    @app.route("/sessoes")
    def sessoes():
        return render_template("sessoes.html")

    # Register blueprints/controllers here
    # e.g. from .controllers.user_controller import user_bp
    # app.register_blueprint(user_bp)

    return app