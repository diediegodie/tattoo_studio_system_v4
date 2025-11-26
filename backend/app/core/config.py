"""
Centralized configuration module for application-wide settings.

This module provides centralized configuration for timezone handling,
ensuring consistency across all datetime operations in the application.
"""

import os
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# ===========================
# Timezone Configuration
# ===========================


def get_app_timezone() -> ZoneInfo:
    """
    Get the application timezone from environment variable.

    Returns:
        ZoneInfo: Application timezone (defaults to UTC if not configured)

    Environment Variables:
        TZ: Timezone identifier (e.g., 'America/Sao_Paulo', 'UTC')
            Default: 'UTC' (safe fallback)
            Production: Should be set to 'America/Sao_Paulo'

    Examples:
        >>> # In .env file:
        >>> # TZ=America/Sao_Paulo
        >>> tz = get_app_timezone()
        >>> print(tz)  # America/Sao_Paulo
    """
    # Default to UTC when TZ is not set to keep deterministic behavior in tests
    # and align with baseline expectations; production can override via TZ.
    tz_name = os.getenv("TZ", "UTC")

    try:
        tz = ZoneInfo(tz_name)
        return tz
    except Exception as e:
        # Fallback to UTC if invalid timezone specified
        logger.warning(
            f"Invalid timezone '{tz_name}' specified in TZ environment variable. "
            f"Falling back to UTC. Error: {e}"
        )
        return ZoneInfo("UTC")


# Global timezone instance - initialized once at import time
APP_TZ = get_app_timezone()


def log_timezone_config():
    """
    Log the active timezone configuration.

    Should be called during application startup to provide visibility
    into the timezone being used for date/time operations.
    """
    logger.info(
        "Timezone configuration initialized",
        extra={
            "timezone": str(APP_TZ),
            "tz_env_var": os.getenv("TZ", "UTC"),
        },
    )


# ===========================
# Extrato Backup Configuration
# ===========================


def get_extrato_backup_requirement() -> bool:
    """
    Get whether backup verification is required before extrato generation.

    Returns:
        bool: True if backup is required, False if optional

    Environment Variables:
        EXTRATO_REQUIRE_BACKUP: Whether to require backup verification
            Default: 'true' (safe default - require backup)
            Production: Should be 'true' for safety
            Development: Can be 'false' for flexibility

    Truthy values: "true", "1", "yes" (case-insensitive)
    Falsy values: "false", "0", "no" (case-insensitive)

    Examples:
        >>> # In .env file:
        >>> # EXTRATO_REQUIRE_BACKUP=true  # Production (strict)
        >>> # EXTRATO_REQUIRE_BACKUP=false # Development (flexible)
        >>> require_backup = get_extrato_backup_requirement()
    """
    require_backup_str = os.getenv("EXTRATO_REQUIRE_BACKUP", "true")

    require_backup = require_backup_str.lower() in ("true", "1", "yes")

    if not require_backup:
        logger.warning(
            "Backup verification is DISABLED - extrato can be generated without backup check",
            extra={
                "EXTRATO_REQUIRE_BACKUP": require_backup_str,
                "environment": os.getenv("FLASK_ENV", "unknown"),
            },
        )

    return require_backup


# Global backup requirement flag
EXTRATO_REQUIRE_BACKUP = get_extrato_backup_requirement()


def log_extrato_config():
    """
    Log the active extrato backup configuration.

    Should be called during application startup to provide visibility
    into the backup verification requirement.
    """
    logger.info(
        "Extrato backup configuration initialized",
        extra={
            "require_backup": EXTRATO_REQUIRE_BACKUP,
            "env_var": os.getenv("EXTRATO_REQUIRE_BACKUP", "true (default)"),
        },
    )


# ===========================
# Health Check Configuration
# ===========================


def get_health_check_token() -> str | None:
    """
    Get the health check token from environment variable.

    Returns:
        str | None: Health check token if configured, None otherwise

    Environment Variables:
        HEALTH_CHECK_TOKEN: Token required for internal health checks
            Default: None (health checks disabled if not set)
            Production: Should be set to a secure random string
            Development: Can be set for testing

    Examples:
        >>> # In .env file:
        >>> # HEALTH_CHECK_TOKEN=secure-random-token-123
        >>> token = get_health_check_token()
    """
    return os.getenv("HEALTH_CHECK_TOKEN", None)


# Global health check token
HEALTH_CHECK_TOKEN = get_health_check_token()


