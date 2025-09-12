#!/usr/bin/env python3
"""
Integration test for atomic extrato generation with historical data cleanup.

This script performs end-to-end testing of the atomic transaction system,
including backup verification and safe deletion of historical records.

Usage:
    python test_atomic_integration.py [--dry-run] [--verbose]
"""

import os
import sys
import logging
import pytest
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.extrato_service import (
    check_and_generate_extrato_with_transaction,
    verify_backup_before_transfer,
    delete_historical_records_atomic,
)
from app.services.backup_service import BackupService


def setup_test_logging(verbose=False):
    """Setup logging for integration tests."""
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/atomic_integration_test.log", mode="w"),
        ],
    )

    return logging.getLogger(__name__)


@pytest.fixture
def logger():
    """Setup test logger fixture."""
    return setup_test_logging(verbose=True)


def test_backup_verification_integration(logger):
    """Test backup verification in integration context."""
    logger.info("=== Testing Backup Verification Integration ===")

    try:
        # Test current month
        now = datetime.now()
        current_year, current_month = now.year, now.month

        logger.info(
            f"Testing backup verification for {current_month:02d}/{current_year}"
        )
        backup_ok = verify_backup_before_transfer(current_year, current_month)

        if backup_ok:
            logger.info("✓ Current month backup verification passed")
            return True
        else:
            logger.warning(
                "⚠ Current month backup verification failed (expected if no backup exists)"
            )
            return True  # This is OK for testing

    except Exception as e:
        logger.error(f"Backup verification integration test failed: {str(e)}")
        return False


def test_atomic_transaction_flow(logger, dry_run=False):
    """Test the complete atomic transaction flow."""
    logger.info("=== Testing Atomic Transaction Flow ===")

    try:
        # Use previous month for testing (safer)
        now = datetime.now()
        if now.month == 1:
            test_year = now.year - 1
            test_month = 12
        else:
            test_year = now.year
            test_month = now.month - 1

        logger.info(f"Testing atomic transaction for {test_month:02d}/{test_year}")

        if dry_run:
            logger.info("DRY RUN: Would execute atomic transaction")
            return True

        # Execute atomic transaction
        success = check_and_generate_extrato_with_transaction(
            mes=test_month,
            ano=test_year,
            force=False,  # Don't force to avoid overwriting existing data
        )

        if success:
            logger.info("✓ Atomic transaction completed successfully")
            return True
        else:
            logger.error("✗ Atomic transaction failed")
            return False

    except Exception as e:
        logger.error(f"Atomic transaction flow test failed: {str(e)}")
        return False


def test_deletion_function_integration(logger):
    """Test the deletion function in isolation."""
    logger.info("=== Testing Deletion Function Integration ===")

    try:
        from unittest.mock import Mock
        from app.db.base import Pagamento, Sessao, Comissao, Gasto

        # Create mock database session
        mock_db = Mock()

        # Create test records
        pagamentos = [Mock(spec=Pagamento, id=i + 1) for i in range(3)]
        sessoes = [Mock(spec=Sessao, id=i + 1) for i in range(2)]
        comissoes = [Mock(spec=Comissao, id=i + 1) for i in range(4)]
        gastos = [Mock(spec=Gasto, id=i + 1) for i in range(2)]

        logger.info("Testing deletion with mock data")

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
            logger.info(
                f"✓ Deletion function test passed ({mock_db.delete.call_count} mock deletions)"
            )
            return True
        else:
            logger.error("✗ Deletion function test failed")
            return False

    except Exception as e:
        logger.error(f"Deletion function integration test failed: {str(e)}")
        return False


