"""
Client controller for handling HTTP requests following SOLID principles.

This controller:
- Handles HTTP concerns only (Single Responsibility)
- Depends on service abstractions (Dependency Inversion)
- Can be easily extended without modification (Open/Closed)
"""

from flask import Blueprint, render_template, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ..db.session import SessionLocal
from ..repositories.client_repo import ClientRepository
from ..services.client_service import ClientService
from ..services.jotform_service import JotFormService
import os

client_bp = Blueprint("client", __name__, url_prefix="/clients")

# JotForm configuration from environment variables
_JOTFORM_API_KEY = os.getenv("JOTFORM_API_KEY", "test-api-key")
_JOTFORM_FORM_ID = os.getenv("JOTFORM_FORM_ID", "test-form-id")

# Validation for required environment variables (skip validation in test environment)
if not os.getenv("TESTING") and (not _JOTFORM_API_KEY or not _JOTFORM_FORM_ID):
    raise ValueError(
        "JOTFORM_API_KEY and JOTFORM_FORM_ID must be set in environment variables"
    )

# Type-safe constants
JOTFORM_API_KEY: str = _JOTFORM_API_KEY
JOTFORM_FORM_ID: str = _JOTFORM_FORM_ID


@client_bp.route("/")
@login_required
def client_list():
    """Display list of clients with all JotForm submission data."""
    db = SessionLocal()
    try:
        # Setup dependencies following SOLID principles
        client_repo = ClientRepository(db)
        jotform_service = JotFormService(JOTFORM_API_KEY, JOTFORM_FORM_ID)
        client_service = ClientService(client_repo, jotform_service)

        # Get formatted JotForm submissions for display
        submissions = client_service.get_jotform_submissions_for_display()
        return render_template("list.html", submissions=submissions)
    except Exception as e:
        flash(f"Erro ao carregar clientes: {str(e)}", "error")
        return render_template("list.html", submissions=[])
    finally:
        db.close()


@client_bp.route("/sync")
@login_required
def sync_clients():
    """Sync clients from JotForm to local database."""
    db = SessionLocal()
    try:
        # Setup dependencies
        client_repo = ClientRepository(db)
        jotform_service = JotFormService(JOTFORM_API_KEY, JOTFORM_FORM_ID)
        client_service = ClientService(client_repo, jotform_service)

        # Sync clients
        synced_clients = client_service.sync_clients_from_jotform()

        flash(
            f"Sincronizados {len(synced_clients)} novos clientes do JotForm!", "success"
        )
        return redirect(url_for("client.client_list"))

    except Exception as e:
        flash(f"Erro ao sincronizar clientes: {str(e)}", "error")
        return redirect(url_for("client.client_list"))
    finally:
        db.close()


@client_bp.route("/api/list")
@login_required
def api_client_list():
    """API endpoint to get clients from local database (for internal system use)."""
    db = SessionLocal()
    try:
        client_repo = ClientRepository(db)
        jotform_service = JotFormService(JOTFORM_API_KEY, JOTFORM_FORM_ID)
        client_service = ClientService(client_repo, jotform_service)

        clients = client_service.get_all_clients()

        client_data = []
        for client in clients:
            client_data.append(
                {
                    "id": client.id,
                    "name": client.full_name,
                    "jotform_submission_id": client.jotform_submission_id,
                    "created_at": (
                        client.created_at.isoformat() if client.created_at else None
                    ),
                }
            )

        return jsonify({"clients": client_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
