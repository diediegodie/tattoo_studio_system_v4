"""
OAuth Token Service - SOLID compliant token management
Single Responsibility: Handle OAuth token operations for Google Calendar
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests
from app.db.base import OAuth
from app.db.session import SessionLocal
from flask import current_app
from app.config.oauth_provider import PROVIDER_GOOGLE_CALENDAR

logger = logging.getLogger(__name__)


class OAuthTokenService:
    """
    Service for managing OAuth tokens.
    Follows Single Responsibility Principle - only handles token operations.
    """

    def __init__(self):
        self.db = SessionLocal()

    def _ensure_token_dict(self, token: Any) -> Dict[str, Any]:
        """Normalize token to a dict for DB storage and in-memory use.

        - If token is JSON string, parse it.
        - If token is a bare string, wrap as {"access_token": <str>}.
        - If token has a to_dict method, use it.
        - Otherwise, return {} to avoid storing invalid types.
        """
        print(f">>> DEBUG: [_ensure_token_dict] incoming token type: {type(token)}")
        print(
            f">>> DEBUG: [_ensure_token_dict] incoming token is dict: {isinstance(token, dict)}"
        )

        try:
            if isinstance(token, dict):
                print(
                    f">>> DEBUG: [_ensure_token_dict] token already dict, returning as-is"
                )
                return token
            if isinstance(token, str):
                print(
                    f">>> DEBUG: [_ensure_token_dict] token is string, attempting to parse"
                )
                try:
                    parsed = json.loads(token)
                    if isinstance(parsed, dict):
                        print(
                            f">>> DEBUG: [_ensure_token_dict] successfully parsed to dict"
                        )
                        return parsed
                    if isinstance(parsed, str):
                        # A plain string inside JSON – treat as access token
                        print(
                            f">>> DEBUG: [_ensure_token_dict] parsed to string, wrapping"
                        )
                        return {"access_token": parsed}
                    # Unsupported JSON type; fallback
                    print(
                        f">>> DEBUG: [_ensure_token_dict] unsupported JSON type, returning empty"
                    )
                    return {}
                except json.JSONDecodeError:
                    # Not JSON; treat as plain access token string
                    print(
                        f">>> DEBUG: [_ensure_token_dict] not JSON, wrapping as access_token"
                    )
                    return {"access_token": token}
            # Objects with to_dict support
            if hasattr(token, "to_dict") and callable(getattr(token, "to_dict")):
                print(f">>> DEBUG: [_ensure_token_dict] using to_dict() method")
                return token.to_dict()  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"Failed to normalize token to dict: {e}")
            print(
                f">>> DEBUG: [_ensure_token_dict] exception during normalization: {e}"
            )

        print(f">>> DEBUG: [_ensure_token_dict] fallback to empty dict")
        return {}

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
            logger.debug(
                "Storing OAuth token",
                extra={
                    "context": {
                        "user_id": user_id,
                        "provider": provider,
                        "provider_user_id": provider_user_id,
                        "token_type": type(token).__name__,
                        "has_access_token": (
                            "access_token" in token
                            if isinstance(token, dict)
                            else False
                        ),
                    }
                },
            )

            # Normalize token to dict and log type before persisting
            token_dict: Dict[str, Any] = self._ensure_token_dict(token)
            print(
                f">>> DEBUG: [SAVE] normalized token type before DB persist: {type(token_dict)}"
            )
            print(
                f">>> DEBUG: [SAVE] normalized token is dict: {isinstance(token_dict, dict)}"
            )
            if isinstance(token_dict, dict):
                print(f">>> DEBUG: [SAVE] token has {len(token_dict)} keys")
                print(f">>> DEBUG: [SAVE] token keys: {list(token_dict.keys())}")

            # Check if record already exists by provider_user_id (unique constraint)
            existing = (
                self.db.query(OAuth)
                .filter(
                    OAuth.provider_user_id == provider_user_id,
                    OAuth.provider == provider,
                )
                .first()
            )

            if existing:
                # Update existing token - use setattr for SQLAlchemy attributes
                logger.debug(
                    "Updating existing OAuth record",
                    extra={
                        "context": {
                            "provider_user_id": provider_user_id,
                            "provider": provider,
                        }
                    },
                )
                setattr(existing, "token", token_dict)
                setattr(
                    existing, "user_id", int(user_id)
                )  # Update user_id in case it changed
                self.db.commit()
                logger.info(
                    f"Updated OAuth token for {provider} user {provider_user_id}"
                )
            else:
                # Create new token record
                logger.debug(
                    "Creating new OAuth record",
                    extra={
                        "context": {
                            "provider_user_id": provider_user_id,
                            "provider": provider,
                        }
                    },
                )
                oauth_record = OAuth()
                # Set all attributes after creation using setattr
                setattr(oauth_record, "provider", provider)
                setattr(oauth_record, "token", token_dict)
                setattr(oauth_record, "provider_user_id", provider_user_id)
                setattr(oauth_record, "user_id", int(user_id))

                self.db.add(oauth_record)

            self.db.commit()
            logger.info(
                "OAuth token committed to database",
                extra={
                    "context": {
                        "user_id": user_id,
                        "provider": provider,
                        "provider_user_id": provider_user_id,
                    }
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to store OAuth token",
                extra={
                    "context": {
                        "user_id": user_id,
                        "provider": provider,
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            self.db.rollback()
            return False
        finally:
            self.db.close()

    def get_user_access_token(
        self, user_id: str, provider: str = PROVIDER_GOOGLE_CALENDAR
    ) -> Optional[str]:
        """
        Get Google access token for user.
        Checks expiration and refreshes if needed.

        Args:
            user_id: User identifier
            provider: OAuth provider name (default: google_calendar)

        Returns:
            Access token if available and valid, None otherwise
        """
        try:
            # Query from database storage
            oauth_record = (
                self.db.query(OAuth)
                .filter(OAuth.user_id == int(user_id), OAuth.provider == provider)
                .first()
            )

            # Diagnostic: Log token retrieval attempt
            logger.debug(
                "Retrieving OAuth token from database",
                extra={
                    "context": {
                        "user_id": user_id,
                        "provider": provider,
                        "found": bool(oauth_record),
                    }
                },
            )

            if oauth_record and getattr(oauth_record, "token", None):
                # OAuth record stores token as JSON string
                import json

                try:
                    token_value = getattr(oauth_record, "token", None)
                    print(
                        f">>> DEBUG: [LOAD] raw token type from DB: {type(token_value)}"
                    )
                    print(
                        f">>> DEBUG: [LOAD] raw token is dict: {isinstance(token_value, dict)}"
                    )

                    token_data = (
                        json.loads(token_value)
                        if isinstance(token_value, str)
                        else token_value
                    )
                    print(
                        f">>> DEBUG: [LOAD] parsed token type in memory: {type(token_data)}"
                    )
                    print(
                        f">>> DEBUG: [LOAD] parsed token is dict: {isinstance(token_data, dict)}"
                    )

                    if token_data and isinstance(token_data, dict):
                        access_token = token_data.get("access_token")
                        expires_at = token_data.get("expires_at")
                        refresh_token = token_data.get("refresh_token")

                        if access_token:
                            # Check if token is expired (with 5-minute safety buffer)
                            now = datetime.now(timezone.utc)
                            if expires_at:
                                if isinstance(expires_at, str):
                                    expires_at = datetime.fromisoformat(
                                        expires_at.replace("Z", "+00:00")
                                    )
                                elif isinstance(expires_at, (int, float)):
                                    # Make timezone-aware when parsing from timestamp
                                    expires_at = datetime.fromtimestamp(
                                        expires_at, tz=timezone.utc
                                    )

                                # Add safety buffer (increased to 10 minutes for better proactive refresh)
                                expires_at_with_buffer = expires_at - timedelta(
                                    minutes=10
                                )

                                if now >= expires_at_with_buffer and refresh_token:
                                    # Token expired or will expire soon, try to refresh
                                    logger.info(
                                        f"Access token expired or expiring soon for user {user_id}, attempting proactive refresh"
                                    )
                                    new_token = self.refresh_access_token(
                                        user_id, provider
                                    )
                                    return new_token
                                else:
                                    logger.info(
                                        f"Retrieved valid token from database for user {user_id}"
                                    )
                                    return access_token
                            else:
                                # No expiration info, assume valid
                                logger.info(
                                    f"Retrieved token from database for user {user_id} (no expiration info)"
                                )
                                return access_token
                except (json.JSONDecodeError, AttributeError, ValueError) as e:
                    logger.warning(f"Error parsing token for user {user_id}: {str(e)}")

            logger.warning(f"No valid access token found for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving access token for user {user_id}: {str(e)}")
            return None
        finally:
            self.db.close()

    def refresh_access_token(
        self, user_id: str, provider: str = PROVIDER_GOOGLE_CALENDAR
    ) -> Optional[str]:
        """
        Refresh Google access token using refresh token.

        Args:
            user_id: User identifier
            provider: OAuth provider name (default: google_calendar)

        Returns:
            New access token if refresh successful, None otherwise
        """
        try:
            # Get current token data from database
            oauth_record = (
                self.db.query(OAuth)
                .filter(OAuth.user_id == int(user_id), OAuth.provider == provider)
                .first()
            )

            if not oauth_record:
                logger.warning(f"No OAuth record found for user {user_id}")
                return None

            import json

            token_value = getattr(oauth_record, "token", None)
            if not token_value:
                logger.warning(f"No token data found for user {user_id}")
                return None

            print(
                f">>> DEBUG: [LOAD] raw token type from DB (refresh): {type(token_value)}"
            )
            print(
                f">>> DEBUG: [LOAD] raw token is dict (refresh): {isinstance(token_value, dict)}"
            )

            token_data = (
                json.loads(token_value) if isinstance(token_value, str) else token_value
            )
            print(
                f">>> DEBUG: [LOAD] parsed token type in memory (refresh): {type(token_data)}"
            )
            print(
                f">>> DEBUG: [LOAD] parsed token is dict (refresh): {isinstance(token_data, dict)}"
            )

            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                logger.warning(f"No refresh token found for user {user_id}")
                return None

            # Get client credentials from config
            client_id = current_app.config.get("GOOGLE_OAUTH_CLIENT_ID")
            client_secret = current_app.config.get("GOOGLE_OAUTH_CLIENT_SECRET")

            if not client_id or not client_secret:
                logger.error("Google OAuth client credentials not configured")
                return None

            # Make refresh request to Google OAuth endpoint
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post(token_url, data=data, timeout=30)

            if response.status_code == 200:
                new_token_data = response.json()
                new_access_token = new_token_data.get("access_token")
                expires_in = new_token_data.get("expires_in", 3600)  # Default 1 hour

                if new_access_token:
                    # Calculate new expiration date
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=expires_in
                    )

                    logger.info(
                        f"Token refresh successful for user {user_id}. "
                        f"New token expires at: {expires_at.isoformat()}, "
                        f"Expires in: {expires_in} seconds"
                    )

                    # Update token data
                    updated_token_data = token_data.copy()
                    updated_token_data["access_token"] = new_access_token
                    updated_token_data["expires_at"] = expires_at.isoformat()
                    # Google may return a new refresh_token
                    if "refresh_token" in new_token_data:
                        updated_token_data["refresh_token"] = new_token_data[
                            "refresh_token"
                        ]
                        logger.info(f"New refresh token received for user {user_id}")

                    # Update database
                    print(
                        f">>> DEBUG: [SAVE] updated token type before DB persist (refresh): {type(updated_token_data)}"
                    )
                    print(
                        f">>> DEBUG: [SAVE] updated token is dict (refresh): {isinstance(updated_token_data, dict)}"
                    )
                    setattr(oauth_record, "token", updated_token_data)
                    self.db.commit()

                    logger.info(
                        f"Successfully refreshed and stored access token for user {user_id}"
                    )
                    return new_access_token
                else:
                    logger.error(
                        f"No access token in refresh response for user {user_id}"
                    )
                    return None
            else:
                logger.error(
                    f"Failed to refresh token for user {user_id}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Request error refreshing token for user {user_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error refreshing token for user {user_id}: {str(e)}")
            return None
        finally:
            self.db.close()

    def is_token_valid(
        self, user_id: str, provider: str = PROVIDER_GOOGLE_CALENDAR
    ) -> bool:
        """
        Check if user's OAuth token is valid.

        Args:
            user_id: User identifier
            provider: OAuth provider name (default: google_calendar)

        Returns:
            True if token is valid, False otherwise
        """
        try:
            access_token = self.get_user_access_token(user_id, provider)
            if not access_token:
                return False

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

    def revoke_user_token(
        self, user_id: str, provider: str = PROVIDER_GOOGLE_CALENDAR
    ) -> bool:
        """
        Revoke Google access token for user.

        Args:
            user_id: User identifier
            provider: OAuth provider name (default: google_calendar)

        Returns:
            True if revocation successful, False otherwise
        """
        try:
            access_token = self.get_user_access_token(user_id, provider)
            if not access_token:
                logger.info(f"No token to revoke for user {user_id}")
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
                    .filter(OAuth.user_id == int(user_id), OAuth.provider == provider)
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
        Get Google OAuth authorization URL for manual/testing flows.

        Note:
            - The primary OAuth flow is handled by the Flask-Dance blueprints configured in
              `app.main`. This helper is intended for manual testing or diagnostics and may
              use scopes that differ slightly from the production blueprint configuration.
            - This generates a URL with calendar scopes. For login-only, use the google_login
              blueprint endpoint directly.

        Returns:
            Authorization URL for redirecting user (manual usage only)
        """
        try:
            # This would typically be handled by Flask-Dance blueprint
            # But we can provide the URL for manual authorization
            import os
            from urllib.parse import urlencode

            params = {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "redirect_uri": os.getenv(
                    "GOOGLE_OAUTH_REDIRECT_URL",
                    "http://localhost:5000/auth/calendar/google_calendar/authorized",
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
