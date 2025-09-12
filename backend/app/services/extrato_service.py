"""
Service for managing extrato generation and retrieval.
Reuses logic from generate_monthly_extrato.py for modularity.
"""

import json
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.base import (
    Pagamento,
    Sessao,
    Comissao,
    Extrato,
    Client,
    User,
    ExtratoRunLog,
    Gasto,
)


def get_previous_month():
    """Get the previous month and year."""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    return last_day_prev_month.month, last_day_prev_month.year


def check_existing_extrato(db, mes, ano, force=False):
    """Check if extrato already exists for the month/year."""
    existing = db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
    if existing:
        if not force:
            print(
                f"ERROR: Extrato for {mes}/{ano} already exists. Use --force to overwrite."
            )
            return False
        else:
            print(f"WARNING: Overwriting existing extrato for {mes}/{ano}.")
            db.delete(existing)
            db.commit()
    return True


def query_data(db, mes, ano):
    """Query Pagamento, Sessao, Comissao, Gasto for the month/year."""
    start_date = datetime(ano, mes, 1)
    if mes == 12:
        end_date = datetime(ano + 1, 1, 1)
    else:
        end_date = datetime(ano, mes + 1, 1)

    # Query Pagamentos with joins
    pagamentos = (
        db.query(Pagamento)
        .options(
            joinedload(Pagamento.cliente),
            joinedload(Pagamento.artista),
            joinedload(Pagamento.sessao),
        )
        .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
        .all()
    )

    # Query Sessoes
    sessoes = (
        db.query(Sessao)
        .options(joinedload(Sessao.cliente), joinedload(Sessao.artista))
        .filter(Sessao.data >= start_date, Sessao.data < end_date)
        .all()
    )

    # Query Comissoes with joins
    comissoes = (
        db.query(Comissao)
        .options(
            joinedload(Comissao.artista),
            joinedload(Comissao.pagamento).joinedload(Pagamento.cliente),
            joinedload(Comissao.pagamento).joinedload(Pagamento.sessao),
        )
        .filter(Comissao.created_at >= start_date, Comissao.created_at < end_date)
        .all()
    )

    # Query Gastos
    gastos = (
        db.query(Gasto)
        .options(joinedload(Gasto.creator))
        .filter(Gasto.data >= start_date, Gasto.data < end_date)
        .all()
    )

    return pagamentos, sessoes, comissoes, gastos


def serialize_data(pagamentos, sessoes, comissoes, gastos):
    """Serialize data into JSON-compatible dicts."""
    pagamentos_data = []
    for p in pagamentos:
        pagamentos_data.append(
            {
                "data": p.data.isoformat() if p.data else None,
                "hora": p.hora.isoformat() if p.hora else None,
                "cliente_name": p.cliente.name if p.cliente else None,
                "artista_name": p.artista.name if p.artista else None,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "observacoes": p.observacoes,
                "sessao_data": (
                    p.sessao.data.isoformat() if p.sessao and p.sessao.data else None
                ),
            }
        )

    sessoes_data = []
    for s in sessoes:
        sessoes_data.append(
            {
                "data": s.data.isoformat() if s.data else None,
                "hora": s.hora.isoformat() if s.hora else None,
                "cliente_name": s.cliente.name if s.cliente else None,
                "artista_name": s.artista.name if s.artista else None,
                "valor": float(s.valor),
                "status": s.status,
                "observacoes": s.observacoes,
            }
        )

    comissoes_data = []
    for c in comissoes:
        cliente_name = (
            c.pagamento.sessao.cliente.name
            if c.pagamento and c.pagamento.sessao and c.pagamento.sessao.cliente
            else None
        )
        comissoes_data.append(
            {
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "artista_name": c.artista.name if c.artista else None,
                "cliente_name": cliente_name,
                "pagamento_valor": float(c.pagamento.valor) if c.pagamento else None,
                "percentual": float(c.percentual),
                "valor": float(c.valor),
                "observacoes": c.observacoes,
            }
        )

    gastos_data = []
    for g in gastos:
        categoria = getattr(g, "categoria", None)  # Optional, forward-compatible
        gastos_data.append(
            {
                "data": g.data.isoformat() if g.data else None,
                "valor": float(g.valor),
                "descricao": g.descricao,
                "forma_pagamento": g.forma_pagamento,
                "categoria": categoria,
                "created_by": g.created_by,
            }
        )

    return pagamentos_data, sessoes_data, comissoes_data, gastos_data


