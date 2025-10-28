"""
Tests for EXTRATO_REQUIRE_BACKUP toggle behavior.

This test suite validates the backup verification toggle functionality:
- Strict mode (EXTRATO_REQUIRE_BACKUP=true): blocks when backup missing
- Flexible mode (EXTRATO_REQUIRE_BACKUP=false): allows with warning when backup missing
- Backup exists: always succeeds regardless of toggle
- Default behavior: require backup (safe default)
- Integration with atomic generation

Run these tests BEFORE implementing the toggle to confirm they fail (expected).
After implementation, all tests should pass.
"""

import os
from unittest.mock import patch, MagicMock
import pytest


class TestBackupToggle:
    """Test backup verification toggle behavior."""

    def test_backup_required_blocks_when_missing(self):
        """
        Test that EXTRATO_REQUIRE_BACKUP=true blocks when backup missing.

        Expected behavior (strict mode):
        - Backup verification checks BackupService
        - BackupService returns False (no backup)
        - verify_backup_before_transfer returns False (blocks execution)
        - Error logged
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "true"}):
            # Reload config to pick up environment variable
            import importlib
            from app.core import config

            importlib.reload(config)

            with patch("app.services.extrato_core.BackupService") as mock_service:
                # Mock: backup does NOT exist
                mock_service.return_value.verify_backup_exists.return_value = False

                from app.services.extrato_core import verify_backup_before_transfer

                result = verify_backup_before_transfer(2025, 10)

                # Should block execution
                assert (
                    result is False
                ), "Should return False when backup missing and EXTRATO_REQUIRE_BACKUP=true"

                # Verify BackupService was called
                mock_service.return_value.verify_backup_exists.assert_called_once_with(
                    2025, 10
                )

    def test_backup_not_required_allows_when_missing(self):
        """
        Test that EXTRATO_REQUIRE_BACKUP=false allows when backup missing.

        Expected behavior (flexible mode):
        - Backup verification checks BackupService
        - BackupService returns False (no backup)
        - verify_backup_before_transfer returns True (allows execution with warning)
        - Warning logged
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "false"}):
            # Reload config to pick up environment variable
            import importlib
            from app.core import config

            importlib.reload(config)

            with patch("app.services.extrato_core.BackupService") as mock_service:
                # Mock: backup does NOT exist
                mock_service.return_value.verify_backup_exists.return_value = False

                from app.services.extrato_core import verify_backup_before_transfer

                result = verify_backup_before_transfer(2025, 10)

                # Should allow execution with warning
                assert (
                    result is True
                ), "Should return True when backup missing and EXTRATO_REQUIRE_BACKUP=false"

                # Verify BackupService was called
                mock_service.return_value.verify_backup_exists.assert_called_once_with(
                    2025, 10
                )

    def test_backup_exists_always_succeeds(self):
        """
        Test that backup existence always succeeds regardless of toggle.

        Expected behavior:
        - When backup exists, both strict and flexible modes return True
        - No difference in behavior when backup is present
        """
        for toggle_value in ["true", "false"]:
            with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": toggle_value}):
                # Reload config to pick up environment variable
                import importlib
                from app.core import config

                importlib.reload(config)

                with patch("app.services.extrato_core.BackupService") as mock_service:
                    # Mock: backup EXISTS
                    mock_service.return_value.verify_backup_exists.return_value = True

                    from app.services.extrato_core import verify_backup_before_transfer

                    result = verify_backup_before_transfer(2025, 10)

                    # Should always succeed when backup exists
                    assert (
                        result is True
                    ), f"Should return True when backup exists (toggle={toggle_value})"

                    # Verify BackupService was called
                    mock_service.return_value.verify_backup_exists.assert_called_with(
                        2025, 10
                    )

    def test_default_is_required(self):
        """
        Test that default behavior is to require backup.

        Expected behavior:
        - When EXTRATO_REQUIRE_BACKUP is not set, default to True
        - This is the safe default for production
        """
        # Clear environment variable
        with patch.dict(os.environ, {}, clear=True):
            # Remove EXTRATO_REQUIRE_BACKUP if it exists
            os.environ.pop("EXTRATO_REQUIRE_BACKUP", None)

            # Reload config to pick up default
            import importlib
            from app.core import config

            importlib.reload(config)

            # Check that default is True (require backup)
            assert (
                config.EXTRATO_REQUIRE_BACKUP is True
            ), "Default should be True (require backup)"

    def test_atomic_generation_respects_toggle_strict(self):
        """
        Test that atomic generation respects backup toggle in STRICT mode.

        Expected behavior:
        - EXTRATO_REQUIRE_BACKUP=true
        - Backup missing (verify returns False)
        - generate_extrato_with_atomic_transaction should return False (blocked)
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "true"}):
            # Reload config
            import importlib
            from app.core import config

            importlib.reload(config)

            with patch(
                "app.services.extrato_atomic.verify_backup_before_transfer"
            ) as mock_verify:
                # Mock: backup verification fails (strict mode blocks)
                mock_verify.return_value = False

                from app.services.extrato_atomic import (
                    generate_extrato_with_atomic_transaction,
                )

                # Should return False without attempting generation
                result = generate_extrato_with_atomic_transaction(
                    mes=10, ano=2025, force=False
                )

                assert (
                    result is False
                ), "Should return False when backup verification fails in strict mode"
                mock_verify.assert_called_once_with(2025, 10)

    def test_atomic_generation_respects_toggle_flexible(self):
        """
        Test that atomic generation respects backup toggle in FLEXIBLE mode.

        Expected behavior:
        - EXTRATO_REQUIRE_BACKUP=false
        - Backup missing but verify returns True (flexible mode allows)
        - generate_extrato_with_atomic_transaction should proceed

        Note: This test mocks the entire transaction to avoid database dependencies.
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "false"}):
            # Reload config
            import importlib
            from app.core import config

            importlib.reload(config)

            with patch(
                "app.services.extrato_atomic.verify_backup_before_transfer"
            ) as mock_verify:
                # Mock: backup verification allows (flexible mode)
                mock_verify.return_value = True

                # Mock database operations to avoid actual DB calls
                with patch("app.services.extrato_atomic.SessionLocal") as mock_session:
                    mock_db = MagicMock()
                    mock_session.return_value = mock_db

                    # Mock query results (empty data for simplicity)
                    with patch("app.services.extrato_atomic.query_data") as mock_query:
                        mock_query.return_value = ([], [], [], [])

                        with patch(
                            "app.services.extrato_atomic.check_existing_extrato"
                        ) as mock_check:
                            mock_check.return_value = True

                            from app.services.extrato_atomic import (
                                generate_extrato_with_atomic_transaction,
                            )

                            # Should proceed (won't fully succeed due to mocks, but won't block)
                            result = generate_extrato_with_atomic_transaction(
                                mes=10, ano=2025, force=False
                            )

                            # Verify backup check was called
                            mock_verify.assert_called_once_with(2025, 10)

    def test_backup_verification_error_handling_strict(self):
        """
        Test error handling during backup verification in STRICT mode.

        Expected behavior:
        - EXTRATO_REQUIRE_BACKUP=true
        - BackupService raises exception
        - verify_backup_before_transfer returns False (fail-closed, safe)
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "true"}):
            # Reload config
            import importlib
            from app.core import config

            importlib.reload(config)

            with patch("app.services.extrato_core.BackupService") as mock_service:
                # Mock: BackupService raises exception
                mock_service.return_value.verify_backup_exists.side_effect = Exception(
                    "Connection error"
                )

                from app.services.extrato_core import verify_backup_before_transfer

                result = verify_backup_before_transfer(2025, 10)

                # Should fail-closed (safe): return False
                assert (
                    result is False
                ), "Should return False on error in strict mode (fail-closed)"

    def test_backup_verification_error_handling_flexible(self):
        """
        Test error handling during backup verification in FLEXIBLE mode.

        Expected behavior:
        - EXTRATO_REQUIRE_BACKUP=false
        - BackupService raises exception
        - verify_backup_before_transfer returns True (allows with warning)
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "false"}):
            # Reload config
            import importlib
            from app.core import config

            importlib.reload(config)

            with patch("app.services.extrato_core.BackupService") as mock_service:
                # Mock: BackupService raises exception
                mock_service.return_value.verify_backup_exists.side_effect = Exception(
                    "Connection error"
                )

                from app.services.extrato_core import verify_backup_before_transfer

                result = verify_backup_before_transfer(2025, 10)

                # Should allow with warning
                assert (
                    result is True
                ), "Should return True on error in flexible mode (with warning)"