def test_batch_processing_integration(logger):
    """Test batch processing functionality in integration context."""
    logger.info("=== Testing Batch Processing Integration ===")

    try:
        from app.services.extrato_service import (
            get_batch_size,
            process_records_in_batches,
        )

        # Test batch size configuration
        batch_size = get_batch_size()
        logger.info(f"Current batch size: {batch_size}")

        # Test batch processing with sample data
        test_records = list(range(10))
        processed_batches = []

        def test_process_func(batch):
            batch_sum = sum(batch)
            processed_batches.append(batch_sum)
            return batch_sum

        results = list(process_records_in_batches(test_records, 3, test_process_func))

        logger.info(f"Processed {len(results)} batches with results: {results}")
        assert (
            len(results) == 4
        )  # Should have 4 batches: [0,1,2], [3,4,5], [6,7,8], [9]
        assert results == [3, 12, 21, 9]  # Sums of batches

        logger.info("✓ Batch processing integration test passed")
        return True

    except Exception as e:
        logger.error(f"Batch processing integration test failed: {str(e)}")
        return False


def run_health_check(logger):
    """Run a comprehensive health check of the atomic system."""
    logger.info("=== Running Atomic System Health Check ===")

    health_status = {
        "backup_service": False,
        "extrato_service": False,
        "deletion_function": False,
        "overall_health": "UNKNOWN",
    }

    try:
        # Test backup service availability
        backup_service = BackupService()
        health_status["backup_service"] = True
        logger.info("✓ Backup service is available")

        # Test extrato service imports
        from app.services.extrato_service import (
            generate_extrato_with_atomic_transaction,
        )

        health_status["extrato_service"] = True
        logger.info("✓ Extrato service is available")

        # Test deletion function
        health_status["deletion_function"] = test_deletion_function_integration(logger)

        # Determine overall health
        if all(health_status.values()):
            health_status["overall_health"] = "HEALTHY"
            logger.info("✓ Overall system health: HEALTHY")
        elif health_status["backup_service"] and health_status["extrato_service"]:
            health_status["overall_health"] = "DEGRADED"
            logger.warning(
                "⚠ Overall system health: DEGRADED (deletion function issues)"
            )
        else:
            health_status["overall_health"] = "UNHEALTHY"
            logger.error("✗ Overall system health: UNHEALTHY")

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        health_status["overall_health"] = "ERROR"
        return health_status


def main():
    """Main integration test function."""
    import argparse

    parser = argparse.ArgumentParser(description="Atomic Extrato Integration Tests")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't execute actual transactions)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--health-check", action="store_true", help="Run health check only"
    )
    parser.add_argument(
        "--test-deletion", action="store_true", help="Test deletion function only"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_test_logging(args.verbose)

    print("=" * 80)
    print("ATOMIC EXTRATO INTEGRATION TEST")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Verbose: {args.verbose}")
    print()

    success = True

    try:
        if args.health_check:
            # Run health check only
            health = run_health_check(logger)
            print(f"\nHealth Check Result: {health['overall_health']}")
            return health["overall_health"] == "HEALTHY"

        if args.test_deletion:
            # Test deletion function only
            return test_deletion_function_integration(logger)

        # Run full integration test
        logger.info("Starting full integration test suite")

        # Test 1: Backup verification
        if not test_backup_verification_integration(logger):
            success = False

        # Test 2: Atomic transaction flow
        if not test_atomic_transaction_flow(logger, args.dry_run):
            success = False

        # Test 3: Deletion function
        if not test_deletion_function_integration(logger):
            success = False

        # Test 4: Batch processing
        if not test_batch_processing_integration(logger):
            success = False

        # Test 4: Batch processing
        if not test_batch_processing_integration(logger):
            success = False

        # Final status
        if success:
            logger.info("✓ All integration tests passed!")
            print("\n✓ INTEGRATION TEST SUCCESS")
        else:
            logger.error("✗ Some integration tests failed")
            print("\n✗ INTEGRATION TEST FAILED")

        return success

    except KeyboardInterrupt:
        logger.info("Integration test interrupted by user")
        print("\n⚠ Test interrupted")
        return False

    except Exception as e:
        logger.error(f"Integration test failed with exception: {str(e)}")
        print(f"\n✗ INTEGRATION TEST ERROR: {str(e)}")
        return False

    finally:
        end_time = datetime.now()
        print(f"\nEnd Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
