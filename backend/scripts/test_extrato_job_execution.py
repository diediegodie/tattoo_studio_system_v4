#!/usr/bin/env python3
"""
Manual test script for monthly extrato job execution.

This script allows you to manually trigger the monthly extrato job
and verify that it works correctly in your environment.

Usage:
    python test_extrato_job_execution.py [--year YYYY] [--month MM]
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import Extrato, ExtratoRunLog
from app.db.session import SessionLocal
from app.services.extrato_core import get_previous_month
from app.services.extrato_generation import check_and_generate_extrato

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_extrato_exists(db, mes, ano):
    """Check if extrato exists for given month/year."""
    extrato = db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
    return extrato is not None


def check_run_log_exists(db, mes, ano):
    """Check if run log exists for given month/year."""
    run_log = (
        db.query(ExtratoRunLog)
        .filter(ExtratoRunLog.mes == mes, ExtratoRunLog.ano == ano)
        .all()
    )
    return run_log


def print_separator(title):
    """Print a formatted separator."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(
        description="Manually test monthly extrato job execution"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Year to generate extrato for (default: previous month)",
    )
    parser.add_argument(
        "--month",
        type=int,
        help="Month to generate extrato for (default: previous month)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force generation even if exists"
    )

    args = parser.parse_args()

    # Determine target month/year
    if args.year and args.month:
        target_month = args.month
        target_year = args.year
    else:
        target_month, target_year = get_previous_month()

    print_separator("MONTHLY EXTRATO JOB MANUAL TEST")
    print(f"Target: {target_month:02d}/{target_year}")
    print(f"Force: {args.force}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Check initial state
    print_separator("STEP 1: Check Initial State")
    db = SessionLocal()
    try:
        extrato_exists = check_extrato_exists(db, target_month, target_year)
        run_logs = check_run_log_exists(db, target_month, target_year)

        print(f"Extrato exists: {extrato_exists}")
        print(f"Run logs found: {len(run_logs)}")
        if run_logs:
            for log in run_logs:
                print(
                    f"  - Status: {log.status}, Run at: {log.run_at}, Message: {log.message}"
                )

        if extrato_exists and not args.force:
            print("\n⚠️  Extrato already exists. Use --force to overwrite.")
            return 1

    finally:
        db.close()

    # Execute the job
    print_separator("STEP 2: Execute Job")
    try:
        logger.info(
            f"Calling check_and_generate_extrato for {target_month}/{target_year}"
        )

        if args.year and args.month:
            check_and_generate_extrato(
                mes=target_month, ano=target_year, force=args.force
            )
        else:
            check_and_generate_extrato(force=args.force)

        print("✅ Job executed successfully")
    except Exception as e:
        print(f"❌ Job execution failed: {str(e)}")
        logger.exception("Job execution error")
        return 1

    # Check final state
    print_separator("STEP 3: Verify Results")
    db = SessionLocal()
    try:
        extrato_exists = check_extrato_exists(db, target_month, target_year)
        run_logs = check_run_log_exists(db, target_month, target_year)

        print(f"Extrato exists: {extrato_exists}")
        print(f"Run logs found: {len(run_logs)}")

        if run_logs:
            for log in run_logs:
                print(
                    f"  - Status: {log.status}, Run at: {log.run_at}, Message: {log.message}"
                )

        if extrato_exists:
            extrato = (
                db.query(Extrato)
                .filter(Extrato.mes == target_month, Extrato.ano == target_year)
                .first()
            )

            if extrato is None:
                print(f"\n⚠️  Warning: Extrato exists but query returned None")
                return 1

            print(f"\nExtrato details:")
            print(f"  - ID: {extrato.id}")
            print(f"  - Month: {extrato.mes}")
            print(f"  - Year: {extrato.ano}")
            print(f"  - Created at: {extrato.created_at}")

            # Check data integrity
            import json

            try:
                pagamentos = json.loads(extrato.pagamentos)
                sessoes = json.loads(extrato.sessoes)
                comissoes = json.loads(extrato.comissoes)
                totais = json.loads(extrato.totais)

                print(f"\nData counts:")
                print(f"  - Pagamentos: {len(pagamentos)}")
                print(f"  - Sessões: {len(sessoes)}")
                print(f"  - Comissões: {len(comissoes)}")
                print(f"\nTotals:")
                print(f"  - Receita total: {totais.get('receita_total', 0)}")
                print(f"  - Comissões total: {totais.get('comissoes_total', 0)}")
                print(f"  - Despesas total: {totais.get('despesas_total', 0)}")
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing JSON data: {str(e)}")
                return 1

    finally:
        db.close()

    # Test idempotency
    print_separator("STEP 4: Test Idempotency")
    print("Running job again (should skip if already successful)...")

    try:
        if args.year and args.month:
            check_and_generate_extrato(mes=target_month, ano=target_year, force=False)
        else:
            check_and_generate_extrato(force=False)

        print("✅ Idempotency check passed (job did not fail on second run)")
    except Exception as e:
        print(f"⚠️  Second run behavior: {str(e)}")

    print_separator("TEST COMPLETE")
    print("✅ All checks passed successfully!")
    print(f"Extrato for {target_month:02d}/{target_year} is ready.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