def calculate_totals(pagamentos_data, sessoes_data, comissoes_data, gastos_data=None):
    """Calculate totals including despesas if provided."""
    receita_total = sum(p["valor"] for p in pagamentos_data)
    comissoes_total = sum(c["valor"] for c in comissoes_data)
    gastos_data = gastos_data or []
    despesas_total = sum(g["valor"] for g in gastos_data)

    # Por artista
    artistas = {}
    for p in pagamentos_data:
        artista = p["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
            artistas[artista]["receita"] += p["valor"]

    for c in comissoes_data:
        artista = c["artista_name"]
        if artista and artista in artistas:
            artistas[artista]["comissao"] += c["valor"]

    por_artista = [
        {"artista": k, "receita": v["receita"], "comissao": v["comissao"]}
        for k, v in artistas.items()
    ]

    # Por forma de pagamento (receitas)
    formas = {}
    for p in pagamentos_data:
        forma = p["forma_pagamento"]
        if forma:
            formas[forma] = formas.get(forma, 0) + p["valor"]

    por_forma_pagamento = [{"forma": k, "total": v} for k, v in formas.items()]

    # Gastos por forma de pagamento
    gastos_por_forma = {}
    for g in gastos_data:
        forma = g.get("forma_pagamento")
        if forma:
            gastos_por_forma[forma] = gastos_por_forma.get(forma, 0) + g["valor"]
    gastos_por_forma_pagamento = [
        {"forma": k, "total": v} for k, v in gastos_por_forma.items()
    ]

    # Gastos por categoria (optional field)
    gastos_por_categoria_map = {}
    for g in gastos_data:
        categoria = g.get("categoria") or "Outros"
        gastos_por_categoria_map[categoria] = (
            gastos_por_categoria_map.get(categoria, 0) + g["valor"]
        )
    gastos_por_categoria = [
        {"categoria": k, "total": v} for k, v in gastos_por_categoria_map.items()
    ]

    saldo = receita_total - despesas_total  # commissions shown separately

    return {
        "receita_total": receita_total,
        "comissoes_total": comissoes_total,
        "despesas_total": despesas_total,
        "saldo": saldo,
        "por_artista": por_artista,
        "por_forma_pagamento": por_forma_pagamento,
        "gastos_por_forma_pagamento": gastos_por_forma_pagamento,
        "gastos_por_categoria": gastos_por_categoria,
    }


def generate_extrato(mes, ano, force=False):
    """Generate extrato for the given month/year if it doesn't exist."""
    import logging

    logger = logging.getLogger(__name__)

    db = SessionLocal()
    try:
        if not check_existing_extrato(db, mes, ano, force):
            return

        # Query data
        pagamentos, sessoes, comissoes, gastos = query_data(db, mes, ano)
        logger.info(
            f"Generating extrato for {mes}/{ano}: {len(pagamentos)} pagamentos, {len(sessoes)} sessoes, {len(comissoes)} comissoes, {len(gastos)} gastos."
        )

        # Serialize
        pagamentos_data, sessoes_data, comissoes_data, gastos_data = serialize_data(
            pagamentos, sessoes, comissoes, gastos
        )

        # Calculate totals
        totais = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Create extrato
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

        logger.info("Extrato created successfully.")

        # Delete original records in dependency order, breaking circular references
        for c in comissoes:
            db.delete(c)
        # Break circular reference between Sessao and Pagamento
        for s in sessoes:
            setattr(s, "payment_id", None)
        db.commit()
        for p in pagamentos:
            db.delete(p)
        for s in sessoes:
            db.delete(s)
        for g in gastos:
            db.delete(g)
        db.commit()

        logger.info(
            f"Deleted {len(pagamentos)} pagamentos, {len(sessoes)} sessoes, {len(comissoes)} comissoes, {len(gastos)} gastos."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"ERROR generating extrato: {str(e)}")
        raise
    finally:
        db.close()


def should_run_monthly_extrato():
    """Check if we should run the monthly extrato generation using database tracking.

    This should only run once per month, after the 1st of the month.
    Uses database table instead of file-based tracking for better reliability.
    """
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    # Only run if today is on or after the 1st of the month
    if today.day < 1:  # Should not happen, but safety check
        return False

    # Check database for existing successful run this month
    db = SessionLocal()
    try:
        existing_run = (
            db.query(ExtratoRunLog)
            .filter(
                ExtratoRunLog.mes == current_month,
                ExtratoRunLog.ano == current_year,
                ExtratoRunLog.status == "success",
            )
            .first()
        )

        if existing_run:
            return False  # Already ran successfully this month

        return True

    except Exception as e:
        # If there's any error reading the database, log it but allow the run
        print(f"Warning: Could not check extrato run history: {e}")
        return True
    finally:
        db.close()


def run_extrato_in_background():
    """Run extrato generation in background thread with error handling.

    This is a shared utility function to avoid code duplication between
    main.py and historico_controller.py.
    """
    import threading

    # Check if background processing is disabled (for testing)
    disable_background = (
        os.getenv("DISABLE_EXTRATO_BACKGROUND", "false").lower() == "true"
    )

    if disable_background:
        # Run synchronously for testing
        try:
            check_and_generate_extrato()
        except Exception as e:
            print(f"Error in extrato generation: {e}")
    else:
        # Run in background thread
        def run_extrato_generation():
            try:
                check_and_generate_extrato()
            except Exception as e:
                print(f"Error in background extrato generation: {e}")

        # Start background thread
        thread = threading.Thread(target=run_extrato_generation, daemon=True)
        thread.start()


def _log_extrato_run(mes, ano, status, message=None):
    """Log an extrato generation run to the database."""
    db = SessionLocal()
    try:
        run_log = ExtratoRunLog(mes=mes, ano=ano, status=status, message=message)
        db.add(run_log)
        db.commit()
    except Exception as e:
        print(f"Warning: Could not log extrato run: {e}")
    finally:
        db.close()


def check_and_generate_extrato(mes=None, ano=None, force=False):
    """Check and generate extrato for the given or previous month.

    Enhanced version with production-ready logic and database logging.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # If specific month/year provided, use those
        if mes is not None and ano is not None:
            logger.info(f"Generating extrato for specific month: {mes}/{ano}")
            generate_extrato(mes, ano, force=force)
            # Log successful run
            _log_extrato_run(mes, ano, "success", "Manual generation completed")
            return

        # Check if we should run the monthly automation
        if not force and not should_run_monthly_extrato():
            logger.info(
                "Monthly extrato generation skipped - already ran this month or too early in month"
            )
            return

        # Get previous month and generate
        mes, ano = get_previous_month()
        logger.info(f"Running monthly extrato generation for {mes}/{ano}")
        generate_extrato(mes, ano, force=force)

        # Log successful run
        _log_extrato_run(mes, ano, "success", "Monthly automation completed")

    except Exception as e:
        # Log failed run
        if mes is not None and ano is not None:
            _log_extrato_run(mes, ano, "error", str(e))
        logger.error(f"Error in check_and_generate_extrato: {str(e)}")
        raise


def get_current_month_totals(db):
    """Calculate totals for the current month from the database, including gastos."""
    from datetime import datetime
    from sqlalchemy import func

    today = datetime.now()
    start_date = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_date = datetime(today.year + 1, 1, 1)
    else:
        end_date = datetime(today.year, today.month + 1, 1)

    # Get pagamentos
    pagamentos = (
        db.query(Pagamento)
        .options(joinedload(Pagamento.artista))
        .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
        .all()
    )

    # Get comissoes
    comissoes = (
        db.query(Comissao)
        .options(joinedload(Comissao.artista))
        .filter(Comissao.created_at >= start_date, Comissao.created_at < end_date)
        .all()
    )

    # Get gastos
    gastos = (
        db.query(Gasto).filter(Gasto.data >= start_date, Gasto.data < end_date).all()
    )

    # Serialize for calculation
    pagamentos_data = [
        {
            "valor": float(p.valor),
            "artista_name": p.artista.name if p.artista else None,
            "forma_pagamento": p.forma_pagamento,
        }
        for p in pagamentos
    ]

    comissoes_data = [
        {
            "valor": float(c.valor),
            "artista_name": c.artista.name if c.artista else None,
        }
        for c in comissoes
    ]

    gastos_data = [
        {
            "valor": float(g.valor),
            "forma_pagamento": g.forma_pagamento,
            "categoria": getattr(g, "categoria", None),
        }
        for g in gastos
    ]

    # Use existing calculate_totals function
    return calculate_totals(pagamentos_data, [], comissoes_data, gastos_data)


def verify_backup_before_transfer(year: int, month: int) -> bool:
    """
    Verify that a backup exists and is valid before proceeding with data transfer.

    Args:
        year: Year of the backup to verify
        month: Month of the backup to verify

    Returns:
        True if backup exists and is valid, False otherwise
    """
    import logging
    from app.services.backup_service import BackupService

    logger = logging.getLogger(__name__)

    try:
        logger.info(
            f"Verifying backup exists for {month:02d}/{year} before data transfer"
        )

        backup_service = BackupService()
        backup_exists = backup_service.verify_backup_exists(year, month)

        if backup_exists:
            logger.info(f"✓ Backup verification successful for {month:02d}/{year}")
            return True
        else:
            logger.error(f"✗ Backup verification failed for {month:02d}/{year}")
            return False

    except Exception as e:
        logger.error(
            f"Error during backup verification for {month:02d}/{year}: {str(e)}"
        )
        return False


def delete_historical_records_atomic(
    db_session,
    pagamentos: list,
    sessoes: list,
    comissoes: list,
    gastos: list,
    mes: int,
    ano: int,
) -> bool:
    """
    Safely delete historical records from the database within an atomic transaction.

    This function handles the deletion of records from the historico tables in the correct
    dependency order to maintain referential integrity. All deletions occur within the
    provided database session/transaction.

    Args:
        db_session: Active SQLAlchemy session (within transaction)
        pagamentos: List of Pagamento objects to delete
        sessoes: List of Sessao objects to delete
        comissoes: List of Comissao objects to delete
        gastos: List of Gasto objects to delete
        mes: Month of the records being deleted
        ano: Year of the records being deleted

    Returns:
        True if all deletions successful, False if any deletion failed

    Note:
        This function assumes it's being called within an active transaction.
        The caller is responsible for commit/rollback.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Starting deletion of historical records for {mes:02d}/{ano}")

        total_records = len(pagamentos) + len(sessoes) + len(comissoes) + len(gastos)
        if total_records == 0:
            logger.info("No records to delete")
            return True

        logger.info(f"Deleting {total_records} total records in dependency order")

        # Step 1: Delete commissions first (they depend on payments)
        # Commissions have foreign key to pagamentos, so delete them first
        deleted_comissoes = 0
        for comissao in comissoes:
            try:
                db_session.delete(comissao)
                deleted_comissoes += 1
            except Exception as e:
                logger.error(f"Failed to delete commission {comissao.id}: {str(e)}")
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_comissoes} commissions")

        # Step 2: Break circular references between Sessao and Pagamento
        # This prevents foreign key constraint violations when deleting payments/sessions
        logger.info("Breaking circular references between sessions and payments")
        for sessao in sessoes:
            try:
                # Set payment_id to None to break the circular reference
                setattr(sessao, "payment_id", None)
                logger.debug(f"Set payment_id to None for session {sessao.id}")
            except Exception as e:
                logger.error(
                    f"Failed to break reference for session {sessao.id}: {str(e)}"
                )
                raise  # Re-raise to trigger transaction rollback

        logger.info("✓ Broke circular references between sessions and payments")

        # Step 3: Delete payments (now safe to delete since references are broken)
        deleted_pagamentos = 0
        for pagamento in pagamentos:
            try:
                db_session.delete(pagamento)
                deleted_pagamentos += 1
            except Exception as e:
                logger.error(f"Failed to delete payment {pagamento.id}: {str(e)}")
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_pagamentos} payments")

        # Step 4: Delete sessions (now safe to delete)
        deleted_sessoes = 0
        for sessao in sessoes:
            try:
                db_session.delete(sessao)
                deleted_sessoes += 1
            except Exception as e:
                logger.error(f"Failed to delete session {sessao.id}: {str(e)}")
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_sessoes} sessions")

        # Step 5: Delete expenses (independent table, no dependencies)
        deleted_gastos = 0
        for gasto in gastos:
            try:
                db_session.delete(gasto)
                deleted_gastos += 1
            except Exception as e:
                logger.error(f"Failed to delete expense {gasto.id}: {str(e)}")
                raise  # Re-raise to trigger transaction rollback

        logger.info(f"✓ Deleted {deleted_gastos} expenses")

        # Verify all records were deleted
        expected_deletions = (
            len(pagamentos) + len(sessoes) + len(comissoes) + len(gastos)
        )
        actual_deletions = (
            deleted_pagamentos + deleted_sessoes + deleted_comissoes + deleted_gastos
        )

        if actual_deletions != expected_deletions:
            error_msg = f"Deletion count mismatch: expected {expected_deletions}, got {actual_deletions}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"✓ Successfully deleted all {actual_deletions} historical records for {mes:02d}/{ano}"
        )
        return True

    except Exception as e:
        logger.error(f"Error during historical records deletion: {str(e)}")
        raise  # Re-raise to ensure transaction rollback


