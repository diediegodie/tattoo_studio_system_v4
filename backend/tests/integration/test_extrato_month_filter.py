"""
Regression tests ensuring extrato generation filters future-month data and
that the extrato UI stays aligned with the historico UI.

These tests seed September and October historico data, run
check_and_generate_extrato for September 2025, and verify that only
September rows are migrated into the extrato snapshot while October
records remain in the live historico tables. They also ensure the rendered
section headings stay consistent between historico and extrato pages.
"""

import html
import json
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.base import (
    Client,
    Comissao,
    Extrato,
    Gasto,
    Pagamento,
    Sessao,
    User,
)
from app.services.extrato_core import calculate_totals, serialize_data
from app.services.extrato_generation import check_and_generate_extrato

TARGET_YEAR = 2025
TARGET_MONTH = 9
SEPTEMBER_DAY = date(TARGET_YEAR, TARGET_MONTH, 15)
OCTOBER_DAY = date(TARGET_YEAR, 10, 10)

EXPECTED_SECTION_TITLES = [
    "Pagamentos",
    "Comissões",
    "Sessões realizadas",
    "Comissões por Artista",
    "Receita por Forma de Pagamento",
    "Gastos do Mês",
    "Totais do Mês Atual",
]


def _extract_section_headings(html_text):
    """Return ordered section headings that match historico/extrato sections."""

    pattern = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.IGNORECASE | re.DOTALL)
    headings = []

    for match in pattern.findall(html_text):
        # Strip nested tags then normalise whitespace/HTML entities
        cleaned = re.sub(r"<[^>]+>", "", match)
        cleaned = html.unescape(cleaned).strip()
        if cleaned in EXPECTED_SECTION_TITLES:
            headings.append(cleaned)

    return headings


def _load_json_field(value, default):
    """Parse JSON fields regardless of backend (text vs native JSON)."""
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return default


@pytest.fixture
def historico_seed(db_session):
    """Insert September and October historico data for regression tests."""

    def unique_email(prefix: str) -> str:
        return f"{prefix}-{uuid4()}@example.com"

    owner = User(name="Owner QA", email=unique_email("owner"), role="admin")
    artist_sep = User(
        name="Artista Setembro QA", email=unique_email("artist-sep"), role="artist"
    )
    artist_oct = User(
        name="Artista Outubro QA", email=unique_email("artist-oct"), role="artist"
    )
    db_session.add_all([owner, artist_sep, artist_oct])
    db_session.commit()

    client_sep = Client(
        name="Cliente Setembro QA",
        jotform_submission_id=f"jotform-sep-{uuid4()}",
    )
    client_oct = Client(
        name="Cliente Outubro QA",
        jotform_submission_id=f"jotform-oct-{uuid4()}",
    )
    db_session.add_all([client_sep, client_oct])
    db_session.commit()

    sessao_sep = Sessao(
        data=SEPTEMBER_DAY,
        valor=Decimal("300.00"),
        observacoes="Sessão concluída em setembro",
        cliente_id=client_sep.id,
        artista_id=artist_sep.id,
        status="completed",
    )
    sessao_oct = Sessao(
        data=OCTOBER_DAY,
        valor=Decimal("200.00"),
        observacoes="Sessão prevista em outubro",
        cliente_id=client_oct.id,
        artista_id=artist_oct.id,
        status="completed",
    )
    db_session.add_all([sessao_sep, sessao_oct])
    db_session.commit()

    pagamento_sep = Pagamento(
        data=SEPTEMBER_DAY,
        valor=Decimal("300.00"),
        forma_pagamento="PIX",
        observacoes="Pagamento setembro",
        cliente_id=client_sep.id,
        artista_id=artist_sep.id,
        sessao_id=sessao_sep.id,
    )
    pagamento_oct = Pagamento(
        data=OCTOBER_DAY,
        valor=Decimal("200.00"),
        forma_pagamento="Cartão",
        observacoes="Pagamento outubro",
        cliente_id=client_oct.id,
        artista_id=artist_oct.id,
        sessao_id=sessao_oct.id,
    )
    db_session.add_all([pagamento_sep, pagamento_oct])
    db_session.commit()

    comissao_sep = Comissao(
        pagamento_id=pagamento_sep.id,
        artista_id=artist_sep.id,
        percentual=Decimal("30.00"),
        valor=Decimal("90.00"),
        observacoes="Comissão setembro",
    )
    comissao_oct = Comissao(
        pagamento_id=pagamento_oct.id,
        artista_id=artist_oct.id,
        percentual=Decimal("25.00"),
        valor=Decimal("50.00"),
        observacoes="Comissão outubro",
    )
    db_session.add_all([comissao_sep, comissao_oct])
    db_session.commit()

    gasto_sep = Gasto(
        data=date(TARGET_YEAR, TARGET_MONTH, 20),
        valor=Decimal("45.00"),
        descricao="Gasto operacional setembro",
        forma_pagamento="PIX",
        created_by=owner.id,
    )
    gasto_oct = Gasto(
        data=date(TARGET_YEAR, 10, 12),
        valor=Decimal("60.00"),
        descricao="Gasto operacional outubro",
        forma_pagamento="PIX",
        created_by=owner.id,
    )
    db_session.add_all([gasto_sep, gasto_oct])
    db_session.commit()

    db_session.expire_all()

    return {
        "owner": owner,
        "artists": {"sep": artist_sep, "oct": artist_oct},
        "clients": {"sep": client_sep, "oct": client_oct},
        "sessoes": {"sep": sessao_sep, "oct": sessao_oct},
        "pagamentos": {"sep": pagamento_sep, "oct": pagamento_oct},
        "comissoes": {"sep": comissao_sep, "oct": comissao_oct},
        "gastos": {"sep": gasto_sep, "oct": gasto_oct},
    }


