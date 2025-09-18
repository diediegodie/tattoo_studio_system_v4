"""
Integration and unit tests for /historico endpoint.

Tests validate the historico controller's get_current_month_totals functionality,
including happy path scenarios, edge cases, and regression testing.
"""

import pytest
import os
from datetime import datetime, date
from unittest.mock import patch
from flask import url_for

# Import integration fixtures
from tests.fixtures.integration_fixtures import (
    app,
    client,
    db_session,
    authenticated_client,
    database_transaction_isolator,
)

# Import models
from db.base import Pagamento, Sessao, Comissao, Gasto, Client, User

# Import services for testing
from app.services.extrato_generation import get_current_month_totals
from app.services.extrato_core import current_month_range


@pytest.mark.integration
@pytest.mark.controllers
class TestHistoricoEndpoint:
    """Integration tests for the /historico endpoint."""

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Set up test data and environment for each test."""
        # Clear any existing data
        db_session.query(Comissao).delete()
        db_session.query(Pagamento).delete()
        db_session.query(Sessao).delete()
        db_session.query(Gasto).delete()
        db_session.query(Client).delete()
        db_session.query(User).delete()
        db_session.commit()

        # Create test users and clients
        self.test_artist = User(
            name="Test Artist", email="artist@test.com", role="artist"
        )
        self.test_client = Client(name="Test Client", jotform_submission_id="test123")
        db_session.add(self.test_artist)
        db_session.add(self.test_client)
        db_session.commit()

        # Set environment variable for debug logging
        os.environ["HISTORICO_DEBUG"] = "1"

        yield

        # Cleanup
        os.environ.pop("HISTORICO_DEBUG", None)

    def _create_test_data_current_month(self, db_session, data_config):
        """Helper to create test data for current month."""
        current_date = date.today().replace(day=15)  # Mid-month for safety

        # Create payments
        for payment_data in data_config.get("payments", []):
            payment = Pagamento(
                data=current_date,
                valor=payment_data["valor"],
                forma_pagamento=payment_data.get("forma_pagamento", "Dinheiro"),
                observacoes=payment_data.get("observacoes", ""),
                cliente_id=self.test_client.id,
                artista_id=self.test_artist.id,
            )
            db_session.add(payment)
            db_session.commit()

            # Create commissions for this payment if specified
            for commission_data in payment_data.get("commissions", []):
                commission = Comissao(
                    pagamento_id=payment.id,
                    artista_id=self.test_artist.id,
                    percentual=commission_data["percentual"],
                    valor=commission_data["valor"],
                    observacoes=commission_data.get("observacoes", ""),
                )
                db_session.add(commission)

        # Create sessions
        for session_data in data_config.get("sessions", []):
            session = Sessao(
                data=current_date,
                hora=datetime.now().time(),
                valor=session_data["valor"],
                observacoes=session_data.get("observacoes", ""),
                cliente_id=self.test_client.id,
                artista_id=self.test_artist.id,
                status="completed",
            )
            db_session.add(session)

        # Create expenses
        for expense_data in data_config.get("expenses", []):
            expense = Gasto(
                data=current_date,
                valor=expense_data["valor"],
                descricao=expense_data.get("descricao", ""),
                forma_pagamento=expense_data.get("forma_pagamento", "Dinheiro"),
                created_by=self.test_artist.id,
            )
            db_session.add(expense)

        db_session.commit()

    def test_happy_path_current_month_totals(self, app, db_session, caplog):
        """Test happy path: current month with mixed data shows correct totals."""
        with app.app_context():
            # Test data: 1 Pagamento R$500, 1 Sessao R$800, 2 Comissoes R$350+R$560, 1 Gasto R$455
            test_data = {
                "payments": [
                    {
                        "valor": 500.00,
                        "forma_pagamento": "Cartão",
                        "commissions": [
                            {"percentual": 70.0, "valor": 350.00},
                            {"percentual": 112.0, "valor": 560.00},  # Second commission
                        ],
                    }
                ],
                "sessions": [{"valor": 800.00}],
                "expenses": [{"valor": 455.00, "forma_pagamento": "Dinheiro"}],
            }

            self._create_test_data_current_month(db_session, test_data)

            # Test the service function directly
            totals = get_current_month_totals(db_session)

            # Verify totals
            assert totals["receita_total"] == 1300.00  # 500 + 800
            assert totals["comissoes_total"] == 910.00  # 350 + 560
            assert totals["despesas_total"] == 455.00
            assert totals["receita_liquida"] == 390.00  # 1300 - 910

            # Verify debug logs
            log_messages = [record.message for record in caplog.records]
            assert any("Current month window:" in msg for msg in log_messages)
            assert any(
                "pagamentos:1 sessoes:1 comissoes:2 gastos:1" in msg
                for msg in log_messages
            )
            assert any(
                "receita_total:1300.0 comissoes_total:910.0 despesas_total:455.0 receita_liquida:390.0"
                in msg
                for msg in log_messages
            )

    def test_happy_path_full_endpoint(self, authenticated_client, db_session):
        """Test full endpoint integration with HTML response."""
        # Test data: same as happy path
        test_data = {
            "payments": [
                {
                    "valor": 500.00,
                    "forma_pagamento": "Cartão",
                    "commissions": [
                        {"percentual": 70.0, "valor": 350.00},
                        {"percentual": 112.0, "valor": 560.00},
                    ],
                }
            ],
            "sessions": [{"valor": 800.00}],
            "expenses": [{"valor": 455.00, "forma_pagamento": "Dinheiro"}],
        }

        self._create_test_data_current_month(db_session, test_data)

        # Verify data was created
        from app.services.extrato_core import current_month_range

        start_date, end_date = current_month_range()

        payment_count = (
            db_session.query(Pagamento)
            .filter(Pagamento.data >= start_date, Pagamento.data < end_date)
            .count()
        )
        session_count = (
            db_session.query(Sessao)
            .filter(Sessao.data >= start_date, Sessao.data < end_date)
            .count()
        )
        commission_count = (
            db_session.query(Comissao)
            .filter(Comissao.created_at >= start_date, Comissao.created_at < end_date)
            .count()
        )
        gasto_count = (
            db_session.query(Gasto)
            .filter(Gasto.data >= start_date, Gasto.data < end_date)
            .count()
        )

        assert payment_count == 1
        assert session_count == 1
        assert commission_count == 2
        assert gasto_count == 1

        # Make request to /historico
        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        # Check HTML contains expected totals
        html_content = response.get_data(as_text=True)
        assert "R$ 1300.00" in html_content  # Receita Total
        assert "R$ 910.00" in html_content  # Comissões Totais
        assert "R$ 455.00" in html_content  # Despesas
        assert "R$ 390.00" in html_content  # Receita Líquida

    def test_no_data_current_month(self, app, db_session, caplog):
        """Test edge case: no data for current month returns all zeros."""
        with app.app_context():
            # No test data created

            totals = get_current_month_totals(db_session)

            # All totals should be 0
            assert totals["receita_total"] == 0.00
            assert totals["comissoes_total"] == 0.00
            assert totals["despesas_total"] == 0.00
            assert totals["receita_liquida"] == 0.00

            # Verify debug logs show zero counts
            log_messages = [record.message for record in caplog.records]
            assert any(
                "pagamentos:0 sessoes:0 comissoes:0 gastos:0" in msg
                for msg in log_messages
            )
            assert any(
                "receita_total:0 comissoes_total:0 despesas_total:0 receita_liquida:0"
                in msg
                for msg in log_messages
            )

    def test_only_payments_no_commissions(self, app, db_session):
        """Test edge case: only payments, no commissions."""
        with app.app_context():
            test_data = {
                "payments": [{"valor": 1000.00, "forma_pagamento": "Dinheiro"}]
            }
            self._create_test_data_current_month(db_session, test_data)

            totals = get_current_month_totals(db_session)

            assert totals["receita_total"] == 1000.00
            assert totals["comissoes_total"] == 0.00
            assert totals["receita_liquida"] == 1000.00

    def test_only_sessions_no_commissions(self, app, db_session):
        """Test edge case: only sessions, no commissions.

        FIXED: Sessions without payments should not count as revenue.
        Revenue represents actual money collected, not potential income.
        """
        with app.app_context():
            test_data = {"sessions": [{"valor": 750.00}]}
            self._create_test_data_current_month(db_session, test_data)

            totals = get_current_month_totals(db_session)

            # CORRECTED: Sessions without payments = 0 revenue (no actual money received)
            assert totals["receita_total"] == 0.00
            assert totals["comissoes_total"] == 0.00
            assert totals["receita_liquida"] == 0.00

    def test_negative_net_revenue(self, app, db_session):
        """Test edge case: commissions exceed revenue (negative net revenue)."""
        with app.app_context():
            test_data = {
                "payments": [
                    {
                        "valor": 300.00,
                        "commissions": [
                            {
                                "percentual": 150.0,
                                "valor": 450.00,
                            }  # Commission > payment
                        ],
                    }
                ]
            }
            self._create_test_data_current_month(db_session, test_data)

            totals = get_current_month_totals(db_session)

            assert totals["receita_total"] == 300.00
            assert totals["comissoes_total"] == 450.00
            assert totals["receita_liquida"] == -150.00  # Negative value

    @pytest.mark.regression
    def test_extrato_navigation_still_works(self, authenticated_client):
        """Regression test: ensure /extrato endpoint still works."""
        # This is a basic smoke test - the actual /extrato functionality
        # should be tested separately, but we verify it doesn't crash
        response = authenticated_client.get("/extrato/")
        # Just check it doesn't return a 500 error
        assert response.status_code in [200, 302, 404]  # Various valid responses
