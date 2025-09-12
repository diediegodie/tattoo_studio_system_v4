#!/usr/bin/env python3
"""
Atomic Extrato Monitoring Script
Checks the status of atomic extrato operations and reports health metrics.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.extrato_service import check_and_generate_extrato_with_transaction
from app.services.extrato_service import (
    check_and_generate_extrato_with_transaction,
    verify_backup_before_transfer,
)

# Configuration
LOG_DIR = Path(__file__).parent.parent / "logs"
STATUS_FILE = LOG_DIR / "atomic_monitor_status.json"


class AtomicMonitor:
    def __init__(self):
        self.logger = self._setup_logger()
        self.status = self._load_status()

    def _setup_logger(self):
        """Setup logging for monitoring operations."""
        logger = logging.getLogger("atomic_monitor")
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        LOG_DIR.mkdir(exist_ok=True)

        # File handler
        fh = logging.FileHandler(LOG_DIR / "atomic_monitor.log")
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _load_status(self):
        """Load previous monitoring status."""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load status file: {e}")
        return {}

    def _save_status(self):
        """Save current monitoring status."""
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(self.status, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save status file: {e}")

    def check_backup_status(self, year, month):
        """Check if backup exists and is valid for given month."""
        try:
            backup_ok = verify_backup_before_transfer(year, month)
            status = "OK" if backup_ok else "MISSING"
            self.logger.info(f"Backup status for {month:02d}/{year}: {status}")
            return backup_ok
        except Exception as e:
            self.logger.error(f"Backup check failed for {month:02d}/{year}: {e}")
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
                self.logger.error(f"Failed to read log file: {e}")

        return operations

    def run_health_check(self):
        """Run comprehensive health check."""
        self.logger.info("Starting atomic extrato health check")

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

        self.logger.info(
            f"Health check completed. Overall status: {health_status['overall_health']}"
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
        print(report)
    else:
        # Run health check
        health = monitor.run_health_check()
        print(f"Health check completed. Status: {health['overall_health']}")


if __name__ == "__main__":
    main()
