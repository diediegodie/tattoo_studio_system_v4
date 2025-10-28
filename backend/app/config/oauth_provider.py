"""
OAuth Provider Constants

Centralized constants for OAuth provider names to ensure consistency
across blueprint creation, storage, and database queries.
"""

# Google OAuth provider name - DEPRECATED: Use PROVIDER_GOOGLE_LOGIN instead
# Kept for backwards compatibility during migration
PROVIDER_GOOGLE = "google"

# Google Login provider - used for user authentication only
# Scopes: openid, email, profile
PROVIDER_GOOGLE_LOGIN = "google_login"

# Google Calendar provider - used for calendar token authorization only
# Scopes: calendar.readonly, calendar.events
PROVIDER_GOOGLE_CALENDAR = "google_calendar"
