"""Integration tests for monthly report (extrato mensal) functionality.

These tests validate the monthly aggregation logic for sessions, payments,
commissions, and expenses, ensuring accurate totals and correct filtering
by month/year. They complement existing historico tests by focusing on
multi-month scenarios and edge cases around net revenue calculations.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.db.base import Client, Comissao, Gasto, Pagamento, Sessao, User
from app.services.extrato_core import calculate_totals, current_month_range


@pytest.mark.integration
@pytest.mark.extrato
class TestMonthlyReportAggregation:
    """Integration tests for monthly report data aggregation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Set up test data and environment for each test."""
        # Clear existing data
        db_session.query(Comissao).delete()
        db_session.query(Pagamento).delete()
        db_session.query(Sessao).delete()
        db_session.query(Gasto).delete()
        db_session.query(Client).delete()
        db_session.query(User).delete()
        db_session.commit()

        # Create test users and clients
        self.test_artist_1 = User()
        self.test_artist_1.name = "Artist One"
        self.test_artist_1.email = f"artist1.{uuid.uuid4().hex[:8]}@test.com"
        self.test_artist_1.role = "artist"

        self.test_artist_2 = User()
        self.test_artist_2.name = "Artist Two"
        self.test_artist_2.email = f"artist2.{uuid.uuid4().hex[:8]}@test.com"
        self.test_artist_2.role = "artist"

        self.test_client_1 = Client()
        self.test_client_1.name = "Client One"
        self.test_client_1.jotform_submission_id = f"test-{uuid.uuid4().hex[:8]}"

        self.test_client_2 = Client()
        self.test_client_2.name = "Client Two"
        self.test_client_2.jotform_submission_id = f"test-{uuid.uuid4().hex[:8]}"

        db_session.add_all(
            [
                self.test_artist_1,
                self.test_artist_2,
                self.test_client_1,
                self.test_client_2,
            ]
        )
        db_session.commit()

    def test_single_month_with_complete_data(self, db_session):
        """Test monthly report with all data types for a single month."""

        target_date = date(2025, 3, 15)  # March 2025

        # Create 2 payments with commissions
        payment_1 = Pagamento(
            data=target_date,
            valor=Decimal("1000.00"),
            forma_pagamento="Cartão",
            observacoes="Payment 1",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        payment_2 = Pagamento(
            data=target_date + timedelta(days=5),
            valor=Decimal("500.00"),
            forma_pagamento="Pix",
            observacoes="Payment 2",
            cliente_id=self.test_client_2.id,
            artista_id=self.test_artist_2.id,
        )
        db_session.add_all([payment_1, payment_2])
        db_session.commit()

        # Create sessions linked to payments
        session_1 = Sessao(
            data=target_date,
            valor=Decimal("1000.00"),
            observacoes="Session 1",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
            status="completed",
            payment_id=payment_1.id,
        )
        session_2 = Sessao(
            data=target_date + timedelta(days=5),
            valor=Decimal("500.00"),
            observacoes="Session 2",
            cliente_id=self.test_client_2.id,
            artista_id=self.test_artist_2.id,
            status="completed",
            payment_id=payment_2.id,
        )
        db_session.add_all([session_1, session_2])
        db_session.commit()

        # Create commissions
        commission_1 = Comissao(
            pagamento_id=payment_1.id,
            artista_id=self.test_artist_1.id,
            percentual=Decimal("50.0"),
            valor=Decimal("500.00"),
            observacoes="50% commission",
        )
        commission_2 = Comissao(
            pagamento_id=payment_2.id,
            artista_id=self.test_artist_2.id,
            percentual=Decimal("60.0"),
            valor=Decimal("300.00"),
            observacoes="60% commission",
        )
        db_session.add_all([commission_1, commission_2])
        db_session.commit()

        # Create expenses
        expense_1 = Gasto(
            data=target_date,
            valor=Decimal("200.00"),
            descricao="Supplies",
            forma_pagamento="Dinheiro",
            created_by=self.test_artist_1.id,
        )
        expense_2 = Gasto(
            data=target_date + timedelta(days=3),
            valor=Decimal("150.00"),
            descricao="Utilities",
            forma_pagamento="Cartão",
            created_by=self.test_artist_1.id,
        )
        db_session.add_all([expense_1, expense_2])
        db_session.commit()

        # Query all data for March 2025
        pagamentos = (
            db_session.query(Pagamento)
            .filter(
                Pagamento.data >= date(2025, 3, 1), Pagamento.data < date(2025, 4, 1)
            )
            .all()
        )
        sessoes = (
            db_session.query(Sessao)
            .filter(Sessao.data >= date(2025, 3, 1), Sessao.data < date(2025, 4, 1))
            .all()
        )
        # Query commissions linked to payments in the target month
        # This matches the production logic in extrato_core.py
        comissoes = (
            db_session.query(Comissao)
            .join(Pagamento, Comissao.pagamento_id == Pagamento.id)
            .filter(
                Pagamento.data >= date(2025, 3, 1), Pagamento.data < date(2025, 4, 1)
            )
            .all()
        )
        gastos = (
            db_session.query(Gasto)
            .filter(Gasto.data >= date(2025, 3, 1), Gasto.data < date(2025, 4, 1))
            .all()
        )

        # Serialize data for calculate_totals with proper artist lookups
        artist_map = {
            self.test_artist_1.id: self.test_artist_1,
            self.test_artist_2.id: self.test_artist_2,
        }

        pagamentos_data = [
            {
                "id": p.id,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "sessao_id": getattr(p, "sessao_id", None),
                "artista_name": (
                    artist_map[p.artista_id].name
                    if p.artista_id in artist_map
                    else None
                ),
            }
            for p in pagamentos
        ]
        sessoes_data = [
            {
                "id": s.id,
                "valor": float(s.valor),
                "artista_name": (
                    artist_map[s.artista_id].name
                    if s.artista_id in artist_map
                    else None
                ),
                "payment_id": s.payment_id,
            }
            for s in sessoes
        ]
        comissoes_data = [
            {
                "id": c.id,
                "valor": float(c.valor),
                "percentual": float(c.percentual),
                "artista_name": (
                    artist_map[c.artista_id].name
                    if c.artista_id in artist_map
                    else None
                ),
                "pagamento_id": c.pagamento_id,
            }
            for c in comissoes
        ]
        gastos_data = [
            {
                "id": g.id,
                "valor": float(g.valor),
                "descricao": g.descricao,
                "forma_pagamento": g.forma_pagamento,
            }
            for g in gastos
        ]

        # Calculate totals
        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Assertions
        assert totals["receita_total"] == 1500.00  # 1000 + 500
        assert totals["comissoes_total"] == 800.00  # 500 + 300
        assert totals["despesas_total"] == 350.00  # 200 + 150
        assert totals["receita_liquida"] == 350.00  # 1500 - 800 - 350

        # Verify per-artist breakdown
        assert len(totals["por_artista"]) == 2
        artist_names = {a["artista"] for a in totals["por_artista"]}
        assert artist_names == {"Artist One", "Artist Two"}

        # Verify payment method breakdown
        assert len(totals["por_forma_pagamento"]) == 2
        payment_methods = {p["forma"] for p in totals["por_forma_pagamento"]}
        assert payment_methods == {"Cartão", "Pix"}

    def test_no_data_for_target_month(self, db_session):
        """Test monthly report when no data exists for the selected month."""

        # Create data for a different month (February)
        feb_date = date(2025, 2, 10)
        payment = Pagamento(
            data=feb_date,
            valor=Decimal("500.00"),
            forma_pagamento="Dinheiro",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        db_session.add(payment)
        db_session.commit()

        # Query for March (should return nothing)
        pagamentos = (
            db_session.query(Pagamento)
            .filter(
                Pagamento.data >= date(2025, 3, 1), Pagamento.data < date(2025, 4, 1)
            )
            .all()
        )
        sessoes = (
            db_session.query(Sessao)
            .filter(Sessao.data >= date(2025, 3, 1), Sessao.data < date(2025, 4, 1))
            .all()
        )
        # Query commissions linked to payments in the target month
        comissoes = (
            db_session.query(Comissao)
            .join(Pagamento, Comissao.pagamento_id == Pagamento.id)
            .filter(
                Pagamento.data >= date(2025, 3, 1), Pagamento.data < date(2025, 4, 1)
            )
            .all()
        )
        gastos = (
            db_session.query(Gasto)
            .filter(Gasto.data >= date(2025, 3, 1), Gasto.data < date(2025, 4, 1))
            .all()
        )

        # Verify queries return empty results
        assert pagamentos == []
        assert sessoes == []
        assert comissoes == []
        assert gastos == []

        totals = calculate_totals([], [], [], [])

        # All totals should be zero
        assert totals["receita_total"] == 0.00
        assert totals["comissoes_total"] == 0.00
        assert totals["despesas_total"] == 0.00
        assert totals["receita_liquida"] == 0.00
        assert len(totals["por_artista"]) == 0
        assert len(totals["por_forma_pagamento"]) == 0

    def test_multi_month_filtering(self, db_session):
        """Test that data is correctly filtered by month boundaries."""

        # Create data across 3 months
        # January payment
        jan_payment = Pagamento(
            data=date(2025, 1, 15),
            valor=Decimal("100.00"),
            forma_pagamento="Dinheiro",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        # February payment
        feb_payment = Pagamento(
            data=date(2025, 2, 15),
            valor=Decimal("200.00"),
            forma_pagamento="Cartão",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        # March payment
        mar_payment = Pagamento(
            data=date(2025, 3, 15),
            valor=Decimal("300.00"),
            forma_pagamento="Pix",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        db_session.add_all([jan_payment, feb_payment, mar_payment])
        db_session.commit()

        # Query only February data
        feb_pagamentos = (
            db_session.query(Pagamento)
            .filter(
                Pagamento.data >= date(2025, 2, 1), Pagamento.data < date(2025, 3, 1)
            )
            .all()
        )

        assert len(feb_pagamentos) == 1
        assert feb_pagamentos[0].valor == Decimal("200.00")

        # Calculate totals for February only
        feb_data = [
            {
                "id": p.id,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "sessao_id": None,
                "artista_name": self.test_artist_1.name,
            }
            for p in feb_pagamentos
        ]
        totals = calculate_totals(feb_data, [], [], [])

        assert totals["receita_total"] == 200.00

    def test_expenses_reduce_net_revenue(self, db_session):
        """Test that expenses correctly reduce net revenue."""

        target_date = date(2025, 4, 10)

        # Revenue: R$1000
        payment = Pagamento(
            data=target_date,
            valor=Decimal("1000.00"),
            forma_pagamento="Cartão",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        db_session.add(payment)
        db_session.commit()

        # Commissions: R$400
        commission = Comissao(
            pagamento_id=payment.id,
            artista_id=self.test_artist_1.id,
            percentual=Decimal("40.0"),
            valor=Decimal("400.00"),
        )
        db_session.add(commission)
        db_session.commit()

        # Expenses: R$250
        expense = Gasto(
            data=target_date,
            valor=Decimal("250.00"),
            descricao="Equipment",
            forma_pagamento="Dinheiro",
            created_by=self.test_artist_1.id,
        )
        db_session.add(expense)
        db_session.commit()

        # Query and calculate
        pagamentos_data = [
            {
                "id": payment.id,
                "valor": float(payment.valor),
                "forma_pagamento": payment.forma_pagamento,
                "sessao_id": None,
                "artista_name": self.test_artist_1.name,
            }
        ]
        comissoes_data = [
            {
                "id": commission.id,
                "valor": float(commission.valor),
                "percentual": float(commission.percentual),
                "artista_name": self.test_artist_1.name,
                "pagamento_id": commission.pagamento_id,
            }
        ]
        gastos_data = [
            {
                "id": expense.id,
                "valor": float(expense.valor),
                "descricao": expense.descricao,
                "forma_pagamento": expense.forma_pagamento,
            }
        ]

        totals = calculate_totals(pagamentos_data, [], comissoes_data, gastos_data)

        # Net revenue = 1000 - 400 - 250 = 350
        assert totals["receita_total"] == 1000.00
        assert totals["comissoes_total"] == 400.00
        assert totals["despesas_total"] == 250.00
        assert totals["receita_liquida"] == 350.00

    def test_negative_net_revenue_high_expenses(self, db_session):
        """Test edge case where expenses exceed gross revenue."""

        target_date = date(2025, 5, 20)

        # Low revenue
        payment = Pagamento(
            data=target_date,
            valor=Decimal("500.00"),
            forma_pagamento="Dinheiro",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        db_session.add(payment)
        db_session.commit()

        # High commissions
        commission = Comissao(
            pagamento_id=payment.id,
            artista_id=self.test_artist_1.id,
            percentual=Decimal("70.0"),
            valor=Decimal("350.00"),
        )
        db_session.add(commission)
        db_session.commit()

        # High expenses
        expense = Gasto(
            data=target_date,
            valor=Decimal("400.00"),
            descricao="Major repair",
            forma_pagamento="Cartão",
            created_by=self.test_artist_1.id,
        )
        db_session.add(expense)
        db_session.commit()

        pagamentos_data = [
            {
                "id": payment.id,
                "valor": float(payment.valor),
                "forma_pagamento": payment.forma_pagamento,
                "sessao_id": None,
                "artista_name": self.test_artist_1.name,
            }
        ]
        comissoes_data = [
            {
                "id": commission.id,
                "valor": float(commission.valor),
                "percentual": float(commission.percentual),
                "artista_name": self.test_artist_1.name,
                "pagamento_id": commission.pagamento_id,
            }
        ]
        gastos_data = [
            {
                "id": expense.id,
                "valor": float(expense.valor),
                "descricao": expense.descricao,
                "forma_pagamento": expense.forma_pagamento,
            }
        ]

        totals = calculate_totals(pagamentos_data, [], comissoes_data, gastos_data)

        # Net revenue = 500 - 350 - 400 = -250
        assert totals["receita_liquida"] == -250.00

    def test_multiple_payment_methods(self, db_session):
        """Test that payment method breakdown is calculated correctly."""

        target_date = date(2025, 6, 5)

        # Create payments with different methods
        payment_cash = Pagamento(
            data=target_date,
            valor=Decimal("300.00"),
            forma_pagamento="Dinheiro",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        payment_card = Pagamento(
            data=target_date + timedelta(days=1),
            valor=Decimal("500.00"),
            forma_pagamento="Cartão",
            cliente_id=self.test_client_2.id,
            artista_id=self.test_artist_2.id,
        )
        payment_pix = Pagamento(
            data=target_date + timedelta(days=2),
            valor=Decimal("200.00"),
            forma_pagamento="Pix",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        db_session.add_all([payment_cash, payment_card, payment_pix])
        db_session.commit()

        artist_map = {
            self.test_artist_1.id: self.test_artist_1,
            self.test_artist_2.id: self.test_artist_2,
        }
        pagamentos_data = [
            {
                "id": p.id,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "sessao_id": None,
                "artista_name": (
                    artist_map[p.artista_id].name
                    if p.artista_id in artist_map
                    else None
                ),
            }
            for p in [payment_cash, payment_card, payment_pix]
        ]

        totals = calculate_totals(pagamentos_data, [], [], [])

        # Verify payment method breakdown
        payment_breakdown = totals["por_forma_pagamento"]
        assert len(payment_breakdown) == 3

        methods_dict = {item["forma"]: item["total"] for item in payment_breakdown}
        assert methods_dict["Dinheiro"] == 300.00
        assert methods_dict["Cartão"] == 500.00
        assert methods_dict["Pix"] == 200.00

    def test_multiple_artists_commission_breakdown(self, db_session):
        """Test that per-artist commission breakdown is calculated correctly."""

        target_date = date(2025, 7, 10)

        # Create payments for different artists
        payment_1 = Pagamento(
            data=target_date,
            valor=Decimal("1000.00"),
            forma_pagamento="Cartão",
            cliente_id=self.test_client_1.id,
            artista_id=self.test_artist_1.id,
        )
        payment_2 = Pagamento(
            data=target_date,
            valor=Decimal("800.00"),
            forma_pagamento="Dinheiro",
            cliente_id=self.test_client_2.id,
            artista_id=self.test_artist_2.id,
        )
        db_session.add_all([payment_1, payment_2])
        db_session.commit()

        # Create commissions
        commission_1 = Comissao(
            pagamento_id=payment_1.id,
            artista_id=self.test_artist_1.id,
            percentual=Decimal("50.0"),
            valor=Decimal("500.00"),
        )
        commission_2 = Comissao(
            pagamento_id=payment_2.id,
            artista_id=self.test_artist_2.id,
            percentual=Decimal("60.0"),
            valor=Decimal("480.00"),
        )
        db_session.add_all([commission_1, commission_2])
        db_session.commit()

        artist_map = {
            self.test_artist_1.id: self.test_artist_1,
            self.test_artist_2.id: self.test_artist_2,
        }

        pagamentos_data = [
            {
                "id": p.id,
                "valor": float(p.valor),
                "forma_pagamento": p.forma_pagamento,
                "sessao_id": None,
                "artista_name": (
                    artist_map[p.artista_id].name
                    if p.artista_id in artist_map
                    else None
                ),
            }
            for p in [payment_1, payment_2]
        ]
        comissoes_data = [
            {
                "id": commission_1.id,
                "valor": float(commission_1.valor),
                "percentual": float(commission_1.percentual),
                "artista_name": self.test_artist_1.name,
                "pagamento_id": commission_1.pagamento_id,
            },
            {
                "id": commission_2.id,
                "valor": float(commission_2.valor),
                "percentual": float(commission_2.percentual),
                "artista_name": self.test_artist_2.name,
                "pagamento_id": commission_2.pagamento_id,
            },
        ]

        totals = calculate_totals(pagamentos_data, [], comissoes_data, [])

        # Verify artist breakdown
        artist_breakdown = totals["por_artista"]
        assert len(artist_breakdown) == 2

        artists_dict = {item["artista"]: item for item in artist_breakdown}
        assert artists_dict["Artist One"]["comissao"] == 500.00
        assert artists_dict["Artist Two"]["comissao"] == 480.00


@pytest.mark.integration
@pytest.mark.extrato
class TestMonthlyReportEndpoint:
    """Integration tests for the monthly report HTTP endpoint."""

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Set up test data for endpoint tests."""
        db_session.query(Comissao).delete()
        db_session.query(Pagamento).delete()
        db_session.query(Sessao).delete()
        db_session.query(Gasto).delete()
        db_session.query(Client).delete()
        db_session.query(User).delete()
        db_session.commit()

        self.test_artist = User()
        self.test_artist.name = "Test Artist"
        self.test_artist.email = f"artist.{uuid.uuid4().hex[:8]}@test.com"
        self.test_artist.role = "artist"

        self.test_client = Client()
        self.test_client.name = "Test Client"
        self.test_client.jotform_submission_id = f"test-{uuid.uuid4().hex[:8]}"
        db_session.add_all([self.test_artist, self.test_client])
        db_session.commit()

    def test_historico_endpoint_renders_current_month_totals(
        self, authenticated_client, db_session
    ):
        """Test that /historico endpoint renders current month totals correctly."""

        # Get current month range
        start_date, end_date = current_month_range()
        mid_month = start_date.date() + timedelta(days=10)

        # Create test data for current month
        payment = Pagamento(
            data=mid_month,
            valor=Decimal("750.00"),
            forma_pagamento="Cartão",
            cliente_id=self.test_client.id,
            artista_id=self.test_artist.id,
        )
        db_session.add(payment)
        db_session.commit()

        commission = Comissao(
            pagamento_id=payment.id,
            artista_id=self.test_artist.id,
            percentual=Decimal("40.0"),
            valor=Decimal("300.00"),
        )
        db_session.add(commission)
        db_session.commit()

        expense = Gasto(
            data=mid_month,
            valor=Decimal("100.00"),
            descricao="Test expense",
            forma_pagamento="Dinheiro",
            created_by=self.test_artist.id,
        )
        db_session.add(expense)
        db_session.commit()

        # Make request
        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        # Verify totals appear in HTML
        # Note: HTML formatting may vary, so we check for the values
        assert "750.00" in html  # Receita total
        assert "300.00" in html  # Comissões
        assert "100.00" in html  # Despesas
        # Net revenue: 750 - 300 - 100 = 350
        assert "350.00" in html

    def test_historico_endpoint_with_no_data(self, authenticated_client, db_session):
        """Test that /historico endpoint handles empty data gracefully."""

        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        # Should not crash and should show zero totals or empty state
        # The exact rendering depends on the template
        assert "Totais do Mês Atual" in html or "Histórico" in html

    def test_label_matches_calculation(self, authenticated_client, db_session):
        """Test that the rendered label matches the actual calculation formula."""

        # Get current month
        start_date, end_date = current_month_range()
        mid_month = start_date.date() + timedelta(days=10)

        # Create minimal data
        payment = Pagamento(
            data=mid_month,
            valor=Decimal("1000.00"),
            forma_pagamento="Dinheiro",
            cliente_id=self.test_client.id,
            artista_id=self.test_artist.id,
        )
        db_session.add(payment)
        db_session.commit()

        commission = Comissao(
            pagamento_id=payment.id,
            artista_id=self.test_artist.id,
            percentual=Decimal("30.0"),
            valor=Decimal("300.00"),
        )
        db_session.add(commission)
        db_session.commit()

        expense = Gasto(
            data=mid_month,
            valor=Decimal("150.00"),
            descricao="Materials",
            forma_pagamento="Cartão",
            created_by=self.test_artist.id,
        )
        db_session.add(expense)
        db_session.commit()

        response = authenticated_client.get("/historico/")
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        # Verify the updated label is present
        assert "Receita Líquida (Bruta - Comissões - Gastos)" in html

        # Verify the calculated net revenue is correct: 1000 - 300 - 150 = 550
        assert "550.00" in html
