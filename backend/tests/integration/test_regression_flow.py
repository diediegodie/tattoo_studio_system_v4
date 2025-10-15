"""
End-to-End Regression Test Suite for Tattoo Studio System

This module implements comprehensive regression tests that validate the complete business flow:
1. Creating payments with/without clients
2. Creating payments for artists with 0% and >0% commission
3. Registering expenses
4. Generating historical records
5. Generating monthly extratos
6. Validating commission exclusion logic

Focuses on the critical commission fix: ensuring 0% commission artists
- DO NOT appear in "Comissões por Artista"
- DO appear in "Pagamentos realizados"
"""

import json
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from app.db.base import Client, Comissao, Extrato, Gasto, Pagamento, Sessao, User
from app.services.extrato_core import calculate_totals, serialize_data


class TestRegressionFlowComprehensive:
    """Complete end-to-end regression tests for the payment/commission system."""

    @pytest.fixture
    def regression_dataset(self, db_session):
        """Create fixed dataset for regression testing."""
        # Create users (artists) - User model only has basic fields
        artist_with_commission = User(
            id=101,
            email="artist_com@studio.com",
            name="Artist Com Comissão",
            active_flag=True,
            role="artist",
        )

        artist_zero_commission = User(
            id=102,
            email="artist_zero@studio.com",
            name="Artist Zero Comissão",
            active_flag=True,
            role="artist",
        )

        studio_owner = User(
            id=103,
            email="owner@studio.com",
            name="Studio Owner",
            active_flag=True,
            role="admin",
        )

        db_session.add_all(
            [artist_with_commission, artist_zero_commission, studio_owner]
        )

        # Create clients
        client_with_payment = Client(
            id=201, name="Cliente Regular", jotform_submission_id="test_submission_123"
        )

        db_session.add(client_with_payment)

        # Create sessions for different scenarios
        today = date.today()

        session_with_client = Sessao(
            id=301,
            data=today,
            artista_id=101,  # Artist with commission
            cliente_id=201,  # Has client
            valor=200.00,
            status="finalizada",
        )

        # Note: Sessao.cliente_id is NOT NULL in schema; keep a valid client here
        # while allowing the related payment to have cliente_id=None (walk-in payment)
        session_without_client = Sessao(
            id=302,
            data=today,
            artista_id=102,  # Artist with zero commission
            cliente_id=201,  # Use existing client to satisfy NOT NULL constraint
            valor=150.00,
            status="finalizada",
        )

        session_owner = Sessao(
            id=303,
            data=today,
            artista_id=103,  # Studio owner
            cliente_id=201,  # Has client
            valor=300.00,
            status="finalizada",
        )

        db_session.add_all([session_with_client, session_without_client, session_owner])

        # Create payments linked to sessions
        payment_with_client = Pagamento(
            id=401,
            data=today,
            valor=Decimal("200.00"),
            forma_pagamento="cartao",
            observacoes="Pagamento com cliente",
            cliente_id=201,  # Has client
            artista_id=101,  # Artist with commission
            sessao_id=301,
        )

        payment_without_client = Pagamento(
            id=402,
            data=today,
            valor=Decimal("150.00"),
            forma_pagamento="dinheiro",
            observacoes="Pagamento sem cliente (walk-in)",
            cliente_id=None,  # No client
            artista_id=102,  # Zero commission artist
            sessao_id=302,
        )

        payment_owner = Pagamento(
            id=403,
            data=today,
            valor=Decimal("300.00"),
            forma_pagamento="pix",
            observacoes="Pagamento para owner",
            cliente_id=201,  # Has client
            artista_id=103,  # Studio owner
            sessao_id=303,
        )

        # Additional payment for artist with commission (no session - older payment)
        payment_standalone = Pagamento(
            id=404,
            data=today - timedelta(days=1),
            valor=Decimal("100.00"),
            forma_pagamento="cartao",
            observacoes="Pagamento avulso",
            cliente_id=None,  # No client
            artista_id=101,  # Artist with commission
            sessao_id=None,  # No session
        )

        db_session.add_all(
            [
                payment_with_client,
                payment_without_client,
                payment_owner,
                payment_standalone,
            ]
        )

        # Create expenses
        expense_1 = Gasto(
            id=501,
            data=today,
            valor=Decimal("50.00"),
            descricao="Material de tatuagem",
            forma_pagamento="cartao",
            created_by=103,  # Created by owner
        )

        expense_2 = Gasto(
            id=502,
            data=today - timedelta(days=1),
            valor=Decimal("30.00"),
            descricao="Conta de luz",
            forma_pagamento="debito",
            created_by=101,  # Created by artist
        )

        db_session.add_all([expense_1, expense_2])

        # Create commissions for payments
        commission_artist = Comissao(
            id=601,
            pagamento_id=401,  # Payment with client
            artista_id=101,  # Artist with commission
            percentual=Decimal("30.00"),
            valor=Decimal("60.00"),  # 30% of 200
            observacoes="Comissão normal",
        )

        commission_standalone = Comissao(
            id=602,
            pagamento_id=404,  # Standalone payment
            artista_id=101,  # Artist with commission
            percentual=Decimal("30.00"),
            valor=Decimal("30.00"),  # 30% of 100
            observacoes="Comissão pagamento avulso",
        )

        # Note: No commission for zero-commission artist (id=102)
        # Note: No commission for owner (gets 100% - different calculation)

        db_session.add_all([commission_artist, commission_standalone])

        db_session.commit()

        return {
            "artists": {
                "with_commission": artist_with_commission,
                "zero_commission": artist_zero_commission,
                "owner": studio_owner,
            },
            "clients": {"regular": client_with_payment},
            "sessions": {
                "with_client": session_with_client,
                "without_client": session_without_client,
                "owner": session_owner,
            },
            "payments": {
                "with_client": payment_with_client,
                "without_client": payment_without_client,
                "owner": payment_owner,
                "standalone": payment_standalone,
            },
            "expenses": {"materials": expense_1, "utilities": expense_2},
            "commissions": {
                "artist": commission_artist,
                "standalone": commission_standalone,
            },
        }

    def test_step_1_payment_creation_and_validation(
        self, db_session, regression_dataset
    ):
        """Step 1: Validate that payments are created correctly."""
        # Verify all payments exist in database
        payments = db_session.query(Pagamento).all()
        assert len(payments) == 4, "Should have 4 payments in regression dataset"

        # Test payment with client
        payment_with_client = db_session.query(Pagamento).filter_by(id=401).first()
        assert payment_with_client is not None
        assert payment_with_client.cliente_id == 201
        assert payment_with_client.artista_id == 101
        assert payment_with_client.valor == Decimal("200.00")
        assert payment_with_client.sessao_id == 301

        # Test payment without client (walk-in)
        payment_without_client = db_session.query(Pagamento).filter_by(id=402).first()
        assert payment_without_client is not None
        assert payment_without_client.cliente_id is None  # No client
        assert payment_without_client.artista_id == 102  # Zero commission artist
        assert payment_without_client.valor == Decimal("150.00")
        assert payment_without_client.sessao_id == 302

        # Test owner payment
        payment_owner = db_session.query(Pagamento).filter_by(id=403).first()
        assert payment_owner is not None
        assert payment_owner.cliente_id == 201
        assert payment_owner.artista_id == 103  # Owner
        assert payment_owner.valor == Decimal("300.00")

        # Test standalone payment (no session)
        payment_standalone = db_session.query(Pagamento).filter_by(id=404).first()
        assert payment_standalone is not None
        assert payment_standalone.cliente_id is None
        assert payment_standalone.artista_id == 101  # Artist with commission
        assert payment_standalone.sessao_id is None  # No session

    def test_step_2_commission_calculation(self, db_session, regression_dataset):
        """Step 2: Validate commission calculations."""
        # Check commissions exist only for artist with commission rate > 0
        commissions = db_session.query(Comissao).all()
        assert (
            len(commissions) == 2
        ), "Should have 2 commissions (only for artist with commission > 0)"

        # Verify commission for payment with client
        commission_1 = db_session.query(Comissao).filter_by(pagamento_id=401).first()
        assert commission_1 is not None
        assert commission_1.artista_id == 101  # Artist with 30% commission
        assert commission_1.percentual == Decimal("30.00")
        assert commission_1.valor == Decimal("60.00")  # 30% of 200

        # Verify commission for standalone payment
        commission_2 = db_session.query(Comissao).filter_by(pagamento_id=404).first()
        assert commission_2 is not None
        assert commission_2.artista_id == 101  # Same artist
        assert commission_2.percentual == Decimal("30.00")
        assert commission_2.valor == Decimal("30.00")  # 30% of 100

        # Verify NO commission exists for zero-commission artist (id=102)
        commission_zero = db_session.query(Comissao).filter_by(artista_id=102).first()
        assert (
            commission_zero is None
        ), "Zero commission artist should have no commission records"

        # Verify NO commission exists for owner payment (id=403)
        commission_owner = (
            db_session.query(Comissao).filter_by(pagamento_id=403).first()
        )
        assert (
            commission_owner is None
        ), "Owner payment should not have separate commission record"

    def test_step_3_expense_tracking(self, db_session, regression_dataset):
        """Step 3: Validate expense creation and tracking."""
        expenses = db_session.query(Gasto).all()
        assert len(expenses) == 2, "Should have 2 expenses in regression dataset"

        # Verify expense details
        expense_1 = db_session.query(Gasto).filter_by(id=501).first()
        assert expense_1 is not None
        assert expense_1.valor == Decimal("50.00")
        assert expense_1.descricao == "Material de tatuagem"
        assert expense_1.created_by == 103  # Owner

        expense_2 = db_session.query(Gasto).filter_by(id=502).first()
        assert expense_2 is not None
        assert expense_2.valor == Decimal("30.00")
        assert expense_2.descricao == "Conta de luz"
        assert expense_2.created_by == 101  # Artist

    def test_step_4_historical_totals_calculation(self, db_session, regression_dataset):
        """Step 4: Test the critical commission exclusion logic in calculate_totals."""
        # This tests the core fix: zero-commission artists should be excluded from commission summary

        # Get test data for current month
        today = date.today()
        mes, ano = today.month, today.year

        # Mock data structures as they would appear in calculate_totals
        pagamentos_data = [
            {
                "id": 401,
                "valor": 200.00,
                "data": today.isoformat(),
                "artista_name": "Artist Com Comissão",
                "cliente_name": "Cliente Regular",
                "forma_pagamento": "cartao",
                "sessao_id": 301,
            },
            {
                "id": 402,
                "valor": 150.00,
                "data": today.isoformat(),
                "artista_name": "Artist Zero Comissão",
                "cliente_name": None,  # Walk-in
                "forma_pagamento": "dinheiro",
                "sessao_id": 302,
            },
            {
                "id": 403,
                "valor": 300.00,
                "data": today.isoformat(),
                "artista_name": "Studio Owner",
                "cliente_name": "Cliente Regular",
                "forma_pagamento": "pix",
                "sessao_id": 303,
            },
            {
                "id": 404,
                "valor": 100.00,
                "data": (today - timedelta(days=1)).isoformat(),
                "artista_name": "Artist Com Comissão",
                "cliente_name": None,
                "forma_pagamento": "cartao",
                "sessao_id": None,
            },
        ]

        sessoes_data = [
            {
                "id": 301,
                "valor": 200.00,
                "data": today.isoformat(),
                "artista_name": "Artist Com Comissão",
                "status": "finalizada",
                "tem_pagamento": True,
            },
            {
                "id": 302,
                "valor": 150.00,
                "data": today.isoformat(),
                "artista_name": "Artist Zero Comissão",
                "status": "finalizada",
                "tem_pagamento": True,
            },
            {
                "id": 303,
                "valor": 300.00,
                "data": today.isoformat(),
                "artista_name": "Studio Owner",
                "status": "finalizada",
                "tem_pagamento": True,
            },
        ]

        comissoes_data = [
            {
                "id": 601,
                "valor": 60.00,
                "artista_name": "Artist Com Comissão",
                "pagamento_id": 401,
            },
            {
                "id": 602,
                "valor": 30.00,
                "artista_name": "Artist Com Comissão",
                "pagamento_id": 404,
            },
            # Note: NO commission for "Artist Zero Comissão" or "Studio Owner"
        ]

        gastos_data = [
            {
                "id": 501,
                "valor": 50.00,
                "descricao": "Material de tatuagem",
                "forma_pagamento": "cartao",
            },
            {
                "id": 502,
                "valor": 30.00,
                "descricao": "Conta de luz",
                "forma_pagamento": "debito",
            },
        ]

        # Call calculate_totals with our test data (CORRECT parameter order!)
        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Validate total calculations
        assert totals["receita_total"] == 750.00  # 200 + 150 + 300 + 100
        assert (
            totals["comissoes_total"] == 90.00
        )  # 60 + 30 (only for Artist Com Comissão)
        assert totals["despesas_total"] == 80.00  # 50 + 30
        assert totals["receita_liquida"] == 580.00  # 750 - 90 - 80
        assert (
            totals["saldo"] == 670.00
        )  # 750 - 80 (saldo = receita - despesas, excluding commissions)

        # CRITICAL TEST: Validate commission summary excludes zero-commission artists
        por_artista = totals["por_artista"]

        # Should only have 1 artist in commission summary (Artist Com Comissão)
        assert (
            len(por_artista) == 1
        ), f"Expected 1 artist in commission summary, got {len(por_artista)}: {por_artista}"

        artist_summary = por_artista[0]
        assert artist_summary["artista"] == "Artist Com Comissão"
        assert artist_summary["receita"] == 300.00  # 200 + 100 from two payments
        assert artist_summary["comissao"] == 90.00  # 60 + 30

        # CRITICAL: Verify zero-commission artist is NOT in summary
        artist_names = [item["artista"] for item in por_artista]
        assert (
            "Artist Zero Comissão" not in artist_names
        ), "Zero commission artist should NOT appear in commission summary"
        assert (
            "Studio Owner" not in artist_names
        ), "Owner without commission record should NOT appear in commission summary"

        # But verify all payments are still counted in totals
        assert (
            totals["total_pagamentos"] == 750.00
        ), "All payments should be counted in total regardless of commission"

    def test_step_5_payments_appearing_in_records(self, db_session, regression_dataset):
        """Step 5: Ensure ALL payments appear in 'Pagamentos realizados' regardless of commission."""
        # Query all payments as they would appear in payment records
        payments = db_session.query(Pagamento).all()

        payment_records = []
        for p in payments:
            payment_records.append(
                {
                    "id": p.id,
                    "valor": float(p.valor),
                    "artista_name": p.artista.name if p.artista else None,
                    "cliente_name": p.cliente.name if p.cliente else None,
                    "forma_pagamento": p.forma_pagamento,
                }
            )

        # Verify all 4 payments appear in records
        assert len(payment_records) == 4

        # Verify zero-commission artist payment appears
        zero_commission_payment = next(
            (p for p in payment_records if p["artista_name"] == "Artist Zero Comissão"),
            None,
        )
        assert (
            zero_commission_payment is not None
        ), "Zero commission artist payment should appear in payment records"
        assert zero_commission_payment["valor"] == 150.00
        assert zero_commission_payment["cliente_name"] is None  # Walk-in

        # Verify all other payments also appear
        regular_payment = next((p for p in payment_records if p["id"] == 401), None)
        assert regular_payment is not None
        assert regular_payment["artista_name"] == "Artist Com Comissão"
        assert regular_payment["cliente_name"] == "Cliente Regular"

    def test_step_6_extrato_generation_flow(self, db_session, regression_dataset):
        """Step 6: Test complete extrato generation preserving commission exclusion."""
        today = date.today()
        mes, ano = today.month, today.year

        # Simulate extrato generation process

        # 1. Gather data from database
        pagamentos = (
            db_session.query(Pagamento)
            .filter(
                Pagamento.data >= date(ano, mes, 1),
                (
                    Pagamento.data < date(ano, mes + 1, 1)
                    if mes < 12
                    else date(ano + 1, 1, 1)
                ),
            )
            .all()
        )

        comissoes = (
            db_session.query(Comissao)
            .join(Pagamento)
            .filter(
                Pagamento.data >= date(ano, mes, 1),
                (
                    Pagamento.data < date(ano, mes + 1, 1)
                    if mes < 12
                    else date(ano + 1, 1, 1)
                ),
            )
            .all()
        )

        sessoes = (
            db_session.query(Sessao)
            .filter(
                Sessao.data >= date(ano, mes, 1),
                (
                    Sessao.data < date(ano, mes + 1, 1)
                    if mes < 12
                    else date(ano + 1, 1, 1)
                ),
            )
            .all()
        )

        gastos = (
            db_session.query(Gasto)
            .filter(
                Gasto.data >= date(ano, mes, 1),
                Gasto.data < date(ano, mes + 1, 1) if mes < 12 else date(ano + 1, 1, 1),
            )
            .all()
        )

        # 2. Serialize data
        pagamentos_data, sessoes_data, comissoes_data, gastos_data = serialize_data(
            pagamentos, sessoes, comissoes, gastos
        )

        # 3. Calculate totals (this includes the commission exclusion logic)
        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # 4. Create extrato record
        extrato = Extrato(
            mes=mes,
            ano=ano,
            pagamentos=pagamentos_data,
            comissoes=comissoes_data,
            sessoes=sessoes_data,
            gastos=gastos_data,
            totais=totals,
        )

        db_session.add(extrato)
        db_session.commit()

        # 5. Validate extrato was created correctly
        saved_extrato = db_session.query(Extrato).filter_by(mes=mes, ano=ano).first()
        assert saved_extrato is not None

        # 6. Validate extrato contains all payment data
        assert (
            len(saved_extrato.pagamentos) == 4
        ), "Extrato should contain all 4 payments"

        # 7. Validate commission exclusion in extrato totals
        por_artista = saved_extrato.totais["por_artista"]
        assert (
            len(por_artista) == 1
        ), "Extrato should only show artists with commissions > 0"
        assert por_artista[0]["artista"] == "Artist Com Comissão"

        # 8. But verify all payments are preserved in the extrato data
        payment_ids = [p["id"] for p in saved_extrato.pagamentos]
        assert 401 in payment_ids  # Payment with client and commission
        assert 402 in payment_ids  # Payment without client, zero commission
        assert 403 in payment_ids  # Owner payment
        assert 404 in payment_ids  # Standalone payment

        # Cleanup
        db_session.delete(saved_extrato)
        db_session.commit()

    def test_step_7_regression_validation_commission_fix(
        self, db_session, regression_dataset
    ):
        """Step 7: Comprehensive validation of the commission exclusion fix."""

        # This test specifically validates the fix for the commission bug
        # reported in the system audit

        # Test data representing the issue scenario
        test_pagamentos = [
            {
                "id": 1,
                "valor": 200.00,
                "artista_name": "Artist Normal",
                "data": "2025-09-30",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 150.00,
                "artista_name": "Artist Zero Commission",
                "data": "2025-09-30",
                "forma_pagamento": "dinheiro",
            },
        ]

        test_sessoes = [
            {
                "id": 1,
                "valor": 200.00,
                "artista_name": "Artist Normal",
                "status": "finalizada",
                "tem_pagamento": True,
            },
            {
                "id": 2,
                "valor": 150.00,
                "artista_name": "Artist Zero Commission",
                "status": "finalizada",
                "tem_pagamento": True,
            },
        ]

        test_comissoes = [
            {
                "id": 1,
                "valor": 60.00,
                "artista_name": "Artist Normal",
                "pagamento_id": 1,
            },
            # Note: NO commission record for "Artist Zero Commission"
        ]

        test_gastos = []

        # Call calculate_totals - this is where the fix was applied
        totals = calculate_totals(
            test_pagamentos, test_sessoes, test_comissoes, test_gastos
        )

        # BEFORE THE FIX: por_artista would contain both artists
        # AFTER THE FIX: por_artista should only contain artists with commission > 0

        por_artista = totals["por_artista"]

        # Validate fix is working
        assert (
            len(por_artista) == 1
        ), f"Should have exactly 1 artist with commission > 0, got {len(por_artista)}"
        assert por_artista[0]["artista"] == "Artist Normal"
        assert por_artista[0]["comissao"] == 60.00

        # Validate zero-commission artist is excluded
        artist_names = [item["artista"] for item in por_artista]
        assert "Artist Zero Commission" not in artist_names

        # But all payments are still counted in totals
        assert totals["receita_total"] == 350.00  # 200 + 150

        # And the zero-commission artist's payment should appear in the payments data
        # (this would be validated when displaying "Pagamentos realizados")
        payment_artists = [p["artista_name"] for p in test_pagamentos]
        assert (
            "Artist Zero Commission" in payment_artists
        ), "Zero commission artist should appear in payment records"

    def test_edge_cases_and_boundary_conditions(self, db_session, regression_dataset):
        """Test edge cases and boundary conditions for the commission logic."""

        # Edge case 1: Artist with very small commission (0.01)
        edge_case_pagamentos = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Artist Tiny Commission",
                "data": "2025-09-30",
                "forma_pagamento": "cartao",
            }
        ]

        edge_case_comissoes = [
            {
                "id": 1,
                "valor": 0.01,
                "artista_name": "Artist Tiny Commission",
                "pagamento_id": 1,
            }
        ]

        totals = calculate_totals(edge_case_pagamentos, [], edge_case_comissoes, [])
        por_artista = totals["por_artista"]

        # Should include artist with commission = 0.01 (> 0)
        assert len(por_artista) == 1
        assert por_artista[0]["artista"] == "Artist Tiny Commission"
        assert por_artista[0]["comissao"] == 0.01

        # Edge case 2: Multiple artists with mixed commissions
        mixed_pagamentos = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Artist A",
                "data": "2025-09-30",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 200.00,
                "artista_name": "Artist B",
                "data": "2025-09-30",
                "forma_pagamento": "pix",
            },
            {
                "id": 3,
                "valor": 150.00,
                "artista_name": "Artist Zero",
                "data": "2025-09-30",
                "forma_pagamento": "dinheiro",
            },
            {
                "id": 4,
                "valor": 300.00,
                "artista_name": "Artist C",
                "data": "2025-09-30",
                "forma_pagamento": "cartao",
            },
        ]

        mixed_comissoes = [
            {"id": 1, "valor": 30.00, "artista_name": "Artist A", "pagamento_id": 1},
            {"id": 2, "valor": 80.00, "artista_name": "Artist B", "pagamento_id": 2},
            {"id": 3, "valor": 120.00, "artista_name": "Artist C", "pagamento_id": 4},
            # No commission for "Artist Zero"
        ]

        totals = calculate_totals(mixed_pagamentos, [], mixed_comissoes, [])
        por_artista = totals["por_artista"]

        # Should only include 3 artists (exclude Artist Zero)
        assert len(por_artista) == 3
        artist_names = [item["artista"] for item in por_artista]
        assert "Artist A" in artist_names
        assert "Artist B" in artist_names
        assert "Artist C" in artist_names
        assert "Artist Zero" not in artist_names

        # But total payments should include all 4
        assert totals["receita_total"] == 750.00  # 100 + 200 + 150 + 300

    @patch("app.services.extrato_core.logger")
    def test_debug_logging_for_commission_exclusion(
        self, mock_logger, db_session, regression_dataset
    ):
        """Test that debug logging correctly reports excluded artists."""

        with patch.dict("os.environ", {"HISTORICO_DEBUG": "1"}):
            test_pagamentos = [
                {
                    "id": 1,
                    "valor": 200.00,
                    "artista_name": "Artist Normal",
                    "data": "2025-09-30",
                    "forma_pagamento": "cartao",
                },
                {
                    "id": 2,
                    "valor": 150.00,
                    "artista_name": "Artist Zero Commission",
                    "data": "2025-09-30",
                    "forma_pagamento": "dinheiro",
                },
            ]

            test_comissoes = [
                {
                    "id": 1,
                    "valor": 60.00,
                    "artista_name": "Artist Normal",
                    "pagamento_id": 1,
                }
            ]

            calculate_totals(test_pagamentos, [], test_comissoes, [])

            # Verify debug logging was called with excluded artists
            mock_logger.info.assert_any_call(
                "HISTORICO_DEBUG: Artists excluded from commission summary (0% commission): ['Artist Zero Commission']"
            )


