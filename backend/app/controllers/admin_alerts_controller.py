import logging
from collections import Counter
from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required

from app.services.alert_dashboard_service import get_recent_alerts

_DEFAULT_SEVERITY_ORDER = ("critical", "error", "warning", "info")

logger = logging.getLogger(__name__)

admin_alerts_bp = Blueprint("admin_alerts", __name__, url_prefix="/admin")


def _ensure_admin() -> None:
    if (
        not current_user.is_authenticated
        or not hasattr(current_user, "role")
        or current_user.role != "admin"
    ):
        abort(403)


@admin_alerts_bp.route("/alerts", methods=["GET"])
@login_required
def alerts_dashboard():
    _ensure_admin()

    default_limit = current_app.config.get("ALERT_DASHBOARD_DEFAULT_LIMIT", 50)
    max_limit = current_app.config.get("ALERT_DASHBOARD_MAX_LIMIT", 200)

    requested_limit = request.args.get("limit", default=default_limit, type=int)
    if requested_limit is None:
        requested_limit = default_limit

    limit = max(1, min(requested_limit, max_limit))
    alerts = get_recent_alerts(limit=limit)

    severity_summary = _summarize_alerts(alerts)

    logger.info(
        "Admin viewed alerts dashboard",
        extra={
            "context": {
                "user_id": getattr(current_user, "id", None),
                "limit": limit,
                "alert_count": len(alerts),
            }
        },
    )

    return render_template(
        "admin_alerts.html",
        alerts=alerts,
        limit=limit,
        log_source=current_app.config.get("ALERT_LOG_PATH"),
        severity_summary=severity_summary,
    )


def _summarize_alerts(alerts):
    if not alerts:
        return {"total": 0, "entries": []}

    counts = Counter()
    for alert in alerts:
        severity = str(alert.get("severity", "")).lower().strip()
        if severity:
            counts[severity] += 1

    severity_order = current_app.config.get(
        "ALERT_SEVERITY_ORDER", _DEFAULT_SEVERITY_ORDER
    )

    summary_entries = []
    for severity in severity_order:
        count = counts.pop(severity, 0)
        if count:
            summary_entries.append(
                {
                    "severity": severity,
                    "label": severity.replace("_", " ").title(),
                    "count": count,
                }
            )

    for severity, count in counts.items():
        summary_entries.append(
            {
                "severity": severity,
                "label": severity.replace("_", " ").title(),
                "count": count,
            }
        )

    total = sum(item["count"] for item in summary_entries)
    return {"total": total, "entries": summary_entries}
