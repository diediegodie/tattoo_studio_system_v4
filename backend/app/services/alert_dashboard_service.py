import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import current_app, has_app_context

_ALERT_LEVELS = {"WARNING", "ERROR", "CRITICAL"}


def _default_log_path() -> Path:
    if has_app_context() and current_app.config.get("ALERT_LOG_PATH"):
        return Path(current_app.config["ALERT_LOG_PATH"])
    base_logs = Path(__file__).resolve().parents[2] / "logs"
    return base_logs / "app.log"


def _sanitize_context(raw_context: Any) -> Dict[str, Any]:
    if not isinstance(raw_context, dict):
        return {}
    context_copy = dict(raw_context)
    request_context = context_copy.pop("context", {})
    if not isinstance(request_context, dict):
        request_context = {}
    context_copy["request"] = request_context
    return context_copy


def _parse_line(line: str) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None

    level = str(payload.get("level", "")).upper()
    context = _sanitize_context(payload.get("context"))

    alert_type = context.get("alert_type") or level.lower()
    severity = context.get("severity") or level.lower()

    if not context.get("alert_type") and level not in _ALERT_LEVELS:
        return None

    return {
        "timestamp": payload.get("timestamp"),
        "message": payload.get("message", ""),
        "alert_type": alert_type,
        "severity": severity.lower(),
        "details": context,
    }


def get_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    log_path = _default_log_path()
    if not log_path.exists():
        return []

    buffer_size = max(limit * 4, 200)
    lines: deque[str] = deque(maxlen=buffer_size)
    try:
        with log_path.open("r", encoding="utf-8") as logfile:
            for line in logfile:
                lines.append(line)
    except OSError:
        return []

    alerts: List[Dict[str, Any]] = []
    for line in reversed(lines):
        entry = _parse_line(line)
        if not entry:
            continue
        alerts.append(entry)
        if len(alerts) >= limit:
            break

    return alerts