def get_batch_size() -> int:
    """
    Get the batch size from environment variable or return default.

    Returns:
        Batch size for processing records (default: 100)
    """
    batch_size_str = os.getenv("BATCH_SIZE", "100")
    try:
        batch_size = int(batch_size_str)
        if batch_size < 1:
            batch_size = 100  # Minimum batch size
        return batch_size
    except ValueError:
        return 100  # Default on invalid value


def process_records_in_batches(records, batch_size, process_func, *args, **kwargs):
    """
    Process records in batches with error handling.

    Args:
        records: List of records to process
        batch_size: Size of each batch
        process_func: Function to process each batch
        *args, **kwargs: Additional arguments for process_func

    Yields:
        Results from each batch processing

    Raises:
        Exception: If any batch processing fails
    """
    import logging

    logger = logging.getLogger(__name__)

    if not records:
        return

    total_records = len(records)
    logger.info(f"Processing {total_records} records in batches of {batch_size}")

    for i in range(0, total_records, batch_size):
        batch = records[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size

        logger.info(
            f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)"
        )

        try:
            result = process_func(batch, *args, **kwargs)
            logger.info(f"✓ Batch {batch_num}/{total_batches} completed successfully")
            yield result

        except Exception as e:
            logger.error(f"✗ Batch {batch_num}/{total_batches} failed: {str(e)}")
            raise  # Re-raise to trigger transaction rollback


