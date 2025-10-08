"""
Script to run atomic extrato generation with backup verification.

This script replaces the traditional extrato generation with atomic transaction support.
It ensures backup verification before proceeding with data transfer.

Usage:
- Run manually: python run_atomic_extrato.py [--year YYYY] [--month MM] [--force]
- If no args, uses previous month for monthly automation.
- Scheduled via CRON: 0 2 1 * * /path/to/run_atomic_extrato.sh

Requirements:
- Run inside the app container or with correct PYTHONPATH
- Database must be accessible
- Backup must exist for the target month/year
"""

import argparse
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(
    0, "/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend"
)

from app.services.extrato_atomic import check_and_generate_extrato_with_transaction
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Main function to run atomic extrato generation."""
    parser = argparse.ArgumentParser(
        description="Run atomic extrato generation with backup verification"
    )
    parser.add_argument("--year", type=int, help="Year to generate extrato for")
    parser.add_argument("--month", type=int, help="Month to generate extrato for")
    parser.add_argument(
        "--force", action="store_true", help="Force generation even if extrato exists"
    )

    args = parser.parse_args()

    try:
        logger.info(
            "Starting atomic extrato generation script",
            extra={
                "context": {
                    "args": {
                        "year": args.year,
                        "month": args.month,
                        "force": args.force,
                    }
                }
            },
        )

        if args.year and args.month:
            logger.info(
                "Running atomic extrato generation for specific month",
                extra={
                    "context": {
                        "month": args.month,
                        "year": args.year,
                        "force": args.force,
                    }
                },
            )
            success = check_and_generate_extrato_with_transaction(
                mes=args.month, ano=args.year, force=args.force
            )
        else:
            logger.info(
                "Running monthly atomic extrato generation",
                extra={"context": {"force": args.force}},
            )
            success = check_and_generate_extrato_with_transaction(force=args.force)

        if success:
            logger.info("Atomic extrato generation completed successfully")
            return 0
        else:
            logger.error("Atomic extrato generation failed")
            return 1

    except Exception as e:
        error_msg = f"Unexpected error in atomic extrato generation: {str(e)}"
        logger.error(
            "Atomic extrato generation crashed",
            extra={"context": {"error": error_msg}},
            exc_info=True,
        )
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
