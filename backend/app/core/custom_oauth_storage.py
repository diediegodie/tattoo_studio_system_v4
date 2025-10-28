"""
Custom OAuth Storage for Flask-Dance
Extends SQLAlchemyStorage to support provider_user_id field

This custom storage backend is required because the project's OAuth model
includes a provider_user_id field (NOT NULL) that Flask-Dance's default
SQLAlchemyStorage doesn't populate.

Without this custom storage, OAuth token persistence fails silently with
IntegrityError, breaking both login and calendar authorization flows.
"""

import logging
from typing import Optional, Any, Union, Callable
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CustomOAuthStorage(SQLAlchemyStorage):
    """
    Custom storage backend for Flask-Dance OAuth tokens.

    Extends SQLAlchemyStorage to support the custom provider_user_id field
    required by our OAuth model schema.

    The standard Flask-Dance SQLAlchemyStorage expects this OAuth model:
    - id (primary key)
    - provider (OAuth provider name)
    - created_at (timestamp)
    - token (JSON blob)
    - user_id (optional, for user association)

    Our OAuth model adds:
    - provider_user_id (NOT NULL) - Google user ID, Facebook ID, etc.

    This custom storage fetches the provider-specific user ID from the
    OAuth provider's API (e.g., /oauth2/v2/userinfo for Google) and
    includes it when creating OAuth records.
    """

    # Type annotations for attributes from parent class
    session: Union[Session, Callable[[], Session]]
    model: Any
    user_required: bool

    def __init__(
        self,
        model,
        session,
        user=None,
        user_id=None,
        user_required=None,
        anon_user=None,
        cache=None,
    ):
        """
        Initialize CustomOAuthStorage with proper parent class initialization.

        This __init__ is CRITICAL - without it, Flask-Dance cannot use this
        storage backend because self.session, self.model, etc. are never set.

        Args:
            model: SQLAlchemy model class (OAuth)
            session: SQLAlchemy session or session factory
            user: User object or callable returning user (e.g., lambda: current_user)
            user_id: User ID value or callable
            user_required: Whether user must be present to store tokens
            anon_user: Anonymous user class
            cache: Flask-Caching instance (optional)
        """
        # Call parent constructor to initialize all base attributes
        # This sets self.model, self.session, self.user, self.user_id, etc.
        super().__init__(
            model=model,
            session=session,
            user=user,
            user_id=user_id,
            user_required=user_required,
            anon_user=anon_user,
            cache=cache,
        )

        logger.info(
            f"CustomOAuthStorage initialized with model={model.__name__}, "
            f"user_required={self.user_required}"
        )

    def _get_session(self) -> Session:
        """
        Get the actual SQLAlchemy session.

        Handles both callable session factories and direct session objects.
        This is CRITICAL because main.py passes SessionLocal (a factory function),
        not SessionLocal() (an actual session).

        Returns:
            SQLAlchemy session object
        """
        if callable(self.session):
            # Session is a factory function like SessionLocal
            return self.session()
        else:
            # Session is already a session object
            return self.session

    def set(self, blueprint, token, user=None, user_id=None) -> None:
        """
        Store OAuth token with provider_user_id.

        Overrides SQLAlchemyStorage.set() to fetch and include the
        provider_user_id field required by our OAuth model.

        Args:
            blueprint: Flask-Dance blueprint instance
            token: OAuth token dict from provider
            user: Flask-Login user object (optional)
            user_id: User ID (optional, overrides user.id)

        Raises:
            ValueError: If user_required=True and no user provided
            IntegrityError: If database constraints violated
        """
        logger.info(
            f"CustomOAuthStorage.set() called for {blueprint.name}",
            extra={
                "context": {
                    "has_token": bool(token),
                    "user_id": user_id,
                    "has_user": bool(user),
                }
            },
        )

        # Get provider_user_id from OAuth provider API
        provider_user_id = self._fetch_provider_user_id(blueprint, user_id)

        if not provider_user_id:
            logger.error(
                f"Cannot store OAuth token without provider_user_id for {blueprint.name}"
            )
            # Use fallback to prevent complete failure
            # This allows token storage to succeed even if provider API is down
            provider_user_id = f"unknown_{user_id or 'anonymous'}"
            logger.warning(f"Using fallback provider_user_id: {provider_user_id}")

        # Extract user_id from various sources (Flask-Dance pattern)
        uid = self._get_user_id(user, user_id, blueprint)

        # Enforce user_required setting
        if self.user_required and not uid:
            raise ValueError(
                f"Cannot set OAuth token without an associated user for {blueprint.name}"
            )

        # Delete existing token for this provider_user_id + provider combination
        # This prevents duplicate tokens and ensures updates work correctly
        # CRITICAL: Use _get_session() to handle callable session factory
        session: Session = self._get_session()

        try:
            existing_query = session.query(self.model).filter_by(
                provider=blueprint.name, provider_user_id=provider_user_id
            )
            deleted_count = existing_query.delete()

            if deleted_count > 0:
                logger.debug(
                    f"Deleted {deleted_count} existing OAuth record(s) for "
                    f"{blueprint.name} user {provider_user_id}"
                )
        except Exception as e:
            logger.warning(f"Error deleting existing OAuth records: {e}", exc_info=True)
            # Continue anyway - INSERT will fail if duplicate exists due to unique constraint

        # Create new OAuth record with all required fields
        kwargs = {
            "provider": blueprint.name,
            "provider_user_id": provider_user_id,
            "token": token,
        }

        if uid:
            kwargs["user_id"] = uid

        # Log for debugging (without exposing token contents)
        logger.debug(
            f"Creating OAuth record: provider={blueprint.name}, "
            f"provider_user_id={provider_user_id}, user_id={uid}, "
            f"has_access_token={'access_token' in token if isinstance(token, dict) else 'unknown'}"
        )

        try:
            # Create and add new record
            session.add(self.model(**kwargs))
            session.commit()

            logger.info(
                f"✅ OAuth token stored successfully for {blueprint.name} "
                f"user {provider_user_id} (internal user_id={uid})"
            )

            # Invalidate cache (Flask-Dance caching mechanism)
            self.cache.delete(
                self.make_cache_key(blueprint=blueprint, user=user, user_id=user_id)
            )

        except Exception as e:
            session.rollback()
            logger.error(
                f"❌ Failed to store OAuth token for {blueprint.name}: {e}",
                exc_info=True,
            )
            raise

    def _fetch_provider_user_id(
        self, blueprint, fallback_user_id=None
    ) -> Optional[str]:
        """
        Fetch provider-specific user ID from OAuth provider API.

        For Google OAuth, calls /oauth2/v2/userinfo to get the Google user ID.
        Other providers would need different API endpoints.

        Args:
            blueprint: Flask-Dance blueprint with active session
            fallback_user_id: Fallback value if API call fails

        Returns:
            Provider user ID string, or fallback value, or None
        """
        logger.info(f"Attempting to fetch provider_user_id for {blueprint.name}")

        try:
            # Google OAuth: Fetch user info
            # Note: This endpoint works for both google_login and google_calendar
            # because both use Google OAuth with valid access tokens
            logger.debug(
                f"Calling blueprint.session.get('/oauth2/v2/userinfo') for {blueprint.name}"
            )
            resp = blueprint.session.get("/oauth2/v2/userinfo")

            logger.info(
                f"Google API response for {blueprint.name}",
                extra={
                    "context": {
                        "status_code": (
                            resp.status_code
                            if hasattr(resp, "status_code")
                            else "unknown"
                        ),
                        "ok": resp.ok if hasattr(resp, "ok") else "unknown",
                    }
                },
            )

            if resp.ok:
                google_info = resp.json()
                logger.debug(f"Google user info keys: {list(google_info.keys())}")
                provider_user_id = str(google_info.get("id", ""))

                if provider_user_id:
                    logger.info(
                        f"✅ Fetched provider_user_id for {blueprint.name}: {provider_user_id}"
                    )
                    return provider_user_id
                else:
                    logger.warning(
                        f"Google user info response missing 'id' field for {blueprint.name}"
                    )
            else:
                logger.error(
                    f"Failed to fetch Google user info for {blueprint.name}: "
                    f"HTTP {resp.status_code}"
                )

        except Exception as e:
            logger.error(
                f"❌ Error fetching provider_user_id for {blueprint.name}: {e}",
                exc_info=True,
            )

        # Return None to let caller decide fallback strategy
        logger.warning(f"Returning None for provider_user_id for {blueprint.name}")
        return None

    def _get_user_id(self, user, user_id, blueprint) -> Optional[int]:
        """
        Extract user ID from various sources.

        Flask-Dance supports multiple ways to specify the user:
        - Explicit user_id parameter
        - User object with .id attribute
        - User object with .get_id() method
        - Blueprint config user_id
        - Blueprint config user

        Args:
            user: Flask-Login user object or None
            user_id: Explicit user ID or None
            blueprint: Flask-Dance blueprint

        Returns:
            User ID as integer, or None
        """
        # Try explicit user_id first
        if user_id:
            return user_id

        # Try self.user_id (from storage config)
        if self.user_id:
            return self.user_id

        # Try blueprint config user_id
        blueprint_user_id = blueprint.config.get("user_id")
        if blueprint_user_id:
            return blueprint_user_id

        # Try user object
        if user:
            # Try .id attribute
            if hasattr(user, "id"):
                user_id_val = getattr(user, "id")
                if isinstance(user_id_val, int):
                    return user_id_val

            # Try .get_id() method (Flask-Login)
            if hasattr(user, "get_id"):
                get_id_method = getattr(user, "get_id", None)
                if callable(get_id_method):
                    try:
                        result = get_id_method()
                        if result is not None:
                            return int(str(result))
                    except (ValueError, TypeError):
                        pass

        # Try self.user (from storage config)
        if self.user:
            user_ref = self.user() if callable(self.user) else self.user
            if user_ref:
                if hasattr(user_ref, "id"):
                    user_id_val = getattr(user_ref, "id")
                    if isinstance(user_id_val, int):
                        return user_id_val
                if hasattr(user_ref, "get_id"):
                    get_id_method = getattr(user_ref, "get_id", None)
                    if callable(get_id_method):
                        try:
                            result = get_id_method()
                            if result is not None:
                                return int(str(result))
                        except (ValueError, TypeError):
                            pass

        # Try blueprint config user
        blueprint_user = blueprint.config.get("user")
        if blueprint_user:
            user_ref = blueprint_user() if callable(blueprint_user) else blueprint_user
            if user_ref:
                if hasattr(user_ref, "id"):
                    user_id_val = getattr(user_ref, "id")
                    if isinstance(user_id_val, int):
                        return user_id_val
                if hasattr(user_ref, "get_id"):
                    get_id_method = getattr(user_ref, "get_id", None)
                    if callable(get_id_method):
                        try:
                            result = get_id_method()
                            if result is not None:
                                return int(str(result))
                        except (ValueError, TypeError):
                            pass

        return None
