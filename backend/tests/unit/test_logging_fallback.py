"""
Unit tests for logging fallback behavior on disk write failures.

Tests verify that the logging system gracefully handles disk failures
by falling back to stdout without crashing the application.
"""

import logging
import os
from unittest.mock import Mock, patch

import pytest

# Mark all tests in this module as logging tests
pytestmark = pytest.mark.logging


@pytest.fixture
def clean_logging():
    """Clean up logging handlers before and after each test."""
    root_logger = logging.getLogger()

    # Store original handlers
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    yield

    # Restore original state
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    for handler in original_handlers:
        root_logger.addHandler(handler)

    root_logger.setLevel(original_level)


@pytest.fixture
def mock_readonly_logs_dir(tmp_path, monkeypatch):
    """Create a read-only logs directory to simulate disk write failure."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    # Make directory read-only
    os.chmod(logs_dir, 0o444)

    # Patch the logs directory path
    from app.core import logging_config

    monkeypatch.setattr(
        logging_config.Path,
        "__truediv__",
        lambda self, other: logs_dir if other == "logs" else tmp_path / other,
    )

    yield logs_dir

    # Restore write permissions for cleanup
    try:
        os.chmod(logs_dir, 0o755)
    except Exception:
        pass


class TestLoggingFallbackOnDiskFailure:
    """Test suite for logging fallback behavior when disk writes fail."""

    def test_logging_fallback_on_file_handler_failure(
        self, clean_logging, capsys, tmp_path
    ):
        """
        Test that when file handler fails to write, logging falls back to stdout
        without raising an exception.
        """
        from app.core.logging_config import setup_logging

        # Create a logs directory that will cause write failures
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Mock the file handler to raise an exception
        with patch("logging.handlers.RotatingFileHandler") as mock_file_handler:
            # Configure mock to raise IOError on initialization
            mock_file_handler.side_effect = IOError("Disk write failed")

            # Setup logging should not crash even if file handler fails
            try:
                setup_logging(
                    app=None,
                    log_level="INFO",
                    enable_sql_echo=False,
                    log_to_file=True,
                    use_json_format=False,
                )

                # Log a test message
                logger = logging.getLogger("test.fallback")
                logger.info("Test message after file handler failure")

                # Capture output
                captured = capsys.readouterr()

                # Verify message appears in stdout (fallback handler)
                assert "Test message after file handler failure" in captured.out
                assert "INFO" in captured.out

            except Exception as e:
                pytest.fail(f"Logging setup crashed with exception: {e}")

    def test_logging_continues_after_file_write_failure(self, clean_logging, capsys):
        """
        Test that after a file write failure, subsequent log messages
        continue to be captured by the fallback handler.
        """
        from app.core.logging_config import setup_logging

        with patch("logging.handlers.RotatingFileHandler") as mock_file_handler:
            # First call raises exception
            mock_file_handler.side_effect = OSError("No space left on device")

            # Setup should succeed with fallback
            setup_logging(
                app=None,
                log_level="INFO",
                enable_sql_echo=False,
                log_to_file=True,
                use_json_format=False,
            )

            logger = logging.getLogger("test.continuous")

            # Log multiple messages
            logger.info("First message")
            logger.warning("Second message")
            logger.error("Third message")

            captured = capsys.readouterr()

            # All messages should appear in stdout
            assert "First message" in captured.out
            assert "Second message" in captured.out
            assert "Third message" in captured.out
            assert captured.out.count("INFO") >= 1
            assert captured.out.count("WARNING") >= 1
            assert captured.out.count("ERROR") >= 1

    def test_logging_with_read_only_directory(self, clean_logging, capsys, tmp_path):
        """
        Test logging behavior when logs directory exists but is read-only.
        """
        from app.core.logging_config import setup_logging

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Mock Path to return our read-only directory
        with patch("app.core.logging_config.Path") as mock_path:
            mock_path.return_value.__truediv__ = lambda self, other: (
                logs_dir if other == "logs" else tmp_path / other
            )
            mock_path.return_value.mkdir = Mock()  # Don't actually create

            # Make log file creation fail
            with patch("logging.handlers.RotatingFileHandler") as mock_handler:
                mock_handler.side_effect = PermissionError("Permission denied: app.log")

                # Should not crash
                setup_logging(
                    app=None,
                    log_level="DEBUG",
                    enable_sql_echo=False,
                    log_to_file=True,
                    use_json_format=False,
                )

                logger = logging.getLogger("test.readonly")
                logger.debug("Debug message")
                logger.info("Info message")

                captured = capsys.readouterr()

                # Messages should still appear via console handler
                assert "Debug message" in captured.out
                assert "Info message" in captured.out

    def test_error_handler_fallback(self, clean_logging, capsys):
        """
        Test that even when both file handlers (app.log and errors.log) fail,
        errors are still logged to stdout.
        """
        from app.core.logging_config import setup_logging

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            # Both file handler creations fail
            mock_handler.side_effect = IOError("Disk full")

            setup_logging(
                app=None,
                log_level="INFO",
                enable_sql_echo=False,
                log_to_file=True,
                use_json_format=False,
            )

            logger = logging.getLogger("test.error_fallback")

            # Log an error
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.error("An error occurred", exc_info=True)

            captured = capsys.readouterr()

            # Error message and traceback should appear in stdout
            assert "An error occurred" in captured.out
            assert "ERROR" in captured.out
            assert "ValueError" in captured.out
            assert "Test exception" in captured.out

    def test_console_handler_always_present(self, clean_logging, capsys):
        """
        Test that console handler is always configured regardless of
        file handler status.
        """
        from app.core.logging_config import setup_logging

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = Exception("Catastrophic disk failure")

            setup_logging(
                app=None,
                log_level="INFO",
                enable_sql_echo=False,
                log_to_file=True,
                use_json_format=False,
            )

            root_logger = logging.getLogger()

            # Verify at least one StreamHandler exists
            stream_handlers = [
                h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
            ]

            assert len(stream_handlers) >= 1, "Console handler should always be present"

            # Verify it works
            logger = logging.getLogger("test.console")
            logger.info("Console handler test")

            captured = capsys.readouterr()
            assert "Console handler test" in captured.out

    def test_logging_with_json_format_fallback(self, clean_logging, capsys):
        """
        Test that JSON formatting works correctly with fallback handler.
        """
        from app.core.logging_config import setup_logging

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = IOError("Write failed")

            setup_logging(
                app=None,
                log_level="INFO",
                enable_sql_echo=False,
                log_to_file=True,
                use_json_format=True,  # JSON format
            )

            logger = logging.getLogger("test.json")
            logger.info("JSON test message", extra={"context": {"user_id": 123}})

            captured = capsys.readouterr()

            # Should see JSON output in stdout
            assert "JSON test message" in captured.out
            # JSON format includes these fields
            assert '"level"' in captured.out or "INFO" in captured.out

    def test_multiple_loggers_after_disk_failure(self, clean_logging, capsys):
        """
        Test that multiple loggers work correctly after disk failure.
        """
        from app.core.logging_config import setup_logging, get_logger

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = IOError("Disk failure")

            setup_logging(
                app=None,
                log_level="INFO",
                enable_sql_echo=False,
                log_to_file=True,
                use_json_format=False,
            )

            # Create multiple loggers
            logger1 = get_logger("module1")
            logger2 = get_logger("module2")
            logger3 = get_logger("app.service")

            logger1.info("Message from module1")
            logger2.warning("Message from module2")
            logger3.error("Message from service")

            captured = capsys.readouterr()

            # All messages should appear
            assert "Message from module1" in captured.out
            assert "Message from module2" in captured.out
            assert "Message from service" in captured.out

    def test_no_exception_propagation_on_handler_error(self, clean_logging, capsys):
        """
        Test that exceptions during handler setup don't propagate
        and crash the application.
        """
        from app.core.logging_config import setup_logging

        # Simulate catastrophic failure
        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = RuntimeError("Unexpected handler error")

            # Should not raise exception
            exception_raised = False
            exception_type = None

            try:
                setup_logging(
                    app=None,
                    log_level="INFO",
                    enable_sql_echo=False,
                    log_to_file=True,
                    use_json_format=False,
                )
            except Exception as e:
                exception_raised = True
                exception_type = type(e).__name__

            # Verify no exception propagated
            if exception_raised:
                pytest.fail(
                    f"Exception propagated from setup_logging: {exception_type}"
                )

            # Logging should still work
            logger = logging.getLogger("test.noprop")
            logger.info("Test after handler error")

            captured = capsys.readouterr()
            assert "Test after handler error" in captured.out

    @pytest.mark.parametrize(
        "error_type,error_msg",
        [
            (IOError, "Input/output error"),
            (OSError, "No space left on device"),
            (PermissionError, "Permission denied"),
            (FileNotFoundError, "Directory not found"),
        ],
    )
    def test_various_disk_errors_handled(
        self, clean_logging, capsys, error_type, error_msg
    ):
        """
        Test that various types of disk-related errors are handled gracefully.
        """
        from app.core.logging_config import setup_logging

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = error_type(error_msg)

            # Should handle any disk-related error
            setup_logging(
                app=None,
                log_level="INFO",
                enable_sql_echo=False,
                log_to_file=True,
                use_json_format=False,
            )

            logger = logging.getLogger("test.various_errors")
            logger.info(f"Test with {error_type.__name__}")

            captured = capsys.readouterr()
            assert error_type.__name__ in captured.out


class TestLoggingIdempotency:
    """Test that fallback behavior is idempotent and consistent."""

    def test_repeated_setup_after_failure(self, clean_logging, capsys):
        """
        Test that setup_logging can be called multiple times after failure
        without issues.
        """
        from app.core.logging_config import setup_logging

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = IOError("Disk failure")

            # Call setup multiple times
            for i in range(3):
                setup_logging(
                    app=None,
                    log_level="INFO",
                    enable_sql_echo=False,
                    log_to_file=True,
                    use_json_format=False,
                )

                logger = logging.getLogger(f"test.repeat_{i}")
                logger.info(f"Message {i}")

            captured = capsys.readouterr()

            # All messages should be present
            assert "Message 0" in captured.out
            assert "Message 1" in captured.out
            assert "Message 2" in captured.out

    def test_handler_cleanup_before_setup(self, clean_logging, capsys):
        """
        Test that existing handlers are properly cleaned up before
        adding new ones.
        """
        from app.core.logging_config import setup_logging

        root_logger = logging.getLogger()

        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = IOError("Disk failure")

            # Setup logging multiple times
            setup_logging(
                app=None, log_level="INFO", enable_sql_echo=False, log_to_file=True
            )
            count_after_first = len(root_logger.handlers)

            setup_logging(
                app=None, log_level="INFO", enable_sql_echo=False, log_to_file=True
            )
            count_after_second = len(root_logger.handlers)

            # Handler count should be consistent (old handlers removed)
            # Should have console handler at minimum
            assert count_after_first >= 1
            assert count_after_second == count_after_first
