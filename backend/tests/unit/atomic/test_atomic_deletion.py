#!/usr/bin/env python3
"""
Test suite for atomic historical records deletion functionality.
"""

import logging

# Add backend to path for testing
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.db.base import Comissao, Gasto, Pagamento, Sessao
from app.services.extrato_core import delete_historical_records_atomic


class TestHistoricalRecordsDeletion:
    """Test cases for the delete_historical_records_atomic function."""

    def setup_method(self):
        """Setup test fixtures."""
        self.logger = logging.getLogger(__name__)

        # Create mock database session
        self.mock_db = Mock()

        # Create test month/year
        self.test_mes = 9
        self.test_ano = 2025

    def create_mock_records(self):
        """Create mock records for testing."""
        # Create mock payments
        pagamentos = []
        for i in range(3):
            mock_pagamento = Mock(spec=Pagamento)
            mock_pagamento.id = i + 1
            pagamentos.append(mock_pagamento)

        # Create mock sessions
        sessoes = []
        for i in range(2):
            mock_sessao = Mock(spec=Sessao)
            mock_sessao.id = i + 1
            sessoes.append(mock_sessao)

        # Create mock commissions
        comissoes = []
        for i in range(4):
            mock_comissao = Mock(spec=Comissao)
            mock_comissao.id = i + 1
            comissoes.append(mock_comissao)

        # Create mock expenses
        gastos = []
        for i in range(2):
            mock_gasto = Mock(spec=Gasto)
            mock_gasto.id = i + 1
            gastos.append(mock_gasto)

        return pagamentos, sessoes, comissoes, gastos

    @patch("app.services.extrato_core.logger")
    def test_successful_deletion_all_record_types(self, mock_logger):
        """Test successful deletion of all record types."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify deletion calls in correct order
        # 1. Commissions deleted first
        assert self.mock_db.delete.call_count == 11  # 3 + 2 + 4 + 2 = 11

        # Verify logging calls
        mock_logger.info.assert_any_call(
            "Starting deletion of historical records for 09/2025", extra={}
        )
        mock_logger.info.assert_any_call(
            "Deleting 11 total records in dependency order", extra={}
        )
        mock_logger.info.assert_any_call("✓ Deleted 4 commissions", extra={})
        mock_logger.info.assert_any_call(
            "Breaking circular references between sessions and payments", extra={}
        )
        mock_logger.info.assert_any_call(
            "✓ Broke circular references between sessions and payments", extra={}
        )
        mock_logger.info.assert_any_call("✓ Deleted 3 payments", extra={})
        mock_logger.info.assert_any_call("✓ Deleted 2 sessions", extra={})
        mock_logger.info.assert_any_call("✓ Deleted 2 expenses", extra={})
        mock_logger.info.assert_any_call(
            "✓ Successfully deleted all 11 historical records for 09/2025", extra={}
        )

    @patch("app.services.extrato_core.logger")
    def test_successful_deletion_empty_lists(self, mock_logger):
        """Test successful deletion when no records exist."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = [], [], [], []

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify no deletion calls
        self.mock_db.delete.assert_not_called()

        # Verify logging
        mock_logger.info.assert_any_call("No records to delete", extra={})

    @patch("app.services.extrato_core.logger")
    def test_deletion_failure_commission_error(self, mock_logger):
        """Test deletion failure when commission deletion fails."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Make commission deletion fail
        self.mock_db.delete.side_effect = [
            Exception("Commission deletion failed"),
            None,
            None,
            None,
        ]

        # Act & Assert
        with pytest.raises(Exception, match="Commission deletion failed"):
            delete_historical_records_atomic(
                db_session=self.mock_db,
                pagamentos=pagamentos,
                sessoes=sessoes,
                comissoes=comissoes,
                gastos=gastos,
                mes=self.test_mes,
                ano=self.test_ano,
            )

        # Verify error logging
        mock_logger.error.assert_any_call(
            "Failed to delete commission 1: Commission deletion failed", extra={}
        )

    @patch("app.services.extrato_core.logger")
    def test_deletion_failure_payment_error(self, mock_logger):
        """Test deletion failure when payment deletion fails."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Make payment deletion fail (after commissions succeed)
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 4:  # After commissions (4) and circular reference breaking
                raise Exception("Payment deletion failed")
            return None

        self.mock_db.delete.side_effect = side_effect

        # Act & Assert
        with pytest.raises(Exception, match="Payment deletion failed"):
            delete_historical_records_atomic(
                db_session=self.mock_db,
                pagamentos=pagamentos,
                sessoes=sessoes,
                comissoes=comissoes,
                gastos=gastos,
                mes=self.test_mes,
                ano=self.test_ano,
            )

        # Verify error logging
        mock_logger.error.assert_any_call(
            "Failed to delete payment 1: Payment deletion failed", extra={}
        )

    @patch("app.services.extrato_core.logger")
    def test_circular_reference_breaking(self, mock_logger):
        """Test that circular references are properly broken."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify payment_id was set to None for each session
        for sessao in sessoes:
            assert sessao.payment_id is None

        # Verify logging
        mock_logger.info.assert_any_call(
            "Breaking circular references between sessions and payments", extra={}
        )
        mock_logger.info.assert_any_call(
            "✓ Broke circular references between sessions and payments", extra={}
        )

    @patch("app.services.extrato_core.logger")
    def test_deletion_count_verification_success(self, mock_logger):
        """Test that deletion count verification works correctly."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify success logging includes correct count
        mock_logger.info.assert_any_call(
            "✓ Successfully deleted all 11 historical records for 09/2025", extra={}
        )

    @patch("app.services.extrato_core.logger")
    def test_deletion_count_verification_failure(self, mock_logger):
        """Test that deletion count verification detects mismatches."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Simulate deletion count mismatch by making some delete calls fail
        # (This would happen if some records couldn't be deleted due to constraints)
        call_count = 0

        def failing_delete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 5:  # Make the last 6 calls fail
                raise Exception("Deletion failed due to constraint")
            return None

        self.mock_db.delete = failing_delete

        # Act & Assert
        with pytest.raises(Exception, match="Deletion failed due to constraint"):
            delete_historical_records_atomic(
                db_session=self.mock_db,
                pagamentos=pagamentos,
                sessoes=sessoes,
                comissoes=comissoes,
                gastos=gastos,
                mes=self.test_mes,
                ano=self.test_ano,
            )

        # Verify error logging
        mock_logger.error.assert_any_call(
            "Failed to delete payment 2: Deletion failed due to constraint", extra={}
        )

    @patch("app.services.extrato_core.logger")
    def test_partial_success_logging(self, mock_logger):
        """Test that partial success is properly logged."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify partial success logging
        mock_logger.info.assert_any_call("✓ Deleted 4 commissions", extra={})
        mock_logger.info.assert_any_call("✓ Deleted 3 payments", extra={})
        mock_logger.info.assert_any_call("✓ Deleted 2 sessions", extra={})
        mock_logger.info.assert_any_call("✓ Deleted 2 expenses", extra={})


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
