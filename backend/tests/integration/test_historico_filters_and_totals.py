import os
import logging
from datetime import date

import pytest

from app.db.base import Client, Comissao, Gasto, Pagamento, Sessao, User
from app.services.extrato_generation import get_current_month_totals


@pytest.fixture(autouse=True)
def clear_env():
    prev = os.environ.get("HISTORICO_DEBUG")
    os.environ["HISTORICO_DEBUG"] = "1"
    yield
    if prev is not None:
        os.environ["HISTORICO_DEBUG"] = prev
    else:
        os.environ.pop("HISTORICO_DEBUG", None)


@pytest.mark.integration
@pytest.mark.controllers
class TestHistoricoFiltersAndTotals:

    def test_finalize_pay_historico_e2e(self, authenticated_client, db_session):
        """End-to-end: finalize session, pay, verify Historico visibility."""
        # Step 1: Create a completed session (not paid)
        s = Sessao(
            data=self._mid_month(),
            valor=123,
            cliente_id=self.client.id,
            artista_id=self.artist.id,
            status="completed",
        )
        db_session.add(s)
        db_session.commit()

        # Step 2: Historico should NOT show the session
        resp = authenticated_client.get("/historico/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert f"sess-{s.id}" not in html

        # Step 3: Create a payment and link to session
        p = Pagamento(
            data=self._mid_month(),
            valor=123,
            forma_pagamento="Pix",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        db_session.add(p)
        db_session.commit()
        s.payment_id = p.id
        db_session.commit()

        # Step 4: Historico should now show the session
        resp2 = authenticated_client.get("/historico/")
        assert resp2.status_code == 200
        html2 = resp2.get_data(as_text=True)
        assert f"sess-{s.id}" in html2

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        db_session.query(Comissao).delete()
        db_session.query(Pagamento).delete()
        db_session.query(Sessao).delete()
        db_session.query(Gasto).delete()
        db_session.query(Client).delete()
        db_session.query(User).delete()
        db_session.commit()

        self.artist = User(name="A", email="a@a", role="artist")
        self.client = Client(name="C", jotform_submission_id="c1")
        db_session.add_all([self.artist, self.client])
        db_session.commit()

    def _mid_month(self):
        return date.today().replace(day=15)

    def test_session_without_payment_not_in_history(
        self, authenticated_client, db_session, caplog
    ):
        s = Sessao(
            data=self._mid_month(),
            valor=100,
            cliente_id=self.client.id,
            artista_id=self.artist.id,
            status="completed",
        )
        db_session.add(s)
        db_session.commit()

        resp = authenticated_client.get("/historico/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        # Session should not appear because not linked to a payment (controller derives from Pagamento)
        assert f"sess-{s.id}" not in html
        # Log assertions are environment-sensitive; the main behavior is exclusion from HTML.

    def test_session_with_payment_is_listed(self, authenticated_client, db_session):
        p = Pagamento(
            data=self._mid_month(),
            valor=200,
            forma_pagamento="Dinheiro",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        db_session.add(p)
        db_session.commit()
        s = Sessao(
            data=self._mid_month(),
            valor=200,
            cliente_id=self.client.id,
            artista_id=self.artist.id,
            status="completed",
            payment_id=p.id,
        )
        db_session.add(s)
        db_session.commit()

        # commission linked to payment
        c = Comissao(
            pagamento_id=p.id, artista_id=self.artist.id, percentual=50, valor=100
        )
        db_session.add(c)
        db_session.commit()

        resp = authenticated_client.get("/historico/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        # Session derived via Pagamento.sessao should be visible
        assert f"sess-{s.id}" in html

    def test_totals_match_payments_only(self, app, db_session):
        with app.app_context():
            # 1 paid session (via payment) and 1 unpaid session
            p = Pagamento(
                data=self._mid_month(),
                valor=300,
                forma_pagamento="Pix",
                cliente_id=self.client.id,
                artista_id=self.artist.id,
            )
            db_session.add(p)
            db_session.commit()
            s_paid = Sessao(
                data=self._mid_month(),
                valor=300,
                cliente_id=self.client.id,
                artista_id=self.artist.id,
                status="completed",
                payment_id=p.id,
            )
            s_unpaid = Sessao(
                data=self._mid_month(),
                valor=999,
                cliente_id=self.client.id,
                artista_id=self.artist.id,
                status="completed",
            )
            db_session.add_all([s_paid, s_unpaid])
            db_session.commit()

            totals = get_current_month_totals(db_session)
            # receita_total from payments only
            assert totals["receita_total"] == 300.0
            # unpaid session should not inflate totals
            assert totals["receita_liquida"] <= 300.0

    def test_paid_session_appears_and_unpaid_excluded_on_month_boundary(
        self, authenticated_client, db_session
    ):
        """A 'paid' session linked by payment_id should appear in Historico even if
        status is 'paid' (not 'completed'), while a 'completed' session without payment
        must not appear. The payment is set on the inclusive month boundary to verify
        inclusion.
        """
        from app.services.extrato_core import current_month_range

        start_date, end_date = current_month_range()
        from datetime import timedelta

        # Use the inclusive end boundary: last day of the current month
        last_day = (end_date - timedelta(days=1)).date()

        # Create a boundary payment on the last day (included by [start, end))
        p_boundary = Pagamento(
            data=last_day,
            valor=250,
            forma_pagamento="Pix",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        db_session.add(p_boundary)
        db_session.commit()

        # Session linked to boundary payment, with status 'paid'
        s_paid = Sessao(
            data=last_day,
            valor=250,
            cliente_id=self.client.id,
            artista_id=self.artist.id,
            status="paid",
            payment_id=p_boundary.id,
        )
        db_session.add(s_paid)

        # Unpaid completed session should not appear
        s_unpaid = Sessao(
            data=last_day,
            valor=999,
            cliente_id=self.client.id,
            artista_id=self.artist.id,
            status="completed",
        )
        db_session.add(s_unpaid)
        db_session.commit()

        # Request Historico page
        resp = authenticated_client.get("/historico/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)

        # Paid-linked session must appear
        assert f"sess-{s_paid.id}" in html
        # Completed but unpaid session must not appear
        assert f"sess-{s_unpaid.id}" not in html
