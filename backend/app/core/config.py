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
