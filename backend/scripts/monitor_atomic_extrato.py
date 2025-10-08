#!/usr/bin/env python3
"""
Atomic Extrato Monitoring Script
Checks the status of atomic extrato operations and reports health metrics.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging_config import get_logger
from app.services.extrato_atomic import check_and_generate_extrato_with_transaction
from app.services.extrato_core import verify_backup_before_transfer

# Configuration
LOG_DIR = Path(__file__).parent.parent / "logs"
STATUS_FILE = LOG_DIR / "atomic_monitor_status.json"

logger = get_logger(__name__)


class AtomicMonitor:
    def __init__(self):
        LOG_DIR.mkdir(exist_ok=True)
        self.status = self._load_status()

    def _load_status(self):
        """Load previous monitoring status."""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(
                    "Failed to load status file",
                    extra={"context": {"error": str(e)}},
                    exc_info=True,
                )
        return {}

    def _save_status(self):
        """Save current monitoring status."""
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(self.status, f, indent=2, default=str)
        except Exception as e:
            logger.error(
                "Failed to save status file",
                extra={"context": {"error": str(e)}},
                exc_info=True,
            )

    def check_backup_status(self, year, month):
        """Check if backup exists and is valid for given month."""
        try:
            backup_ok = verify_backup_before_transfer(year, month)
            status = "OK" if backup_ok else "MISSING"
            logger.info(
                "Backup status",
                extra={"context": {"month": month, "year": year, "status": status}},
            )
            return backup_ok
        except Exception as e:
            logger.error(
                "Backup check failed",
                extra={"context": {"month": month, "year": year, "error": str(e)}},
                exc_info=True,
            )
            return False

    def check_recent_operations(self, days=7):
        """Check recent atomic extrato operations from logs."""
        operations = []
        cutoff_date = datetime.now() - timedelta(days=days)

        # Check atomic extrato log
        log_file = LOG_DIR / "atomic_extrato.log"
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if "Starting atomic extrato generation" in line:
                            # Extract timestamp and details
                            parts = line.split(" - ")
                            if len(parts) >= 3:
                                timestamp_str = parts[0]
                                try:
                                    timestamp = datetime.strptime(
                                        timestamp_str, "%Y-%m-%d %H:%M:%S,%f"
                                    )
                                    if timestamp > cutoff_date:
                                        operations.append(
                                            {
                                                "timestamp": timestamp,
                                                "type": "generation_start",
                                                "details": line.strip(),
                                            }
                                        )
                                except ValueError:
                                    continue
            except Exception as e:
                logger.error(
                    "Failed to read log file",
                    extra={"context": {"error": str(e)}},
                    exc_info=True,
                )

        return operations

    def run_health_check(self):
        """Run comprehensive health check."""
        logger.info("Starting atomic extrato health check")

        health_status = {
            "timestamp": datetime.now(),
            "backup_status": {},
            "recent_operations": [],
            "overall_health": "UNKNOWN",
        }

        # Check current month backup
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # Check current month
        health_status["backup_status"]["current"] = self.check_backup_status(
            current_year, current_month
        )

        # Check previous month (for monthly generation)
        if current_month == 1:
            prev_year = current_year - 1
            prev_month = 12
        else:
            prev_year = current_year
            prev_month = current_month - 1

        health_status["backup_status"]["previous"] = self.check_backup_status(
            prev_year, prev_month
        )

        # Check recent operations
        health_status["recent_operations"] = self.check_recent_operations()

        # Determine overall health
        backup_current = health_status["backup_status"]["current"]
        backup_previous = health_status["backup_status"]["previous"]
        recent_ops = len(health_status["recent_operations"])

        if backup_current and backup_previous:
            health_status["overall_health"] = "HEALTHY"
        elif backup_previous:  # At least previous month backup exists
            health_status["overall_health"] = "WARNING"
        else:
            health_status["overall_health"] = "CRITICAL"

        # Update status
        self.status["last_health_check"] = health_status
        self._save_status()

        logger.info(
            "Health check completed",
            extra={"context": {"overall": health_status["overall_health"]}},
        )

        return health_status

    def generate_report(self):
        """Generate a human-readable health report."""
        health = self.run_health_check()
        report = f"""
Atomic Extrato Health Report
Generated: {health['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

Overall Health: {health['overall_health']}

Backup Status:
- Current Month: {'✓' if health['backup_status']['current'] else '✗'}
- Previous Month: {'✓' if health['backup_status']['previous'] else '✗'}

Recent Operations: {len(health['recent_operations'])} in last 7 days

Recommendations:
"""

        if health["overall_health"] == "CRITICAL":
            report += "- CRITICAL: No backups found. Create backups immediately before running extrato generation.\n"
        elif health["overall_health"] == "WARNING":
            report += "- WARNING: Current month backup missing. Ensure backup is created before end of month.\n"
        else:
            report += "- System is healthy. Ready for atomic extrato generation.\n"

        if len(health["recent_operations"]) == 0:
            report += "- No recent operations found. Consider running monthly generation if due.\n"

        return report


def main():
    """Main monitoring function."""
    monitor = AtomicMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # Generate and print report
        report = monitor.generate_report()
        logger.info(
            "Atomic extrato health report", extra={"context": {"report": report}}
        )
    else:
        # Run health check
        health = monitor.run_health_check()
        logger.info(
            "Health check completed",
            extra={"context": {"overall": health["overall_health"]}},
        )


if __name__ == "__main__":
    main()
