"""
Script to test atomic transaction functionality for extrato generation.

This script demonstrates the new atomic transaction features:
- Backup verification before transfer
- Atomic transaction wrapping the entire process
- Proper rollback on failures
- Comprehensive logging

Usage:
- Run manually: python test_atomic_extrato.py [--year YYYY] [--month MM] [--force]
- If no args, uses previous month.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(
    0, "/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend"
)

from app.services.extrato_atomic import check_and_generate_extrato_with_transaction
from app.services.extrato_core import (
    delete_historical_records_atomic,
    verify_backup_before_transfer,
)


def get_previous_month():
    """Get the previous month and year."""
    now = datetime.now()
    if now.month == 1:
        return 12, now.year - 1
    else:
        return now.month - 1, now.year


# Set up logging
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "test_atomic_extrato.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


def test_backup_verification():
    """Test backup verification functionality."""
    print("=" * 60)
    print("TESTING BACKUP VERIFICATION")
    print("=" * 60)

    # Test with current month (should fail if no backup exists)
    now = datetime.now()
    year, month = now.year, now.month

    print(f"Testing backup verification for {month:02d}/{year}...")
    backup_ok = verify_backup_before_transfer(year, month)

    if backup_ok:
        print("✓ Backup verification passed")
        return True
    else:
        print("✗ Backup verification failed (expected if no backup exists)")
        return False


def test_atomic_extrato_generation():
    """Test atomic extrato generation."""
    print("\n" + "=" * 60)
    print("TESTING ATOMIC EXTRATO GENERATION")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="Test atomic extrato generation")
    parser.add_argument("--year", type=int, help="Year to test")
    parser.add_argument("--month", type=int, help="Month to test")
    parser.add_argument("--force", action="store_true", help="Force generation")

    # Parse known args to avoid conflicts
    args, unknown = parser.parse_known_args()

    try:
        if args.year and args.month:
            print(
                f"Testing atomic extrato generation for {args.month:02d}/{args.year}..."
            )
            success = check_and_generate_extrato_with_transaction(
                mes=args.month, ano=args.year, force=args.force
            )
        else:
            # Test with previous month
            prev_month, prev_year = get_previous_month()
            print(
                f"Testing atomic extrato generation for previous month: {prev_month:02d}/{prev_year}..."
            )
            success = check_and_generate_extrato_with_transaction(
                mes=prev_month, ano=prev_year, force=args.force
            )

        if success:
            print("✓ Atomic extrato generation completed successfully")
            return True
        else:
            print("✗ Atomic extrato generation failed")
            return False

    except Exception as e:
        print(f"✗ Exception during atomic extrato generation: {str(e)}")
        return False


def demonstrate_transaction_rollback():
    """Demonstrate transaction rollback on failure."""
    print("\n" + "=" * 60)
    print("DEMONSTRATING TRANSACTION ROLLBACK")
    print("=" * 60)

    print("Note: To properly test rollback, you would need to simulate a failure")
    print(
        "during the transaction (e.g., database connection loss, constraint violation)"
    )
    print("The atomic transaction implementation ensures that if ANY step fails,")
    print("the entire transaction is rolled back and no data is modified.")

    print("\nKey rollback scenarios handled:")
    print("✓ Database connection errors")
    print("✓ Constraint violations")
    print("✓ Unexpected exceptions")
    print("✓ Backup verification failures")
    print("✓ JSON serialization errors")

    return True


def test_deletion_function():
    """Test the modular deletion function with mock data."""
    print("\n=== Testing Deletion Function ===")

    try:
        from unittest.mock import Mock

        from app.db.base import Comissao, Gasto, Pagamento, Sessao

        # Create mock database session
        mock_db = Mock()

        # Create mock records
        pagamentos = [Mock(spec=Pagamento, id=i + 1) for i in range(2)]
        sessoes = [Mock(spec=Sessao, id=i + 1) for i in range(2)]
        comissoes = [Mock(spec=Comissao, id=i + 1) for i in range(3)]
        gastos = [Mock(spec=Gasto, id=i + 1) for i in range(2)]

        # Test deletion
        success = delete_historical_records_atomic(
            db_session=mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=9,
            ano=2025,
        )

        if success:
            print("✓ Deletion function test passed")
            print(f"✓ Mock delete calls: {mock_db.delete.call_count}")
            return True
        else:
            print("✗ Deletion function test failed")
            return False

    except Exception as e:
        print(f"✗ Deletion function test error: {str(e)}")
        return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test atomic extrato functionality")
    parser.add_argument(
        "--year", type=int, help="Year to test (default: previous month)"
    )
    parser.add_argument(
        "--month", type=int, help="Month to test (default: previous month)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force generation even if exists"
    )
    parser.add_argument(
        "--test-deletion", action="store_true", help="Test deletion function only"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=== Atomic Extrato Test Script ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.test_deletion:
        # Test only the deletion function
        return test_deletion_function()

    # Test backup verification
    if not test_backup_verification():
        print("✗ Backup verification test failed")
        return False

    # Test atomic extrato generation
    if not test_atomic_extrato_generation():
        print("✗ Atomic generation test failed")
        return False

    # Test deletion function
    if not test_deletion_function():
        print("✗ Deletion function test failed")
        return False

    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
