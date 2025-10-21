"""
Extrato Atomic Service - Atomic transaction functions.

This module contains functions for atomic extrato generation with
backup verification and transaction safety.
"""

import json
import logging
import uuid
from datetime import datetime

from app.db.base import Comissao, Extrato, Gasto, Pagamento, Sessao
from app.db.session import SessionLocal
from app.services.extrato_automation import _log_extrato_run
from app.services.extrato_core import (
    calculate_totals,
    check_existing_extrato,
    delete_historical_records_atomic,
    query_data,
    serialize_data,
    verify_backup_before_transfer,
)
from app.services.undo_service import UndoService
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

# Configure logging
logger = logging.getLogger(__name__)


def generate_extrato_with_atomic_transaction(
    mes: int, ano: int, force: bool = False
) -> bool:
    """
    Generate extrato with atomic transaction support.

    This function wraps the entire extrato generation process in a single atomic transaction
    to ensure data consistency. If any part of the process fails, the entire transaction
    is rolled back.

    Args:
        mes: Month to generate extrato for (1-12)
        ano: Year to generate extrato for
        force: Whether to force generation even if extrato already exists

    Returns:
        True if successful, False if failed
    """
    # Generate correlation ID for this run
    correlation_id = str(uuid.uuid4())[:8]
    logger = logging.getLogger(__name__)

    # Add correlation ID to logger context
    extra = {"correlation_id": correlation_id}

    start_time = datetime.now()
    logger.info(
        f"Starting atomic extrato generation for {mes:02d}/{ano} - Run ID: {correlation_id}",
        extra=extra,
    )

    # Step 1: Verify backup exists before proceeding
    backup_verified = verify_backup_before_transfer(ano, mes)

    if not backup_verified:
        logger.error(
            f"Cannot proceed with extrato generation - backup verification failed - Run ID: {correlation_id}",
            extra=extra,
        )
        return False

    # Step 2: Start atomic transaction
    db = SessionLocal()
    try:
        logger.info(
            f"Beginning atomic transaction for extrato generation - Run ID: {correlation_id}",
            extra=extra,
        )

        # Check if extrato already exists (within transaction)
        existing = (
            db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
        )
        if existing and not force:
            logger.error(
                f"Extrato for {mes}/{ano} already exists. Use force=True to overwrite - Run ID: {correlation_id}",
                extra=extra,
            )
            db.rollback()
            return False
        elif existing and force:
            logger.warning(
                f"Overwriting existing extrato for {mes}/{ano} - Run ID: {correlation_id}",
                extra=extra,
            )
            # Create snapshot before deleting existing extrato
            undo_service = UndoService()
            snapshot_id = undo_service.create_snapshot(mes, ano, correlation_id)
            if snapshot_id:
                logger.info(
                    f"Created snapshot {snapshot_id} for existing extrato before overwrite - Run ID: {correlation_id}",
                    extra=extra,
                )
            else:
                logger.warning(
                    f"Failed to create snapshot for existing extrato - Run ID: {correlation_id}",
                    extra=extra,
                )
            db.delete(existing)

        # Step 3: Query all historical data (within transaction)
        logger.info(
            f"Querying historical data within transaction - Run ID: {correlation_id}",
            extra=extra,
        )
        pagamentos, sessoes, comissoes, gastos = query_data(db, mes, ano)

        if not any([pagamentos, sessoes, comissoes, gastos]):
            logger.info(
                f"No historical data found for {mes:02d}/{ano} - Run ID: {correlation_id}",
                extra=extra,
            )
            db.rollback()
            return True  # Not an error, just no data

        logger.info(
            f"Found {len(pagamentos)} payments, {len(sessoes)} sessions, "
            f"{len(comissoes)} commissions, {len(gastos)} expenses - Run ID: {correlation_id}",
            extra=extra,
        )

        # Step 4: Process data (within transaction)
        logger.info(
            f"Processing data within transaction - Run ID: {correlation_id}",
            extra=extra,
        )

        # Serialize data
        pagamentos_data, sessoes_data, comissoes_data, gastos_data = serialize_data(
            pagamentos, sessoes, comissoes, gastos
        )

        logger.info(
            f"✓ Serialized {len(pagamentos_data)} payments, {len(sessoes_data)} sessions, "
            f"{len(comissoes_data)} commissions, {len(gastos_data)} expenses - Run ID: {correlation_id}",
            extra=extra,
        )

        # Step 5: Calculate totals from data (within transaction)
        logger.info(
            f"Calculating totals from data - Run ID: {correlation_id}", extra=extra
        )
        totais = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Step 6: Create extrato record (within transaction)
        logger.info(f"Creating extrato record - Run ID: {correlation_id}", extra=extra)
        extrato = Extrato(
            mes=mes,
            ano=ano,
            pagamentos=json.dumps(pagamentos_data),
            sessoes=json.dumps(sessoes_data),
            comissoes=json.dumps(comissoes_data),
            gastos=json.dumps(gastos_data),
            totais=json.dumps(totais),
        )
        db.add(extrato)

        # Step 7: Delete original records in dependency order (within transaction)
        # This maintains referential integrity
        logger.info(
            f"Deleting original records in dependency order - Run ID: {correlation_id}",
            extra=extra,
        )

        deletion_success = delete_historical_records_atomic(
            db_session=db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=mes,
            ano=ano,
            correlation_id=correlation_id,
        )

        if not deletion_success:
            logger.error(
                f"Historical records deletion failed - Run ID: {correlation_id}",
                extra=extra,
            )
            raise ValueError("Failed to delete historical records")

        # Step 8: Commit the transaction
        logger.info(
            f"Committing atomic transaction - Run ID: {correlation_id}", extra=extra
        )
        db.commit()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(
            f"✓ Atomic extrato generation completed successfully for {mes:02d}/{ano} "
            f"in {duration:.2f}s - Run ID: {correlation_id}",
            extra=extra,
        )
        return True

    except SQLAlchemyError as e:
        # Rollback on database errors
        logger.error(
            f"Database error during atomic extrato generation: {str(e)} - Run ID: {correlation_id}",
            extra=extra,
        )
        db.rollback()
        return False

    except Exception as e:
        # Rollback on any other errors
        logger.error(
            f"Unexpected error during atomic extrato generation: {str(e)} - Run ID: {correlation_id}",
            extra=extra,
        )
        db.rollback()
        return False

    finally:
        # Always close the session
        db.close()
        logger.info(f"Database session closed - Run ID: {correlation_id}", extra=extra)


