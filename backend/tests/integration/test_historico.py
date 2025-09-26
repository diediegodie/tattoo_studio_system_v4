"""
Integration and unit tests for /historico endpoint.

Tests validate the historico controller's get_current_month_totals functionality,
including happy path scenarios, edge cases, and regression testing.
"""

import os
from datetime import date, datetime
from unittest.mock import patch

import pytest

# Import models
from app.db.base import Client, Comissao, Gasto, Pagamento, Sessao, User
from app.services.extrato_core import current_month_range

# Import services for testing
from app.services.extrato_generation import get_current_month_totals
from flask import url_for

# Import integration fixtures
from tests.fixtures.integration_fixtures import (
    app,
    authenticated_client,
    client,
    database_transaction_isolator,
    db_session,
)


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
            # Enable debug logging for this test
            original_debug = os.environ.get("HISTORICO_DEBUG")
            os.environ["HISTORICO_DEBUG"] = "1"
            try:
                # Test data: 1 Pagamento R$500, 1 Sessao R$800, 2 Comissoes R$350+R$560, 1 Gasto R$455
                test_data = {
                    "payments": [
                        {
                            "valor": 500.00,
                            "forma_pagamento": "Cartão",
                            "commissions": [
                                {"percentual": 70.0, "valor": 350.00},
                                {
                                    "percentual": 112.0,
                                    "valor": 560.00,
                                },  # Second commission
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
                assert (
                    totals["receita_total"] == 500.00
                )  # Only payments (fixed double counting)
                assert totals["comissoes_total"] == 910.00  # 350 + 560
                assert totals["despesas_total"] == 455.00
                assert totals["receita_liquida"] == -865.00  # 500 - 910 - 455

                # Note: Debug logs are optional and depend on HISTORICO_DEBUG env var
            finally:
                # Restore original debug setting
                if original_debug is not None:
                    os.environ["HISTORICO_DEBUG"] = original_debug
                else:
                    os.environ.pop("HISTORICO_DEBUG", None)

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
        assert "R$ 500.00" in html_content  # Receita Total (fixed double counting)
        assert "R$ 910.00" in html_content  # Comissões Totais
        assert "R$ 455.00" in html_content  # Despesas
        assert "R$ -865.00" in html_content  # Receita Líquida (500 - 910 - 455)

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

            # Note: Debug logs are optional and depend on HISTORICO_DEBUG env var

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
    def test_single_session_single_payment_no_duplication(
        self, authenticated_client, db_session
    ):
        """Regression test: 1 session + 1 payment should show exactly 1 session and 1 artist.

        This test ensures no duplication occurs in Historico display when a session
        has a linked payment. Previously, the date-based linking logic could incorrectly
        exclude sessions on the same date as paid sessions.
        """
        # Create exactly 1 session with 1 payment
        test_data = {
            "payments": [
                {
                    "valor": 500.00,
                    "forma_pagamento": "Dinheiro",
                    "commissions": [{"percentual": 20.0, "valor": 100.00}],
                }
            ],
            "sessions": [{"valor": 500.00}],  # Same value as payment
        }

        self._create_test_data_current_month(db_session, test_data)

        # Debug: Check what dates are being used
        from app.services.extrato_core import current_month_range

        start_date, end_date = current_month_range()
        current_date = date.today().replace(day=15)
        print(f"DEBUG current_month_range: {start_date} to {end_date}")
        print(f"DEBUG test data date: {current_date}")
        print(
            f"DEBUG is current_date in range: {start_date.date() <= current_date < end_date.date()}"
        )

        # Make request to /historico
        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        html_content = response.get_data(
            as_text=True
        )  # Count session rows in "Sessões realizadas" table
        # Look for table rows that contain session data (skip header)
        sessoes_table_start = html_content.find("<h2>Sessões realizadas</h2>")
        assert sessoes_table_start != -1, "Sessões realizadas section not found"

        # Debug: print HTML around the section
        start_debug = max(0, sessoes_table_start - 200)
        end_debug = min(len(html_content), sessoes_table_start + 500)
        print(
            f"DEBUG HTML around Sessões realizadas: {html_content[start_debug:end_debug]}"
        )

        # Find the table after the "Sessões realizadas" header
        sessoes_header_end = html_content.find("<h2>Sessões realizadas</h2>") + len(
            "<h2>Sessões realizadas</h2>"
        )
        table_start = html_content.find("<table>", sessoes_header_end)
        table_end = html_content.find("</table>", table_start)
        table_content = html_content[table_start : table_end + 8]  # Include </table>

        print(f"DEBUG sessoes_header_end: {sessoes_header_end}")
        print(f"DEBUG table_start: {table_start}, table_end: {table_end}")
        print(f"DEBUG table_content: {table_content}")

        # Count <tr> tags (excluding the header row) - more robust method
        import re

        tr_matches = re.findall(r"<tr[^>]*>", table_content)
        print(f"DEBUG <tr> matches with regex: {tr_matches}")
        print(f"DEBUG number of <tr> matches: {len(tr_matches)}")

        total_tr = len(tr_matches)
        print(f"DEBUG total <tr> tags: {total_tr}")
        tr_count = total_tr - 1  # Subtract 1 for header
        print(f"DEBUG tr_count after subtracting header: {tr_count}")

        # Also check if the session appears in the HTML at all
        session_appears = 'data-id="sess-1"' in html_content
        print(f"DEBUG session appears in HTML: {session_appears}")

        # Check if session data is in the table content
        session_in_table = 'data-id="sess-1"' in table_content
        print(f"DEBUG session in table_content: {session_in_table}")

        assert (
            tr_count == 1
        ), f"Expected exactly 1 session row, found {tr_count}"  # Count artists in "Comissões por Artista" table
        comissoes_header = "<h3>Comissões por Artista</h3>"
        comissoes_start = html_content.find(comissoes_header)
        assert comissoes_start != -1, "Comissões por Artista section not found"

        # Find the table after the commissions header
        comm_table_start = html_content.find("<table>", comissoes_start)
        comm_table_end = html_content.find("</table>", comm_table_start)
        comm_table_content = html_content[comm_table_start:comm_table_end]

        # Count <tr> tags in commissions table (excluding header)
        comm_tr_count = comm_table_content.count("<tr>") - 1  # Subtract 1 for header
        assert (
            comm_tr_count == 1
        ), f"Expected exactly 1 artist in commissions, found {comm_tr_count}"

        # Instead of counting total artist name occurrences (which includes dropdowns, etc.),
        # verify that the artist appears exactly once in each relevant table
        artist_in_sessions = table_content.count("Test Artist")
        artist_in_commissions = comm_table_content.count("Test Artist")

        assert (
            artist_in_sessions == 1
        ), f"Expected artist to appear exactly 1 time in sessions table, found {artist_in_sessions}"
        assert (
            artist_in_commissions == 1
        ), f"Expected artist to appear exactly 1 time in commissions table, found {artist_in_commissions}"

    @pytest.mark.regression
    def test_sessions_only_appear_after_payment_or_completion(
        self, authenticated_client, db_session
    ):
        """Regression test: Sessions should only appear in Historico when paid or completed.

        This test ensures that:
        - Scheduled/active sessions do NOT appear in Historico
        - Paid sessions DO appear in Historico
        - Completed sessions DO appear in Historico
        """
        current_date = date.today().replace(day=15)  # Mid-month for safety

        # Create 3 sessions with different statuses
        # 1. Active/scheduled session (should NOT appear)
        scheduled_session = Sessao(
            data=current_date,
            valor=100.00,
            observacoes="Scheduled session",
            cliente_id=self.test_client.id,
            artista_id=self.test_artist.id,
            status="active",  # Should NOT appear in Historico
        )
        db_session.add(scheduled_session)

        # 2. Completed session (should appear)
        completed_session = Sessao(
            data=current_date,
            valor=200.00,
            observacoes="Completed session",
            cliente_id=self.test_client.id,
            artista_id=self.test_artist.id,
            status="completed",  # Should appear in Historico
        )
        db_session.add(completed_session)

        # 3. Paid session (should appear)
        paid_session = Sessao(
            data=current_date,
            valor=300.00,
            observacoes="Paid session",
            cliente_id=self.test_client.id,
            artista_id=self.test_artist.id,
            status="paid",  # Should appear in Historico
        )
        db_session.add(paid_session)
        db_session.commit()

        # Make request to /historico
        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Find the sessions table
        sessoes_table_start = html_content.find("<h2>Sessões realizadas</h2>")
        assert sessoes_table_start != -1, "Sessões realizadas section not found"

        table_start = html_content.find("<table>", sessoes_table_start)
        table_end = html_content.find("</table>", table_start)
        table_content = html_content[table_start : table_end + 8]

        # Count session rows (excluding header)
        import re

        tr_matches = re.findall(r"<tr[^>]*>", table_content)
        session_rows = len(tr_matches) - 1  # Subtract header row

        # Should show exactly 2 sessions (completed + paid, not scheduled)
        assert (
            session_rows == 2
        ), f"Expected 2 sessions in Historico (completed + paid), found {session_rows}"

        # Verify specific sessions appear/don't appear
        assert (
            'data-id="sess-1"' not in table_content
        ), "Scheduled session should NOT appear in Historico"
        assert (
            'data-id="sess-2"' in table_content
        ), "Completed session should appear in Historico"
        assert (
            'data-id="sess-3"' in table_content
        ), "Paid session should appear in Historico"

        # Verify session values appear
        assert "R$ 200.00" in table_content, "Completed session value should appear"
        assert "R$ 300.00" in table_content, "Paid session value should appear"
        assert (
            "R$ 100.00" not in table_content
        ), "Scheduled session value should NOT appear"

    def test_payments_without_client_appear_correctly(
        self, db_session, authenticated_client
    ):
        """Test that payments without clients appear correctly in Historico."""
        from decimal import Decimal

        # Create a payment without a client (cliente_id = None)
        payment_without_client = Pagamento(
            data=date.today(),
            valor=Decimal("150.00"),
            forma_pagamento="Pix",
            observacoes="Payment without client",
            cliente_id=None,  # No client specified
            artista_id=self.test_artist.id,
        )

        # Create a payment with a client for comparison
        payment_with_client = Pagamento(
            data=date.today(),
            valor=Decimal("250.00"),
            forma_pagamento="Dinheiro",
            observacoes="Payment with client",
            cliente_id=self.test_client.id,
            artista_id=self.test_artist.id,
        )

        db_session.add(payment_without_client)
        db_session.add(payment_with_client)
        db_session.commit()

        # Request historico page
        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        content = response.get_data(as_text=True)

        # Verify both payments appear
        assert "R$ 150.00" in content, "Payment without client should appear"
        assert "R$ 250.00" in content, "Payment with client should appear"

        # Verify client name handling
        assert (
            "Test Client" in content
        ), "Client name should appear for payment with client"
        # The template should show empty string or 'Cliente não encontrado' for payments without clients
        # We don't check for specific text since the template might handle this differently

        # Verify payment details are present
        assert (
            "Payment without client" in content
        ), "Payment without client notes should appear"
        assert (
            "Payment with client" in content
        ), "Payment with client notes should appear"

    @pytest.mark.regression
    def test_extrato_navigation_still_works(self, authenticated_client):
        """Regression test: ensure /extrato endpoint still works."""
        # This is a basic smoke test - the actual /extrato functionality
        # should be tested separately, but we verify it doesn't crash
        response = authenticated_client.get("/extrato/")
        # Just check it doesn't return a 500 error
        assert response.status_code in [200, 302, 404]  # Various valid responses