def serialize_data_batch(
    pagamentos_batch, sessoes_batch, comissoes_batch, gastos_batch
):
    """
    Serialize a batch of data into JSON-compatible dicts.

    Args:
        pagamentos_batch: Batch of Pagamento objects
        sessoes_batch: Batch of Sessao objects
        comissoes_batch: Batch of Comissao objects
        gastos_batch: Batch of Gasto objects

    Returns:
        Tuple of (pagamentos_data, sessoes_data, comissoes_data, gastos_data)
    """
    # Serialize payments batch
    pagamentos_data = []
    for p in pagamentos_batch:
        pagamentos_data.append(
            {
                "data": p.data.isoformat() if p.data else None,
                "hora": p.hora.isoformat() if p.hora else None,
                "cliente_name": p.cliente.name if p.cliente else None,
                "artista_name": p.artista.name if p.artista else None,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "observacoes": p.observacoes,
                "sessao_data": (
                    p.sessao.data.isoformat() if p.sessao and p.sessao.data else None
                ),
            }
        )

    # Serialize sessions batch
    sessoes_data = []
    for s in sessoes_batch:
        sessoes_data.append(
            {
                "data": s.data.isoformat() if s.data else None,
                "hora": s.hora.isoformat() if s.hora else None,
                "cliente_name": s.cliente.name if s.cliente else None,
                "artista_name": s.artista.name if s.artista else None,
                "valor": float(s.valor),
                "status": s.status,
                "observacoes": s.observacoes,
            }
        )

    # Serialize commissions batch
    comissoes_data = []
    for c in comissoes_batch:
        cliente_name = (
            c.pagamento.sessao.cliente.name
            if c.pagamento and c.pagamento.sessao and c.pagamento.sessao.cliente
            else None
        )
        comissoes_data.append(
            {
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "artista_name": c.artista.name if c.artista else None,
                "cliente_name": cliente_name,
                "pagamento_valor": float(c.pagamento.valor) if c.pagamento else None,
                "percentual": float(c.percentual),
                "valor": float(c.valor),
                "observacoes": c.observacoes,
            }
        )

    # Serialize expenses batch
    gastos_data = []
    for g in gastos_batch:
        categoria = getattr(g, "categoria", None)  # Optional, forward-compatible
        gastos_data.append(
            {
                "data": g.data.isoformat() if g.data else None,
                "valor": float(g.valor),
                "descricao": g.descricao,
                "forma_pagamento": g.forma_pagamento,
                "categoria": categoria,
                "created_by": g.created_by,
            }
        )

    return pagamentos_data, sessoes_data, comissoes_data, gastos_data