def test_extrato_generation_filters_future_months(db_session, historico_seed):
    """The September extrato snapshot should only include September entries."""

    check_and_generate_extrato(mes=TARGET_MONTH, ano=TARGET_YEAR, force=True)
    db_session.expire_all()

    extrato_record = (
        db_session.query(Extrato)
        .filter(Extrato.mes == TARGET_MONTH, Extrato.ano == TARGET_YEAR)
        .one()
    )

    pagamentos = _load_json_field(extrato_record.pagamentos, [])
    sessoes = _load_json_field(extrato_record.sessoes, [])
    comissoes = _load_json_field(extrato_record.comissoes, [])
    gastos = _load_json_field(extrato_record.gastos, [])
    totais = _load_json_field(extrato_record.totais, {})

    assert len(pagamentos) == 1
    assert pagamentos[0]["data"] == SEPTEMBER_DAY.isoformat()
    assert pagamentos[0]["valor"] == pytest.approx(300.0)
    assert all("2025-10" not in json.dumps(item) for item in pagamentos)

    assert len(sessoes) == 1
    assert sessoes[0]["data"] == SEPTEMBER_DAY.isoformat()
    assert all("2025-10" not in json.dumps(item) for item in sessoes)

    assert len(comissoes) == 1
    assert comissoes[0]["valor"] == pytest.approx(90.0)

    assert len(gastos) == 1
    assert gastos[0]["valor"] == pytest.approx(45.0)

    assert totais["receita_total"] == pytest.approx(300.0)
    assert totais["comissoes_total"] == pytest.approx(90.0)
    assert totais["despesas_total"] == pytest.approx(45.0)
    assert totais["receita_liquida"] == pytest.approx(165.0)

    por_artista = totais.get("por_artista", [])
    assert len(por_artista) == 1
    assert por_artista[0]["artista"] == "Artista Setembro QA"
    assert por_artista[0]["comissao"] == pytest.approx(90.0)


def test_extrato_generation_retains_future_records(db_session, historico_seed):
    """Historico records for October should remain after September snapshot."""

    check_and_generate_extrato(mes=TARGET_MONTH, ano=TARGET_YEAR, force=True)
    db_session.expire_all()

    remaining_pagamentos = db_session.query(Pagamento).all()
    remaining_sessoes = db_session.query(Sessao).all()
    remaining_comissoes = db_session.query(Comissao).all()
    remaining_gastos = db_session.query(Gasto).all()

    assert len(remaining_pagamentos) == 1
    assert remaining_pagamentos[0].data == OCTOBER_DAY

    assert len(remaining_sessoes) == 1
    assert remaining_sessoes[0].data == OCTOBER_DAY

    assert len(remaining_comissoes) == 1
    assert remaining_comissoes[0].valor == Decimal("50.00")

    assert len(remaining_gastos) == 1
    assert remaining_gastos[0].data.month == 10
    assert remaining_gastos[0].valor == Decimal("60.00")


@pytest.mark.integration
@pytest.mark.controllers
def test_extrato_and_historico_share_section_headings(
    monkeypatch, db_session, authenticated_client, historico_seed
):
    """Ensure extrato and historico pages show identical section headings."""

    # Prevent background automation from mutating the snapshot during the test
    monkeypatch.setattr(
        "app.services.extrato_automation.run_extrato_in_background",
        lambda: None,
    )

    def fake_current_month_range():
        start = datetime(TARGET_YEAR, TARGET_MONTH, 1)
        if TARGET_MONTH == 12:
            end = datetime(TARGET_YEAR + 1, 1, 1)
        else:
            end = datetime(TARGET_YEAR, TARGET_MONTH + 1, 1)
        return start, end

    monkeypatch.setattr(
        "app.services.extrato_core.current_month_range",
        fake_current_month_range,
    )

    # Manually insert an extrato snapshot for the target month while keeping
    # historico tables populated.
    from app.db.base import Extrato

    pagamentos = list(historico_seed["pagamentos"].values())
    sessoes = list(historico_seed["sessoes"].values())
    comissoes = list(historico_seed["comissoes"].values())
    gastos = list(historico_seed["gastos"].values())

    pagamentos_data, sessoes_data, comissoes_data, gastos_data = serialize_data(
        pagamentos, sessoes, comissoes, gastos
    )
    totais = calculate_totals(
        pagamentos_data, sessoes_data, comissoes_data, gastos_data
    )

    extrato_record = Extrato(
        mes=TARGET_MONTH,
        ano=TARGET_YEAR,
        pagamentos=json.dumps(pagamentos_data),
        sessoes=json.dumps(sessoes_data),
        comissoes=json.dumps(comissoes_data),
        gastos=json.dumps(gastos_data),
        totais=json.dumps(totais),
    )
    db_session.add(extrato_record)
    db_session.commit()
    db_session.expire_all()

    extrato_response = authenticated_client.get(
        f"/extrato/{TARGET_YEAR}/{TARGET_MONTH:02d}"
    )
    assert extrato_response.status_code == 200
    extrato_headings = _extract_section_headings(
        extrato_response.get_data(as_text=True)
    )

    historico_response = authenticated_client.get("/historico/")
    assert historico_response.status_code == 200
    historico_headings = _extract_section_headings(
        historico_response.get_data(as_text=True)
    )

    assert extrato_headings == historico_headings == EXPECTED_SECTION_TITLES
