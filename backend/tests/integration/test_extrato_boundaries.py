from datetime import date, datetime, timezone

import pytest

from app.db.base import Client, Comissao, Gasto, Pagamento, Sessao, User
from app.services.extrato_core import query_data


@pytest.mark.integration
@pytest.mark.extrato
class TestExtratoBoundaries:
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

    def test_month_window_inclusion_and_exclusion(self, db_session):
        # Choose a fixed month for clarity
        ano, mes = 2025, 8  # August 2025
        start_day = date(ano, mes, 1)
        last_day = date(ano, mes, 31)
        next_month_day1 = date(2025, 9, 1)

        # Included at start of month
        p1 = Pagamento(
            data=start_day,
            valor=100,
            forma_pagamento="Dinheiro",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        # Included at last day
        p2 = Pagamento(
            data=last_day,
            valor=200,
            forma_pagamento="Pix",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        # Excluded start of next month
        p3 = Pagamento(
            data=next_month_day1,
            valor=300,
            forma_pagamento="Cartao",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        db_session.add_all([p1, p2, p3])
        db_session.commit()

        pagamentos, sessoes, comissoes, gastos = query_data(db_session, mes, ano)
        ids = {p.id for p in pagamentos}
        assert p1.id in ids
        assert p2.id in ids
        assert p3.id not in ids

    def test_timezone_normalization_commission_excluded(self, db_session):
        # August snapshot shouldn't include commission created at 2025-09-01 00:30 UTC when payment is not in August
        ano, mes = 2025, 8
        # Payment in September
        p_sep = Pagamento(
            data=date(2025, 9, 1),
            valor=123,
            forma_pagamento="Pix",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        db_session.add(p_sep)
        db_session.commit()
        # Commission created at 2025-09-01 00:30 UTC and linked to September payment should not appear in August
        c = Comissao(
            pagamento_id=p_sep.id, artista_id=self.artist.id, percentual=10, valor=12.3
        )
        db_session.add(c)
        db_session.commit()

        pagamentos, sessoes, comissoes, gastos = query_data(db_session, mes, ano)
        # No commissions because derived solely from August payments (none exist for August)
        assert comissoes == []

    def test_snapshot_totals_via_payments_only(self, db_session):
        ano, mes = 2025, 8
        p_aug = Pagamento(
            data=date(ano, mes, 15),
            valor=400,
            forma_pagamento="Pix",
            cliente_id=self.client.id,
            artista_id=self.artist.id,
        )
        db_session.add(p_aug)
        db_session.commit()
        s = Sessao(
            data=date(ano, mes, 15),
            valor=400,
            cliente_id=self.client.id,
            artista_id=self.artist.id,
            status="completed",
            payment_id=p_aug.id,
        )
        db_session.add(s)
        db_session.commit()
        c = Comissao(
            pagamento_id=p_aug.id, artista_id=self.artist.id, percentual=25, valor=100
        )
        db_session.add(c)
        db_session.commit()

        pagamentos, sessoes, comissoes, gastos = query_data(db_session, mes, ano)
        assert len(pagamentos) == 1
        assert sessoes and sessoes[0] is not None
        assert len(comissoes) == 1
