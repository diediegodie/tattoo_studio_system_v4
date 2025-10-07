"""Management commands for the Tattoo Studio backend application."""

from __future__ import annotations

import logging
import os
from typing import Optional

import click

from app.main import create_app
from app.db.base import User
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# Create the Flask application once so commands can share configuration.
app = create_app()


@click.group()
def cli() -> None:
    """Entry point for management commands."""


@cli.command("ensure_admin")
@click.option(
    "--email",
    "email_override",
    default=None,
    help="Email of the user to promote. Overrides ADMIN_EMAIL environment variable.",
)
def ensure_admin(email_override: Optional[str]) -> None:
    """Ensure at least one admin user exists by promoting the configured user."""

    target_email = email_override or os.getenv("ADMIN_EMAIL")
    if not target_email:
        raise click.ClickException(
            "ADMIN_EMAIL environment variable is not set and no --email provided."
        )

    with app.app_context():
        session = SessionLocal()
        try:
            existing_admin = session.query(User).filter(User.role == "admin").first()
            if existing_admin:
                logging.info(
                    "Admin already present (id=%s, email=%s); no changes made.",
                    existing_admin.id,
                    existing_admin.email,
                )
                return

            user = session.query(User).filter(User.email == target_email).first()
            if user is None:
                raise click.ClickException(
                    f"No user found with email '{target_email}'. Cannot promote to admin."
                )

            if getattr(user, "role", None) == "admin":
                logging.info(
                    "User %s already has admin role. No changes made.", target_email
                )
                return

            user.role = "admin"
            session.commit()
            logging.info(
                "Promoted user %s (id=%s) to admin role.", target_email, user.id
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    cli()
