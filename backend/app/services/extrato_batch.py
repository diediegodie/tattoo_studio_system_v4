"""
Extrato Batch Processing Service - Batch processing utilities.

This module contains utilities for processing extrato data in batches
for better performance and memory management.
"""

import logging
import os
from typing import Any, List, Tuple

# Configure logging
logger = logging.getLogger(__name__)


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

    if not records:
        return

    total_records = len(records)
    logger.info(
        f"Processing {total_records} records in batches of {batch_size}", extra={}
    )

    for i in range(0, total_records, batch_size):
        batch = records[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size

        logger.info(
            f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)",
            extra={},
        )

        try:
            result = process_func(batch, *args, **kwargs)
            logger.info(
                f"✓ Batch {batch_num}/{total_batches} completed successfully", extra={}
            )
            yield result

        except Exception as e:
            logger.error(
                f"✗ Batch {batch_num}/{total_batches} failed: {str(e)}", extra={}
            )
            raise


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
        if artista:
            if artista not in artistas:
                artistas[artista] = {"receita": 0, "comissao": 0}
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