class TestBackupToggleIntegration:
    """Integration tests for backup toggle with config system."""

    def test_config_loading(self):
        """
        Test that config correctly loads and exposes EXTRATO_REQUIRE_BACKUP.
        """
        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "false"}):
            import importlib
            from app.core import config

            importlib.reload(config)

            assert hasattr(
                config, "EXTRATO_REQUIRE_BACKUP"
            ), "config should expose EXTRATO_REQUIRE_BACKUP"
            assert (
                config.EXTRATO_REQUIRE_BACKUP is False
            ), "Should parse 'false' correctly"

        with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": "true"}):
            importlib.reload(config)
            assert (
                config.EXTRATO_REQUIRE_BACKUP is True
            ), "Should parse 'true' correctly"

    def test_multiple_toggle_values(self):
        """
        Test various truthy/falsy values for EXTRATO_REQUIRE_BACKUP.
        """
        truthy_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]
        falsy_values = ["false", "False", "FALSE", "0", "no", "No", "NO"]

        import importlib
        from app.core import config

        for value in truthy_values:
            with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": value}):
                importlib.reload(config)
                assert (
                    config.EXTRATO_REQUIRE_BACKUP is True
                ), f"'{value}' should be truthy"

        for value in falsy_values:
            with patch.dict(os.environ, {"EXTRATO_REQUIRE_BACKUP": value}):
                importlib.reload(config)
                assert (
                    config.EXTRATO_REQUIRE_BACKUP is False
                ), f"'{value}' should be falsy"


# Run tests with: pytest backend/tests/unit/test_extrato_backup_toggle.py -v