def check_and_generate_extrato_with_transaction(mes=None, ano=None, force=False):
    """
    Check and generate extrato with atomic transaction support.

    Enhanced version with atomic transactions and backup verification.
    """
    import logging

    from app.services.extrato_automation import should_run_monthly_extrato
    from app.services.extrato_core import get_previous_month

    logger = logging.getLogger(__name__)

    try:
        # If specific month/year provided, use those
        if mes is not None and ano is not None:
            logger.info(
                f"Generating extrato with atomic transaction for specific month: {mes}/{ano}"
            )
            success = generate_extrato_with_atomic_transaction(mes, ano, force=force)
            if success:
                # Log successful run
                _log_extrato_run(mes, ano, "success", "Atomic generation completed")
            else:
                # Log failed run
                _log_extrato_run(mes, ano, "error", "Atomic generation failed")
            return success

        # Check if we should run the monthly automation
        if not force and not should_run_monthly_extrato():
            logger.info(
                "Monthly extrato generation skipped - already ran this month or too early in month"
            )
            return True

        # Get previous month and generate with atomic transaction
        mes, ano = get_previous_month()
        logger.info(
            f"Running monthly extrato generation with atomic transaction for {mes}/{ano}"
        )
        success = generate_extrato_with_atomic_transaction(mes, ano, force=force)

        if success:
            # Log successful run
            _log_extrato_run(mes, ano, "success", "Monthly atomic generation completed")
        else:
            # Log failed run
            _log_extrato_run(mes, ano, "error", "Monthly atomic generation failed")

        return success

    except Exception as e:
        logger.error(f"Error in check_and_generate_extrato_with_transaction: {str(e)}")
        if mes is not None and ano is not None:
            _log_extrato_run(mes, ano, "error", f"Exception: {str(e)}")
        return False
