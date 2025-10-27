"""
OAuth Provider Constants

Centralized constants for OAuth provider names to ensure consistency
across blueprint creation, storage, and database queries.
"""

# Google OAuth provider name - used for:
# - Google OAuth blueprint name (google_oauth_bp.name)
# - Database queries (OAuth.provider filter)
# - Storage identification
PROVIDER_GOOGLE = "google"