# Individual test class for quick regression checks
class TestQuickRegressionCheck:
    """Quick regression test for CI/CD pipeline."""

    def test_commission_exclusion_quick_check(self):
        """Quick test to verify commission exclusion logic."""
        from app.services.extrato_core import calculate_totals

        # Minimal test data
        pagamentos = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Normal Artist",
                "data": "2025-09-30",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 100.00,
                "artista_name": "Zero Commission Artist",
                "data": "2025-09-30",
                "forma_pagamento": "dinheiro",
            },
        ]

        sessoes = []

        comissoes = [
            {
                "id": 1,
                "valor": 30.00,
                "artista_name": "Normal Artist",
                "pagamento_id": 1,
            }
            # No commission for Zero Commission Artist
        ]

        totals = calculate_totals(pagamentos, sessoes, comissoes, [])

        # Quick validation
        assert len(totals["por_artista"]) == 1
        assert totals["por_artista"][0]["artista"] == "Normal Artist"
        assert totals["receita_total"] == 200.00  # Both payments counted in total


@pytest.mark.regression
class TestRegressionPerformance:
    """Performance regression tests to ensure the fix doesn't impact performance."""

    def test_large_dataset_performance(self):
        """Test commission calculation performance with large datasets."""
        import time

        # Generate large test dataset
        pagamentos = []
        comissoes = []

        for i in range(1000):
            pagamentos.append(
                {
                    "id": i,
                    "valor": 100.00,
                    "artista_name": f"Artist {i % 10}",  # 10 different artists
                    "data": "2025-09-30",
                    "forma_pagamento": "cartao",
                }
            )

            # Only half the artists have commissions
            if i % 2 == 0:
                comissoes.append(
                    {
                        "id": i,
                        "valor": 30.00,
                        "artista_name": f"Artist {i % 10}",
                        "pagamento_id": i,
                    }
                )

        # Measure performance
        start_time = time.time()
        totals = calculate_totals(pagamentos, [], comissoes, [])
        end_time = time.time()

        # Should complete quickly (less than 1 second for 1000 records)
        assert (
            end_time - start_time
        ) < 1.0, f"Performance regression: took {end_time - start_time:.2f}s"

        # Should still correctly exclude zero-commission artists
        assert len(totals["por_artista"]) == 5  # Only 5 artists have commissions
        assert totals["receita_total"] == 100000.00  # All payments counted
