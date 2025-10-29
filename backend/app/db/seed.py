"""
Database seeding and initialization functions.

This module contains functions that ensure critical data exists in the database,
such as service accounts needed for automation and CI/CD workflows.
"""

import logging
from typing import Optional

from app.db.base import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def ensure_service_account_user() -> None:
    """
    Ensure the GitHub Actions service account user exists in the database.

    This function is idempotent - it can be called multiple times safely.
    If the user doesn't exist, it creates it. If it exists, it updates
    critical fields to ensure the user is active and has admin role.

    Service account details:
    - id: 999
    - email: github-actions@tattoo-studio.local
    - name: GitHub Actions Bot
    - role: admin
    - active_flag: True
    - password_hash: "!" (invalid, forces JWT-only authentication)
    """
    try:
        with SessionLocal() as db:
            # Check if service account user exists
            user: Optional[User] = db.get(User, 999)

            if user is None:
                # Create new service account user
                user = User(
                    id=999,
                    email="github-actions@tattoo-studio.local",
                    name="GitHub Actions Bot",
                    role="admin",
                    active_flag=True,
                    password_hash="!",  # Invalid password, forces JWT-only auth
                )
                db.add(user)
                db.commit()
                logger.info(
                    "Service account user created",
                    extra={
                        "context": {
                            "user_id": 999,
                            "email": "github-actions@tattoo-studio.local",
                        }
                    },
                )
            else:
                # Update existing user to ensure correct role and active status
                updated = False
                if user.role != "admin":
                    user.role = "admin"
                    updated = True
                if not user.active_flag:
                    user.active_flag = True
                    updated = True
                if user.password_hash != "!":
                    user.password_hash = "!"
                    updated = True

                if updated:
                    db.commit()
                    logger.info(
                        "Service account user updated",
                        extra={
                            "context": {
                                "user_id": 999,
                                "email": user.email,
                                "changes": "role/active_flag/password_hash",
                            }
                        },
                    )
                else:
                    logger.debug(
                        "Service account user already exists and is correct",
                        extra={"context": {"user_id": 999}},
                    )
    except Exception as e:
        logger.error(
            "Failed to ensure service account user",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        # Don't raise - app should still start even if seeding fails
