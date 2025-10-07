import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, Optional, Set

from flask import g, has_request_context
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("sql.alerts")

_SLACK_FAILURES: Set[str] = set()
_SENSITIVE_KEYS = ("password", "token", "secret", "email")


def _get_threshold_ms() -> int:
    try:
        return int(os.getenv("ALERT_QUERY_MS_THRESHOLD", "100"))
    except (TypeError, ValueError):
        return 100


def _alerts_enabled() -> bool:
    return os.getenv("ALERT_SLOW_QUERY_ENABLED", "true").lower() == "true"


def _safe_truncate(value: Any, limit: int = 500) -> str:
    try:
        text = str(value)
    except Exception:
        return "<unserializable>"
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _mask_params(params: Any) -> Any:
    try:
        if isinstance(params, dict):
            masked: Dict[str, Any] = {}
            for key, value in params.items():
                lowered = key.lower()
                if any(marker in lowered for marker in _SENSITIVE_KEYS):
                    masked[key] = "***"
                else:
                    masked[key] = _mask_params(value)
            return masked
        if isinstance(params, (list, tuple)):
            return [_mask_params(item) for item in params]
        if isinstance(params, bytes):
            return "<binary>"
        return _safe_truncate(params, 200)
    except Exception:
        return "<unserializable>"


def _post_slack(webhook: str, payload: Dict[str, Any]) -> None:
    if not webhook:
        return
    try:
        request = urllib.request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2):
            return
    except Exception as exc:  # pragma: no cover - network is optional
        failure_key = f"slack:{type(exc).__name__}"
        if failure_key not in _SLACK_FAILURES:
            logger.error(
                "Alert sink failed",
                extra={"context": {"error": str(exc), "sink": "slack"}},
            )
            _SLACK_FAILURES.add(failure_key)


def _gather_request_context(db_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    if has_request_context():
        request_id = getattr(g, "request_id", None)
        if request_id:
            context["request_id"] = request_id
        route = getattr(g, "route", None)
        if route:
            context["route"] = route
        user_id = getattr(g, "user_id", None)
        if user_id is not None:
            context["user_id"] = user_id
    if db_info:
        for key in ("db_host", "db_name"):
            value = db_info.get(key)
            if value:
                context[key] = value
    return context


def _emit_alert(
    duration_ms: float, statement: str, parameters: Any, context_info: Dict[str, Any]
) -> None:
    payload = {
        "alert_type": "slow_query",
        "severity": "warning",
        "duration_ms": round(duration_ms, 2),
        "statement": _safe_truncate(statement or ""),
        "params": _mask_params(parameters),
        "context": context_info,
    }
    logger.warning("Slow query detected", extra={"context": payload})

    webhook = os.getenv("ALERT_SINK_SLACK_WEBHOOK", "").strip()
    _post_slack(
        webhook,
        {
            "text": f":warning: Slow query {payload['duration_ms']}ms",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Slow query alert* ({payload['duration_ms']}ms)",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{_safe_truncate(statement, 300)}```",
                    },
                },
            ],
        },
    )


def register_query_timing(
    engine: Engine, db_info: Optional[Dict[str, Any]] = None
) -> None:
    """Register slow query alert listeners for the provided engine."""

    if getattr(engine, "_slow_query_alerts_registered", False):
        return

    resolved_db_info = dict(db_info or {})
    if not resolved_db_info:
        try:
            url = engine.url
            resolved_db_info = {
                "db_host": getattr(url, "host", None),
                "db_name": getattr(url, "database", None),
            }
        except Exception:
            resolved_db_info = {}

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        context._slow_query_start_time = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        if not _alerts_enabled():
            return
        start = getattr(context, "_slow_query_start_time", None)
        if start is None:
            return
        duration_ms = (time.perf_counter() - start) * 1000.0
        if duration_ms < _get_threshold_ms():
            return
        context_info = _gather_request_context(resolved_db_info)
        raw_params = parameters
        compiled_params = getattr(context, "compiled_parameters", None)
        if compiled_params:
            raw_params = compiled_params if executemany else compiled_params[0]
        _emit_alert(duration_ms, statement, raw_params, context_info)

    setattr(engine, "_slow_query_alerts_registered", True)
