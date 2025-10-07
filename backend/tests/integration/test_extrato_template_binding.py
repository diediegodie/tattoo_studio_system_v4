import json

import pytest

from app.db.base import Extrato


@pytest.mark.integration
@pytest.mark.controllers
def test_extrato_page_displays_snapshot_month(
    monkeypatch, db_session, authenticated_client
):
    """Ensure extrato page labels use the snapshot month instead of current date."""
    monkeypatch.setenv("DISABLE_EXTRATO_BACKGROUND", "true")

    extrato_record = Extrato(
        mes=9,
        ano=2025,
        pagamentos=json.dumps([]),
        sessoes=json.dumps([]),
        comissoes=json.dumps([]),
        gastos=json.dumps([]),
        totais=json.dumps({"receita_total": 0}),
    )
    db_session.add(extrato_record)
    db_session.commit()

    response = authenticated_client.get("/extrato/2025/09")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Setembro/2025" in html
    assert "Setembro / 2025" in html
    assert "Agosto/2025" not in html
