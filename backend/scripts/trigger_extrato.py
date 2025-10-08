#!/usr/bin/env python3
"""
Simplified manual trigger script for extrato generation.
Use this for testing or manual execution of the monthly extrato functionality.
"""

import argparse
import os
import sys
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.extrato_generation import check_and_generate_extrato, generate_extrato
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Manually trigger extrato generation")
    parser.add_argument("--mes", type=int, help="Month (1-12)")
    parser.add_argument("--ano", type=int, help="Year (YYYY)")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing extrato"
    )

    args = parser.parse_args()

    logger.info(
        "Manual Extrato Trigger",
        extra={
            "context": {
                "timestamp": datetime.now().isoformat(),
                "mes": args.mes,
                "ano": args.ano,
                "force": args.force,
            }
        },
    )

    try:
        if args.mes and args.ano:
            logger.info(
                "Generating extrato",
                extra={"context": {"mes": args.mes, "ano": args.ano}},
            )
            generate_extrato(args.mes, args.ano, force=args.force)
        else:
            logger.info("Generating extrato for previous month")
            check_and_generate_extrato(force=args.force)

        logger.info("Extrato generation completed successfully")

    except Exception as e:
        logger.error(
            "Extrato generation error",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
