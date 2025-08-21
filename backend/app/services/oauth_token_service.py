"""
OAuth Token Service - SOLID compliant token management
Single Responsibility: Handle OAuth token operations for Google Calendar
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from flask import current_app

from db.session import SessionLocal
from db.base import OAuth

logger = logging.getLogger(__name__)


class OAuthTokenService:
    """
    Service for managing OAuth tokens.
    Follows Single Responsibility Principle - only handles token operations.
    """

    def __init__(self):
        self.db = SessionLocal()

    def store_oauth_token(
        self, user_id: str, provider: str, provider_user_id: str, token: Dict[str, Any]
    ) -> bool:
        """
        Store OAuth token for user.

        Args:
            user_id: Internal user ID
            provider: OAuth provider (e.g., 'google')
            provider_user_id: Provider-specific user ID
            token: OAuth token data from provider

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            print(
                f"[DEBUG] Storing OAuth token for user {user_id}, provider {provider}"
            )
            print(
                f"[DEBUG] Token data type: {type(token)}, has [REDACTED_ACCESS_TOKEN] in token if isinstance(token, dict) else 'Not a dict'}"
            )

            # Check if record already exists
            existing = (
                self.db.query(OAuth)
                .filter(OAuth.user_id == int(user_id), OAuth.provider == provider)
                .first()
            )

            if existing:
                # Update existing token - use setattr for SQLAlchemy attributes
                setattr(
                    existing,
                    "token",
                    (
                        token
                        if isinstance(token, dict)
                        else json.loads(token) if isinstance(token, str) else token
                    ),
                )
                setattr(existing, "provider_user_id", provider_user_id)
                self.db.commit()
                logger.info(
                    f"Updated OAuth token for {provider} user {provider_user_id}"
                )
            else:
                # Create new token record
                oauth_record = OAuth()
                # Set all attributes after creation using setattr
                setattr(oauth_record, "provider", provider)
                setattr(
                    oauth_record,
                    "token",
                    (
                        token
                        if isinstance(token, dict)
                        else json.loads(token) if isinstance(token, str) else token
                    ),
                )
                setattr(oauth_record, "provider_user_id", provider_user_id)
                setattr(oauth_record, "user_id", int(user_id))

                self.db.add(oauth_record)

            self.db.commit()
            print(f"[DEBUG] OAuth token committed to database")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to store OAuth token: {str(e)}")
            logger.error(f"Error storing OAuth token for user {user_id}: {str(e)}")
            self.db.rollback()
            return False
        finally:
            self.db.close()

    def get_user_access_token(self, user_id: str) -> Optional[str]:
        """
        Get Google access token for user.

        Args:
            user_id: User identifier

        Returns:
            Access token if available and valid, None otherwise
        """
        try:
            # Query from database storage
            oauth_record = (
                self.db.query(OAuth)
                .filter(OAuth.user_id == int(user_id), OAuth.provider == "google")
                .first()
            )

            if oauth_record and getattr(oauth_record, "token", None):
                # OAuth record stores token as JSON string
                import json

                try:
                    token_value = getattr(oauth_record, "token", None)
                    token_data = (
                        json.loads(token_value)
                        if isinstance(token_value, str)
                        else token_value
                    )
                    if token_data and isinstance(token_data, dict):
                        [REDACTED_ACCESS_TOKEN]"access_token")
                        if [REDACTED_ACCESS_TOKEN]
                                f"Retrieved token from database for user {user_id}"
                            )
                            return access_token
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Error parsing token for user {user_id}: {str(e)}")

            logger.warning(f"No valid access token found for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving access token for user {user_id}: {str(e)}")
            return None
        finally:
            self.db.close()

    def refresh_user_token(self, user_id: str) -> Optional[str]:
        """
        Refresh Google access token for user.

        Args:
            user_id: User identifier

        Returns:
            New access token if refresh successful, None otherwise
        """
        try:
            # For now, return the existing token if available
            # Token refresh logic can be implemented later if needed
            existing_token = self.get_user_access_token(user_id)
            if existing_token:
                logger.info(f"Using existing token for user {user_id}")
                return existing_token

            logger.warning(f"Could not refresh token for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error refreshing token for user {user_id}: {str(e)}")
            return None

    def is_token_valid(self, user_id: str) -> bool:
        """
        Check if user's OAuth token is valid.

        Args:
            user_id: User identifier

        Returns:
            True if token is valid, False otherwise
        """
        try:
            [REDACTED_ACCESS_TOKEN]
            if not [REDACTED_ACCESS_TOKEN] False

            # Test token validity with a simple API call
            import requests

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary",
                headers=headers,
                timeout=10,
            )

            is_valid = response.status_code == 200
            logger.info(
                f"Token validation for user {user_id}: {'valid' if is_valid else 'invalid'}"
            )
            return is_valid

        except Exception as e:
            logger.error(f"Error validating token for user {user_id}: {str(e)}")
            return False

    def revoke_user_token(self, user_id: str) -> bool:
        """
        Revoke Google access token for user.

        Args:
            user_id: User identifier

        Returns:
            True if revocation successful, False otherwise
        """
        try:
            [REDACTED_ACCESS_TOKEN]
            if not [REDACTED_ACCESS_TOKEN]"No token to revoke for user {user_id}")
                return True

            # Revoke token with Google
            import requests

            response = requests.post(
                f"https://oauth2.googleapis.com/revoke?token={access_token}", timeout=10
            )

            if response.status_code == 200:
                # Clear token from database
                oauth_record = (
                    self.db.query(OAuth)
                    .filter(OAuth.user_id == int(user_id), OAuth.provider == "google")
                    .first()
                )

                if oauth_record:
                    self.db.delete(oauth_record)
                    self.db.commit()

                logger.info(f"Token revoked for user {user_id}")
                return True
            else:
                logger.warning(
                    f"Failed to revoke token for user {user_id}: {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"Error revoking token for user {user_id}: {str(e)}")
            return False
        finally:
            self.db.close()

    def get_authorization_url(self) -> str:
        """
        Get Google OAuth authorization URL.

        Returns:
            Authorization URL for redirecting user
        """
        try:
            # This would typically be handled by Flask-Dance blueprint
            # But we can provide the URL for manual authorization
            from urllib.parse import urlencode
            import os

            params = {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "redirect_uri": os.getenv(
                    "GOOGLE_OAUTH_REDIRECT_URL",
                    "http://localhost:5000/auth/google/authorized",
                ),
                "scope": "openid email profile https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events",
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
            }

            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            )
            return auth_url

        except Exception as e:
            logger.error(f"Error generating authorization URL: {str(e)}")
            return ""
