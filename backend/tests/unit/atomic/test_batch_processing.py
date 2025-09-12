#!/usr/bin/env python3
"""
Test suite for batch processing functionality in atomic extrato generation.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Add backend to path for testing
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.extrato_service import (
    get_batch_size,
    process_records_in_batches,
    serialize_data_batch,
    calculate_totals_batch,
    generate_extrato_with_atomic_transaction,
)
from app.db.base import Pagamento, Sessao, Comissao, Gasto


class TestBatchProcessing:
    """Test cases for batch processing functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.test_mes = 9
        self.test_ano = 2025

    def create_mock_records(self, count=5):
        """Create mock records for testing."""
        # Create mock payments
        pagamentos = []
        for i in range(count):
            mock_pagamento = Mock(spec=Pagamento)
            mock_pagamento.id = i + 1
            mock_pagamento.data = datetime(2025, 9, i + 1)
            mock_pagamento.hora = datetime(2025, 9, i + 1, 10, 0)
            mock_pagamento.valor = 100.0 * (i + 1)
            mock_pagamento.forma_pagamento = "credit_card"
            mock_pagamento.observacoes = f"Test payment {i + 1}"
            mock_pagamento.cliente = Mock()
            mock_pagamento.cliente.name = f"Client {i + 1}"
            mock_pagamento.artista = Mock()
            mock_pagamento.artista.name = f"Artist {i + 1}"
            mock_pagamento.sessao = Mock()
            mock_pagamento.sessao.data = datetime(2025, 9, i + 1)
            pagamentos.append(mock_pagamento)

        # Create mock sessions
        sessoes = []
        for i in range(count):
            mock_sessao = Mock(spec=Sessao)
            mock_sessao.id = i + 1
            mock_sessao.data = datetime(2025, 9, i + 1)
            mock_sessao.hora = datetime(2025, 9, i + 1, 10, 0)
            mock_sessao.valor = 80.0 * (i + 1)
            mock_sessao.status = "completed"
            mock_sessao.observacoes = f"Test session {i + 1}"
            mock_sessao.cliente = Mock()
            mock_sessao.cliente.name = f"Client {i + 1}"
            mock_sessao.artista = Mock()
            mock_sessao.artista.name = f"Artist {i + 1}"
            sessoes.append(mock_sessao)

        # Create mock commissions
        comissoes = []
        for i in range(count):
            mock_comissao = Mock(spec=Comissao)
            mock_comissao.id = i + 1
            mock_comissao.created_at = datetime(2025, 9, i + 1)
            mock_comissao.percentual = 10.0
            mock_comissao.valor = 10.0 * (i + 1)
            mock_comissao.observacoes = f"Test commission {i + 1}"
            mock_comissao.artista = Mock()
            mock_comissao.artista.name = f"Artist {i + 1}"
            mock_comissao.pagamento = Mock()
            mock_comissao.pagamento.valor = 100.0 * (i + 1)
            mock_comissao.pagamento.sessao = Mock()
            mock_comissao.pagamento.sessao.cliente = Mock()
            mock_comissao.pagamento.sessao.cliente.name = f"Client {i + 1}"
            comissoes.append(mock_comissao)

        # Create mock expenses
        gastos = []
        for i in range(count):
            mock_gasto = Mock(spec=Gasto)
            mock_gasto.id = i + 1
            mock_gasto.data = datetime(2025, 9, i + 1)
            mock_gasto.valor = 50.0 * (i + 1)
            mock_gasto.descricao = f"Test expense {i + 1}"
            mock_gasto.forma_pagamento = "cash"
            mock_gasto.categoria = "Supplies"
            mock_gasto.created_by = f"User {i + 1}"
            gastos.append(mock_gasto)

        return pagamentos, sessoes, comissoes, gastos

    @patch.dict(os.environ, {"BATCH_SIZE": "50"})
    def test_get_batch_size_from_env(self):
        """Test getting batch size from environment variable."""
        batch_size = get_batch_size()
        assert batch_size == 50

    @patch.dict(os.environ, {}, clear=True)
    def test_get_batch_size_default(self):
        """Test getting default batch size when env var not set."""
        batch_size = get_batch_size()
        assert batch_size == 100

    @patch.dict(os.environ, {"BATCH_SIZE": "invalid"})
    def test_get_batch_size_invalid_env(self):
        """Test getting default batch size when env var is invalid."""
        batch_size = get_batch_size()
        assert batch_size == 100

    @patch.dict(os.environ, {"BATCH_SIZE": "0"})
    def test_get_batch_size_minimum(self):
        """Test minimum batch size enforcement."""
        batch_size = get_batch_size()
        assert batch_size == 100  # Should default to minimum

    def test_serialize_data_batch(self):
        """Test batch serialization of data."""
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records(3)

        result = serialize_data_batch(pagamentos, sessoes, comissoes, gastos)

        pagamentos_data, sessoes_data, comissoes_data, gastos_data = result

        # Verify structure
        assert len(pagamentos_data) == 3
        assert len(sessoes_data) == 3
        assert len(comissoes_data) == 3
        assert len(gastos_data) == 3

        # Verify payment data structure
        payment = pagamentos_data[0]
        assert "data" in payment
        assert "hora" in payment
        assert "cliente_name" in payment
        assert "artista_name" in payment
        assert "valor" in payment
        assert "forma_pagamento" in payment
        assert "observacoes" in payment

        # Verify session data structure
        session = sessoes_data[0]
        assert "data" in session
        assert "hora" in session
        assert "cliente_name" in session
        assert "artista_name" in session
        assert "valor" in session
        assert "status" in session
        assert "observacoes" in session

        # Verify commission data structure
        commission = comissoes_data[0]
        assert "created_at" in commission
        assert "artista_name" in commission
        assert "cliente_name" in commission
        assert "pagamento_valor" in commission
        assert "percentual" in commission
        assert "valor" in commission
        assert "observacoes" in commission

        # Verify expense data structure
        expense = gastos_data[0]
        assert "data" in expense
        assert "valor" in expense
        assert "descricao" in expense
        assert "forma_pagamento" in expense
        assert "categoria" in expense
        assert "created_by" in expense

    def test_calculate_totals_batch(self):
        """Test batch calculation of totals."""
        # Create sample serialized data
        pagamentos_data = [
            {
                "valor": 100.0,
                "artista_name": "Artist 1",
                "forma_pagamento": "credit_card",
            },
            {"valor": 200.0, "artista_name": "Artist 2", "forma_pagamento": "cash"},
        ]

        sessoes_data = [
            {"valor": 80.0, "artista_name": "Artist 1"},
            {"valor": 160.0, "artista_name": "Artist 2"},
        ]

        comissoes_data = [
            {"valor": 10.0, "artista_name": "Artist 1"},
            {"valor": 20.0, "artista_name": "Artist 2"},
        ]

        gastos_data = [
            {"valor": 50.0, "forma_pagamento": "cash", "categoria": "Supplies"},
            {"valor": 30.0, "forma_pagamento": "credit_card", "categoria": "Equipment"},
        ]

        totais = calculate_totals_batch(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Verify totals
        assert totais["receita_total"] == 300.0  # 100 + 200
        assert totais["comissoes_total"] == 30.0  # 10 + 20
        assert totais["despesas_total"] == 80.0  # 50 + 30
        assert totais["saldo"] == 220.0  # 300 - 80

        # Verify artist breakdown
        por_artista = totais["por_artista"]
        assert len(por_artista) == 2
        artist1 = next(a for a in por_artista if a["artista"] == "Artist 1")
        artist2 = next(a for a in por_artista if a["artista"] == "Artist 2")
        assert artist1["receita"] == 100.0
        assert artist1["comissao"] == 10.0
        assert artist2["receita"] == 200.0
        assert artist2["comissao"] == 20.0

        # Verify payment method breakdown
        por_forma = totais["por_forma_pagamento"]
        assert len(por_forma) == 2
        credit_card = next(f for f in por_forma if f["forma"] == "credit_card")
        cash = next(f for f in por_forma if f["forma"] == "cash")
        assert credit_card["total"] == 100.0
        assert cash["total"] == 200.0

    @patch("app.services.extrato_service.logger")
    def test_process_records_in_batches_success(self, mock_logger):
        """Test successful batch processing."""
        records = list(range(10))  # 10 records
        batch_size = 3

        def process_func(batch):
            return sum(batch)

        results = list(process_records_in_batches(records, batch_size, process_func))

        # Should have 4 batches: 3, 3, 3, 1
        assert len(results) == 4
        assert results == [3, 6, 9, 1]  # sums of [0,1,2], [3,4,5], [6,7,8], [9]

        # Verify logging
        mock_logger.info.assert_any_call("Processing 10 records in batches of 3")
        mock_logger.info.assert_any_call("Processing batch 1/4 (3 records)")
        mock_logger.info.assert_any_call("✓ Batch 1/4 completed successfully")

    @patch("app.services.extrato_service.logger")
    def test_process_records_in_batches_empty(self, mock_logger):
        """Test batch processing with empty records."""
        records = []
        batch_size = 3

        def process_func(batch):
            return []

        results = list(process_records_in_batches(records, batch_size, process_func))

        assert len(results) == 0
        mock_logger.info.assert_any_call("Processing 0 records in batches of 3")

    @patch("app.services.extrato_service.logger")
    def test_process_records_in_batches_failure(self, mock_logger):
        """Test batch processing failure handling."""
        records = list(range(6))
        batch_size = 3

        def process_func(batch):
            if len(batch) == 3 and batch[0] == 3:  # Fail on second batch
                raise ValueError("Batch processing failed")
            return sum(batch)

        with pytest.raises(ValueError, match="Batch processing failed"):
            list(process_records_in_batches(records, batch_size, process_func))

        # Verify error logging
        mock_logger.error.assert_any_call("✗ Batch 2/2 failed: Batch processing failed")

    @patch("app.services.extrato_service.logger")
    def test_process_records_in_batches_single_batch(self, mock_logger):
        """Test batch processing with single batch."""
        records = [1, 2]
        batch_size = 5  # Larger than record count

        def process_func(batch):
            return sum(batch)

        results = list(process_records_in_batches(records, batch_size, process_func))

        assert len(results) == 1
        assert results[0] == 3  # 1 + 2

        mock_logger.info.assert_any_call("Processing batch 1/1 (2 records)")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