# ===========================
# Authorization Configuration
# ===========================


def get_authorized_emails() -> set[str]:
    """
    Get the set of authorized email addresses from environment variable.

    Returns:
        set[str]: Set of authorized email addresses (lowercased for comparison)

    Environment Variables:
        AUTHORIZED_EMAILS: Comma-separated list of authorized email addresses
            Default: Empty (no users authorized by default)
            Production: Should contain admin email addresses
            Development: Can contain test email addresses

    Examples:
        >>> # In .env file:
        >>> # AUTHORIZED_EMAILS=admin@example.com,user@example.com,dev@example.com
        >>> authorized = get_authorized_emails()
        >>> print(authorized)  # {'admin@example.com', 'user@example.com', 'dev@example.com'}
    """
    emails_str = os.getenv("AUTHORIZED_EMAILS", "")

    if not emails_str.strip():
        logger.warning(
            "AUTHORIZED_EMAILS is not configured - no users will be authorized by default",
            extra={
                "environment": os.getenv("FLASK_ENV", "unknown"),
            },
        )
        return set()

    # Split by comma, strip whitespace, lowercase for case-insensitive comparison
    emails = {email.strip().lower() for email in emails_str.split(",") if email.strip()}

    logger.info(
        "Authorized emails configuration loaded",
        extra={
            "email_count": len(emails),
            "environment": os.getenv("FLASK_ENV", "unknown"),
        },
    )

    return emails


def is_email_authorized(email: str) -> bool:
    """
    Check if an email address is authorized.

    Args:
        email: Email address to check

    Returns:
        bool: True if email is authorized, False otherwise

    Examples:
        >>> # With AUTHORIZED_EMAILS=admin@example.com,user@example.com
        >>> is_email_authorized("admin@example.com")  # True
        >>> is_email_authorized("ADMIN@EXAMPLE.COM")  # True (case-insensitive)
        >>> is_email_authorized("hacker@evil.com")    # False
    """
    if not email:
        return False

    authorized = get_authorized_emails()

    # Empty set means no authorization configured - reject all
    if not authorized:
        return False

    return email.strip().lower() in authorized


# Global authorized emails set - cached at module load time
AUTHORIZED_EMAILS = get_authorized_emails()


def log_authorization_config():
    """
    Log the active authorization configuration.

    Should be called during application startup to provide visibility
    into the authorization settings (without exposing actual emails).
    """
    logger.info(
        "Authorization configuration initialized",
        extra={
            "authorized_count": len(AUTHORIZED_EMAILS),
            "env_var_set": bool(os.getenv("AUTHORIZED_EMAILS")),
        },
    )


# ===========================
# Feature Flags Configuration
# ===========================


def get_unified_session_payment_flow_enabled() -> bool:
    """
    Get whether the unified session+payment flow is enabled.

    Returns:
        bool: True if unified flow is enabled, False to use legacy flow

    Environment Variables:
        UNIFIED_SESSION_PAYMENT_FLOW: Whether to enable unified flow
            Default: 'false' (safe default - use legacy flow)
            Phase 1: Should be 'false' (schema changes only, no behavior change)
            Phase 2: Can be enabled for canary rollout (10% → 100%)
            Phase 3: Should be 'true' for full deployment

    Truthy values: "true", "1", "yes" (case-insensitive)
    Falsy values: "false", "0", "no" (case-insensitive)

    Examples:
        >>> # In .env file:
        >>> # UNIFIED_SESSION_PAYMENT_FLOW=false  # Phase 1 (schema only)
        >>> # UNIFIED_SESSION_PAYMENT_FLOW=true   # Phase 3 (full rollout)
        >>> unified_enabled = get_unified_session_payment_flow_enabled()
    """
    flag_str = os.getenv("UNIFIED_SESSION_PAYMENT_FLOW", "false")
    return flag_str.strip().lower() in ("true", "1", "yes")


# Global feature flag - cached at module load time
UNIFIED_SESSION_PAYMENT_FLOW = get_unified_session_payment_flow_enabled()


def log_feature_flags():
    """
    Log the active feature flag configuration.

    Should be called during application startup to provide visibility
    into which features are enabled.
    """
    logger.info(
        "Feature flags configuration initialized",
        extra={
            "unified_session_payment_flow": UNIFIED_SESSION_PAYMENT_FLOW,
            "env_var_value": os.getenv("UNIFIED_SESSION_PAYMENT_FLOW", "false"),
        },
    )