def calculate_totals_batch(pagamentos_data, sessoes_data, comissoes_data, gastos_data):
    """
    Calculate totals for a batch of data.

    Args:
        pagamentos_data: Serialized payment data
        sessoes_data: Serialized session data
        comissoes_data: Serialized commission data
        gastos_data: Serialized expense data

    Returns:
        Calculated totals dictionary
    """
    receita_total = sum(p["valor"] for p in pagamentos_data)
    comissoes_total = sum(c["valor"] for c in comissoes_data)
    despesas_total = sum(g["valor"] for g in gastos_data)

    # Por artista
    artistas = {}
    for p in pagamentos_data:
        artista = p["artista_name"]
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
            artistas[artista]["receita"] += p["valor"]

    for c in comissoes_data:
        artista = c["artista_name"]
        if artista and artista in artistas:
            artistas[artista]["comissao"] += c["valor"]

    por_artista = [
        {"artista": k, "receita": v["receita"], "comissao": v["comissao"]}
        for k, v in artistas.items()
    ]

    # Por forma de pagamento (receitas)
    formas = {}
    for p in pagamentos_data:
        forma = p["forma_pagamento"]
        if forma:
            formas[forma] = formas.get(forma, 0) + p["valor"]

    por_forma_pagamento = [{"forma": k, "total": v} for k, v in formas.items()]

    # Gastos por forma de pagamento
    gastos_por_forma = {}
    for g in gastos_data:
        forma = g.get("forma_pagamento")
        if forma:
            gastos_por_forma[forma] = gastos_por_forma.get(forma, 0) + g["valor"]
    gastos_por_forma_pagamento = [
        {"forma": k, "total": v} for k, v in gastos_por_forma.items()
    ]

    # Gastos por categoria (optional field)
    gastos_por_categoria_map = {}
    for g in gastos_data:
        categoria = g.get("categoria") or "Outros"
        gastos_por_categoria_map[categoria] = (
            gastos_por_categoria_map.get(categoria, 0) + g["valor"]
        )
    gastos_por_categoria = [
        {"categoria": k, "total": v} for k, v in gastos_por_categoria_map.items()
    ]

    saldo = receita_total - despesas_total  # commissions shown separately

    return {
        "receita_total": receita_total,
        "comissoes_total": comissoes_total,
        "despesas_total": despesas_total,
        "saldo": saldo,
        "por_artista": por_artista,
        "por_forma_pagamento": por_forma_pagamento,
        "gastos_por_forma_pagamento": gastos_por_forma_pagamento,
        "gastos_por_categoria": gastos_por_categoria,
    }


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
    import logging
    from sqlalchemy.exc import SQLAlchemyError

    logger = logging.getLogger(__name__)

    # Step 1: Verify backup exists before proceeding
    logger.info(f"Starting atomic extrato generation for {mes:02d}/{ano}")
    backup_verified = verify_backup_before_transfer(ano, mes)

    if not backup_verified:
        logger.error(
            "Cannot proceed with extrato generation - backup verification failed"
        )
        return False

    # Step 2: Start atomic transaction
    db = SessionLocal()
    try:
        logger.info("Beginning atomic transaction for extrato generation")

        # Check if extrato already exists (within transaction)
        existing = (
            db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
        )
        if existing and not force:
            logger.error(
                f"Extrato for {mes}/{ano} already exists. Use force=True to overwrite."
            )
            db.rollback()
            return False
        elif existing and force:
            logger.warning(f"Overwriting existing extrato for {mes}/{ano}")
            db.delete(existing)

        # Step 3: Query all historical data (within transaction)
        logger.info("Querying historical data within transaction")
        pagamentos, sessoes, comissoes, gastos = query_data(db, mes, ano)

        if not any([pagamentos, sessoes, comissoes, gastos]):
            logger.info(f"No historical data found for {mes:02d}/{ano}")
            db.rollback()
            return True  # Not an error, just no data

        logger.info(
            f"Found {len(pagamentos)} payments, {len(sessoes)} sessions, "
            f"{len(comissoes)} commissions, {len(gastos)} expenses"
        )

        # Step 4: Process data in batches (within transaction)
        logger.info("Processing data in batches within transaction")
        batch_size = get_batch_size()
        logger.info(f"Using batch size: {batch_size}")

        # Initialize accumulators for batched data
        all_pagamentos_data = []
        all_sessoes_data = []
        all_comissoes_data = []
        all_gastos_data = []

        # Process records in batches
        total_batches = 0
        for batch_result in process_records_in_batches(
            zip(pagamentos, sessoes, comissoes, gastos),
            batch_size,
            lambda batch: (
                serialize_data_batch(*zip(*batch)) if batch else ([], [], [], [])
            ),
        ):
            batch_pagamentos, batch_sessoes, batch_comissoes, batch_gastos = (
                batch_result
            )
            all_pagamentos_data.extend(batch_pagamentos)
            all_sessoes_data.extend(batch_sessoes)
            all_comissoes_data.extend(batch_comissoes)
            all_gastos_data.extend(batch_gastos)
            total_batches += 1

        logger.info(
            f"✓ Processed {total_batches} batches, total records: "
            f"{len(all_pagamentos_data)} payments, {len(all_sessoes_data)} sessions, "
            f"{len(all_comissoes_data)} commissions, {len(all_gastos_data)} expenses"
        )

        # Step 5: Calculate totals from accumulated data (within transaction)
        logger.info("Calculating totals from batched data")
        totais = calculate_totals_batch(
            all_pagamentos_data, all_sessoes_data, all_comissoes_data, all_gastos_data
        )

        # Step 6: Create extrato record (within transaction)
        logger.info("Creating extrato record")
        extrato = Extrato(
            mes=mes,
            ano=ano,
            pagamentos=json.dumps(all_pagamentos_data),
            sessoes=json.dumps(all_sessoes_data),
            comissoes=json.dumps(all_comissoes_data),
            gastos=json.dumps(all_gastos_data),
            totais=json.dumps(totais),
        )
        db.add(extrato)

        # Step 7: Delete original records in dependency order (within transaction)
        # This maintains referential integrity
        logger.info("Deleting original records in dependency order")

        deletion_success = delete_historical_records_atomic(
            db_session=db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=mes,
            ano=ano,
        )

        if not deletion_success:
            logger.error("Historical records deletion failed")
            raise ValueError("Failed to delete historical records")

        # Step 8: Commit the transaction
        logger.info("Committing atomic transaction")
        db.commit()

        logger.info(
            f"✓ Atomic extrato generation completed successfully for {mes:02d}/{ano}"
        )
        return True

    except SQLAlchemyError as e:
        # Rollback on database errors
        logger.error(f"Database error during atomic extrato generation: {str(e)}")
        db.rollback()
        return False

    except Exception as e:
        # Rollback on any other errors
        logger.error(f"Unexpected error during atomic extrato generation: {str(e)}")
        db.rollback()
        return False

    finally:
        # Always close the session
        db.close()
        logger.info("Database session closed")


def check_and_generate_extrato_with_transaction(mes=None, ano=None, force=False):
    """
    Check and generate extrato with atomic transaction support.

    Enhanced version with atomic transactions and backup verification.
    """
    import logging

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
