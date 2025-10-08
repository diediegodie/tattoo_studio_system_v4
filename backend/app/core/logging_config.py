"""
Centralized logging configuration for Tattoo Studio System.

This module provides structured logging with:
- JSON formatting for production
- Console formatting for development
- SQLAlchemy query logging
- Request/response logging
- Log rotation
- Performance metrics

Usage:
    from app.core.logging_config import setup_logging, get_logger

    # In main.py
    setup_logging(app, log_level="INFO", enable_sql_echo=True)

    # In any module
    logger = get_logger(__name__)
    logger.info("Operation completed", extra={"context": {"user_id": 123}})
"""

import json
import logging
import logging.handlers
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from flask import Flask, g, request
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs as JSON with timestamp, level, message, and extra context.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add context from extra parameter
        if hasattr(record, "context"):
            log_data["context"] = getattr(record, "context", {})

        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter with colors for development.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:8}{self.RESET}"
        return super().format(record)


def setup_logging(
    app: Optional[Flask] = None,
    log_level: Union[int, str] = "INFO",
    enable_sql_echo: bool = False,
    log_to_file: bool = True,
    use_json_format: bool = False,
) -> None:
    """
    Configure comprehensive logging for the Flask application.

    Args:
        app: Flask application instance (required for request/response hooks)
        log_level: Logging level (can be int like logging.INFO or string "INFO")
        enable_sql_echo: Enable SQLAlchemy query logging
        log_to_file: Write logs to rotating file
        use_json_format: Use JSON format instead of console format
    """
    # Determine log level
    if isinstance(log_level, int):
        level = log_level
    else:
        level = getattr(logging, str(log_level).upper(), logging.INFO)

    # Create logs directory (with fallback if creation fails)
    log_dir = Path(__file__).parent.parent.parent / "logs"
    early_warnings = []
    try:
        log_dir.mkdir(exist_ok=True)
    except Exception as e:
        # Defer warning until console handler is configured to avoid print()
        early_warnings.append(
            f"Failed to create logs directory: {e}. Logging will only go to console."
        )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Close and remove existing handlers properly
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_json_format:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ConsoleFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Flush any early warnings now that a handler exists
    for msg in early_warnings:
        root_logger.warning(msg, extra={"context": {"component": "logging_setup"}})

    # File handler with rotation (with fallback on failure)
    if log_to_file:
        file_formatter = JSONFormatter()  # Always JSON for files

        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / "app.log",
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # Log to console if file handler fails (disk full, read-only, etc.)
            # Catch all exceptions to ensure app doesn't crash
            console_handler.handle(
                logging.LogRecord(
                    name="app.logging",
                    level=logging.WARNING,
                    pathname=__file__,
                    lineno=0,
                    msg=f"Failed to create file handler for app.log: {e}. Falling back to console-only logging.",
                    args=(),
                    exc_info=None,
                )
            )

        # Separate error log (with independent error handling)
        try:
            error_handler = logging.handlers.RotatingFileHandler(
                log_dir / "tattoo_studio_errors.log",
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            root_logger.addHandler(error_handler)
        except Exception as e:
            # Log to console if error handler fails
            # Catch all exceptions to ensure app doesn't crash
            console_handler.handle(
                logging.LogRecord(
                    name="app.logging",
                    level=logging.WARNING,
                    pathname=__file__,
                    lineno=0,
                    msg=f"Failed to create error file handler: {e}. Error logs will only go to console.",
                    args=(),
                    exc_info=None,
                )
            )

    # Configure SQLAlchemy logging
    if enable_sql_echo:
        sql_logger = logging.getLogger("sqlalchemy.engine")
        sql_logger.setLevel(logging.INFO)
        sql_logger.propagate = True

        # Add event listener for query timing
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            conn.info.setdefault("query_start_time", []).append(time.time())

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            total_time = time.time() - conn.info["query_start_time"].pop(-1)
            perf_logger = logging.getLogger("sqlalchemy.performance")
            perf_logger.info(
                f"Query executed in {total_time * 1000:.2f}ms",
                extra={
                    "context": {
                        "sql_query": statement[:500],  # Truncate long queries
                        "sql_duration_ms": round(total_time * 1000, 2),
                    }
                },
            )

    # Flask request/response logging (only if app is provided)
    if app is not None:
        app.config.setdefault("ALERT_LOG_PATH", str(log_dir / "app.log"))
        app.config.setdefault("ALERT_DASHBOARD_DEFAULT_LIMIT", 50)
        app.config.setdefault("ALERT_DASHBOARD_MAX_LIMIT", 200)

        @app.before_request
        def log_request():
            g.request_start_time = time.time()
            g.request_id = f"{time.time()}-{id(request)}"
            g.route = (
                request.url_rule.rule if request.url_rule is not None else request.path
            )
            g.user_id = None
            if current_user.is_authenticated:
                g.user_id = getattr(current_user, "id", None)

            req_logger = logging.getLogger("flask.request")
            req_logger.info(
                f"{request.method} {request.path}",
                extra={
                    "context": {
                        "request_id": g.request_id,
                        "method": request.method,
                        "path": request.path,
                        "route": g.route,
                        "user_id": g.user_id,
                        "remote_addr": request.remote_addr,
                        "user_agent": str(request.user_agent),
                    }
                },
            )

        @app.after_request
        def log_response(response):
            if hasattr(g, "request_start_time"):
                duration_ms = (time.time() - g.request_start_time) * 1000
                resp_logger = logging.getLogger("flask.response")
                resp_logger.info(
                    f"{request.method} {request.path} {response.status_code} in {duration_ms:.2f}ms",
                    extra={
                        "context": {
                            "request_id": g.get("request_id"),
                            "method": request.method,
                            "path": request.path,
                            "status_code": response.status_code,
                            "duration_ms": round(duration_ms, 2),
                        }
                    },
                )
            return response

    # Suppress noisy third-party loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("oauthlib").setLevel(logging.WARNING)

    # Application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    app_logger.info(
        f"Logging configured: level={level}, sql_echo={enable_sql_echo}, "
        f"log_to_file={log_to_file}, json_format={use_json_format}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"context": {"user_id": 123}})
    """
    return logging.getLogger(name)


def log_performance(func_name: str, duration_ms: float, **kwargs) -> None:
    """
    Log performance metrics for a function or operation.

    Args:
        func_name: Name of the function or operation
        duration_ms: Execution duration in milliseconds
        **kwargs: Additional context (user_id, record_count, etc.)
    """
    perf_logger = get_logger("app.performance")
    context = {"function": func_name, "duration_ms": round(duration_ms, 2)}
    context.update(kwargs)
    perf_logger.info(
        f"{func_name} completed in {duration_ms:.2f}ms",
        extra={"context": context},
    )


def log_sql_query(
    query: str, params: dict, duration_ms: float, row_count: int = 0
) -> None:
    """
    Log a SQL query execution with timing and row count.

    Args:
        query: SQL query string
        params: Query parameters
        duration_ms: Execution duration in milliseconds
        row_count: Number of rows returned/affected
    """
    sql_logger = get_logger("app.sql")
    sql_logger.info(
        f"SQL query executed in {duration_ms:.2f}ms",
        extra={
            "context": {
                "query": query[:500],  # Truncate long queries
                "params": params,
                "duration_ms": round(duration_ms, 2),
                "row_count": row_count,
            }
        },
    )
