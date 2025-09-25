"""
Tests for monthly extrato process - Etapa 3 implementation.

Covers:
- Transfer failure and rollback scenarios
- Duplicate data prevention
- Time zone divergence handling
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from app.db.base import Comissao, Extrato, ExtratoRunLog, Pagamento, Sessao
from app.db.session import SessionLocal
from app.services.extrato_atomic import \
    generate_extrato_with_atomic_transaction
from app.services.extrato_core import (check_existing_extrato,
                                       get_previous_month)
from sqlalchemy.exc import IntegrityError, OperationalError


class TestExtratoTransferFailureAndRollback:
    """Test failure scenarios and rollback behavior."""

    @patch(
        "app.services.extrato_atomic.verify_backup_before_transfer", return_value=True
    )
    def test_transfer_failure_with_partial_data_rollback(self, mock_backup, db_session):
        """Test that partial failures trigger complete rollback."""
        # Setup test data
        mes, ano = 8, 2024

        # Create some test records
        pagamento = Pagamento(
            data=datetime(2024, 8, 15),
            valor=100.0,
            forma_pagamento="dinheiro",
            cliente_id=1,
            artista_id=1,
            sessao_id=1,
        )
        db_session.add(pagamento)
        db_session.commit()

        # Mock a failure during the transfer process
        with patch("app.services.extrato_atomic.query_data") as mock_query:
            mock_query.side_effect = OperationalError(
                None, None, Exception("Connection lost")
            )

            # Function should handle error gracefully and return False
            result = generate_extrato_with_atomic_transaction(mes, ano)
            assert result is False

            # Verify no extrato was created
            extrato = (
                db_session.query(Extrato)
                .filter(Extrato.mes == mes, Extrato.ano == ano)
                .first()
            )
            assert extrato is None

    def test_transfer_with_integrity_constraint_failure(self, db_session):
        """Test handling of integrity constraint violations."""
        mes, ano = 9, 2024

        # Create duplicate data that would cause constraint violation
        existing_extrato = Extrato(
            mes=mes,
            ano=ano,
            pagamentos=json.dumps([]),
            sessoes=json.dumps([]),
            comissoes=json.dumps([]),
            gastos=json.dumps([]),
            totais=json.dumps(
                {
                    "receita_total": 500.0,
                    "comissoes_total": 50.0,
                    "gastos_total": 100.0,
                    "lucro_total": 350.0,
                }
            ),
        )
        db_session.add(existing_extrato)
        db_session.commit()

        # Attempt to generate extrato for same month/year
        with patch(
            "app.services.extrato_atomic.verify_backup_before_transfer",
            return_value=True,
        ):
            result = generate_extrato_with_atomic_transaction(mes, ano)
            assert result is False  # Should fail because extrato already exists

        # Verify only one extrato exists
        extratos = (
            db_session.query(Extrato)
            .filter(Extrato.mes == mes, Extrato.ano == ano)
            .all()
        )
        assert len(extratos) == 1


class TestDuplicateDataPrevention:
    """Test duplicate data prevention mechanisms."""

    @patch(
        "app.services.extrato_atomic.verify_backup_before_transfer", return_value=True
    )
    def test_idempotent_extrato_generation(self, mock_backup, db_session):
        """Test that running extrato generation multiple times is safe."""
        mes, ano = 10, 2024

        # Create test payment data
        pagamento = Pagamento(
            data=datetime(2024, 10, 15),
            valor=150.0,
            forma_pagamento="dinheiro",
            cliente_id=1,
            artista_id=1,
            sessao_id=1,
        )
        db_session.add(pagamento)
        db_session.commit()

        # First run
        result1 = generate_extrato_with_atomic_transaction(mes, ano)
        assert result1 is not None

        # Second run should be idempotent
        result2 = generate_extrato_with_atomic_transaction(mes, ano)
        assert result2 is not None

        # Verify only one extrato exists
        extratos = (
            db_session.query(Extrato)
            .filter(Extrato.mes == mes, Extrato.ano == ano)
            .all()
        )
        assert len(extratos) == 1

    @patch(
        "app.services.extrato_atomic.verify_backup_before_transfer", return_value=True
    )
    def test_duplicate_prevention_with_force_flag(self, mock_backup, db_session):
        """Test duplicate prevention can be overridden with force flag."""
        mes, ano = 11, 2024

        # Create test payment data
        pagamento = Pagamento(
            data=datetime(2024, 11, 15),
            valor=250.0,
            forma_pagamento="cartao",
            cliente_id=1,
            artista_id=1,
            sessao_id=1,
        )
        db_session.add(pagamento)
        db_session.commit()

        # First run
        result1 = generate_extrato_with_atomic_transaction(mes, ano)
        assert result1 is not None

        # Second run with force should succeed and replace
        result2 = generate_extrato_with_atomic_transaction(mes, ano, force=True)
        assert result2 is not None

        # Verify still only one extrato exists
        extratos = (
            db_session.query(Extrato)
            .filter(Extrato.mes == mes, Extrato.ano == ano)
            .all()
        )
        assert len(extratos) == 1


class TestTimeZoneDivergenceHandling:
    """Test time zone handling and normalization."""

    @patch(
        "app.services.extrato_atomic.verify_backup_before_transfer", return_value=True
    )
    def test_naive_datetime_normalization(self, mock_backup, db_session):
        """Test that naive datetimes are properly handled."""
        mes, ano = 12, 2024

        # Create payment with naive datetime
        naive_datetime = datetime(2024, 12, 15, 14, 30, 0)  # No timezone

        pagamento = Pagamento(
            data=naive_datetime,
            valor=200.0,
            forma_pagamento="cartao",
            cliente_id=1,
            artista_id=1,
            sessao_id=1,
        )
        db_session.add(pagamento)
        db_session.commit()

        # Generate extrato
        result = generate_extrato_with_atomic_transaction(mes, ano)

        # Verify extrato was created successfully
        extrato = (
            db_session.query(Extrato)
            .filter(Extrato.mes == mes, Extrato.ano == ano)
            .first()
        )
        assert extrato is not None
        totais = json.loads(extrato.totais)
        assert totais["receita_total"] == 200.0

    @patch(
        "app.services.extrato_atomic.verify_backup_before_transfer", return_value=True
    )
    def test_timezone_aware_datetime_handling(self, mock_backup, db_session):
        """Test handling of timezone-aware datetimes."""
        mes, ano = 1, 2025

        # Create payment with timezone-aware datetime
        aware_datetime = datetime(2025, 1, 10, 16, 45, 0, tzinfo=timezone.utc)

        pagamento = Pagamento(
            data=aware_datetime,
            valor=150.0,
            forma_pagamento="pix",
            cliente_id=1,
            artista_id=1,
            sessao_id=1,
        )
        db_session.add(pagamento)
        db_session.commit()

        # Generate extrato
        result = generate_extrato_with_atomic_transaction(mes, ano)

        # Verify extrato was created successfully
        extrato = (
            db_session.query(Extrato)
            .filter(Extrato.mes == mes, Extrato.ano == ano)
            .first()
        )
        assert extrato is not None
        totais = json.loads(extrato.totais)
        assert totais["receita_total"] == 150.0

    @patch(
        "app.services.extrato_atomic.verify_backup_before_transfer", return_value=True
    )
    def test_mixed_timezone_data_consistency(self, mock_backup, db_session):
        """Test handling of mixed timezone data in the same month."""
        mes, ano = 2, 2025

        # Create payments with different timezone info
        payments_data = [
            (datetime(2025, 2, 5, 10, 0, 0), 100.0),  # Naive
            (datetime(2025, 2, 15, 14, 0, 0, tzinfo=timezone.utc), 200.0),  # UTC
            (
                datetime(2025, 2, 25, 18, 0, 0, tzinfo=timezone(timedelta(hours=-3))),
                150.0,
            ),  # BRT
        ]

        for payment_date, valor in payments_data:
            pagamento = Pagamento(
                data=payment_date,
                valor=valor,
                forma_pagamento="dinheiro",
                cliente_id=1,
                artista_id=1,
                sessao_id=1,
            )
            db_session.add(pagamento)

        db_session.commit()

        # Generate extrato
        result = generate_extrato_with_atomic_transaction(mes, ano)

        # Verify extrato aggregates all payments correctly
        extrato = (
            db_session.query(Extrato)
            .filter(Extrato.mes == mes, Extrato.ano == ano)
            .first()
        )
        assert extrato is not None
        totais = json.loads(extrato.totais)
        assert totais["receita_total"] == 450.0  # Sum of all payments

    def test_previous_month_calculation_edge_cases(self):
        """Test edge cases in previous month calculation."""
        # Test January (should return December of previous year)
        with patch("app.services.extrato_core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 15)
            mes, ano = get_previous_month()
            assert mes == 12
            assert ano == 2024

        # Test normal month
        with patch("app.services.extrato_core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 6, 15)
            mes, ano = get_previous_month()
            assert mes == 5
            assert ano == 2025
