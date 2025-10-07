import json
from datetime import date
from decimal import Decimal

import pytest

from app.db.base import (
    Client,
    Comissao,
    Extrato,
    ExtratoRunLog,
    Gasto,
    Pagamento,
    Sessao,
    User,
)
from app.db.session import SessionLocal
from app.services.extrato_generation import check_and_generate_extrato

TEST_MONTH = 8
TEST_YEAR = 2025


def _load_json_field(value, empty_default):
    """Return parsed JSON content or the provided default."""
    if value is None:
        return empty_default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return empty_default


def _seed_monthly_historico(db_session, mes=TEST_MONTH, ano=TEST_YEAR):
    """Insert sample historico data for the given month/year."""
    primary_client = Client(
        name="Cliente Regular",
        jotform_submission_id=f"jotform-{ano}-{mes:02d}",
    )
    walk_in_client = Client(
        name="Cliente Walk-in",
        jotform_submission_id=f"walkin-{ano}-{mes:02d}",
    )
    artist_with_commission = User()
    artist_with_commission.name = "Artista Com Comissão"  # type: ignore[assignment]
    artist_with_commission.email = f"artist.com+{ano}{mes:02d}@example.com"  # type: ignore[assignment]
    artist_with_commission.google_id = f"artist-{ano}-{mes:02d}"  # type: ignore[assignment]

    artist_zero_commission = User()
    artist_zero_commission.name = "Artista Zero Comissão"  # type: ignore[assignment]
    artist_zero_commission.email = f"artist.zero+{ano}{mes:02d}@example.com"  # type: ignore[assignment]
    artist_zero_commission.google_id = f"artist-zero-{ano}-{mes:02d}"  # type: ignore[assignment]

    db_session.add_all(
        [primary_client, walk_in_client, artist_with_commission, artist_zero_commission]
    )
    db_session.flush()

    sessao_comissionada = Sessao(
        data=date(ano, mes, 5),
        valor=Decimal("200.00"),
        observacoes="Sessão com comissão",
        cliente_id=primary_client.id,
        artista_id=artist_with_commission.id,
        status="completed",
    )
    sessao_zero = Sessao(
        data=date(ano, mes, 12),
        valor=Decimal("150.00"),
        observacoes="Sessão sem comissão",
        cliente_id=walk_in_client.id,
        artista_id=artist_zero_commission.id,
        status="completed",
    )
    db_session.add_all([sessao_comissionada, sessao_zero])
    db_session.flush()

    pagamento_comissionado = Pagamento(
        data=date(ano, mes, 5),
        valor=Decimal("200.00"),
        forma_pagamento="PIX",
        observacoes="Pagamento com comissão",
        cliente_id=primary_client.id,
        artista_id=artist_with_commission.id,
        sessao_id=sessao_comissionada.id,
    )
    pagamento_zero = Pagamento(
        data=date(ano, mes, 12),
        valor=Decimal("150.00"),
        forma_pagamento="Dinheiro",
        observacoes="Pagamento sem comissão",
        cliente_id=None,
        artista_id=artist_zero_commission.id,
        sessao_id=sessao_zero.id,
    )
    db_session.add_all([pagamento_comissionado, pagamento_zero])
    db_session.flush()

    comissao = Comissao(
        pagamento_id=pagamento_comissionado.id,
        artista_id=artist_with_commission.id,
        percentual=Decimal("30.0"),
        valor=Decimal("60.00"),
        observacoes="Comissão padrão",
    )
    gasto = Gasto(
        data=date(ano, mes, 20),
        valor=Decimal("50.00"),
        descricao="Compra de materiais",
        forma_pagamento="Cartão",
        created_by=artist_with_commission.id,
    )

    db_session.add_all([comissao, gasto])
    db_session.commit()

    return {
        "receita_total": Decimal("350.00"),
        "comissoes_total": Decimal("60.00"),
        "despesas_total": Decimal("50.00"),
        "artists_with_commission": {"Artista Com Comissão"},
        "artists_without_commission": {"Artista Zero Comissão"},
    }


@pytest.mark.integration
def test_check_and_generate_extrato_snapshots_and_cleans_historico(db_session):
    expected = _seed_monthly_historico(db_session)

    check_and_generate_extrato(mes=TEST_MONTH, ano=TEST_YEAR, force=True)

    verification_session = SessionLocal()
    try:
        extrato = (
            verification_session.query(Extrato)
            .filter(Extrato.mes == TEST_MONTH, Extrato.ano == TEST_YEAR)
            .one()
        )

        pagamentos = _load_json_field(extrato.pagamentos, [])
        sessoes = _load_json_field(extrato.sessoes, [])
        comissoes = _load_json_field(extrato.comissoes, [])
        gastos = _load_json_field(extrato.gastos, [])
        totais = _load_json_field(extrato.totais, {})

        assert len(pagamentos) == 2
        assert len(sessoes) == 2
        assert len(comissoes) == 1
        assert len(gastos) == 1

        receita_total = float(totais.get("receita_total", 0))
        comissoes_total = float(totais.get("comissoes_total", 0))
        despesas_total = float(totais.get("despesas_total", 0))

        assert receita_total == pytest.approx(float(expected["receita_total"]))
        assert comissoes_total == pytest.approx(float(expected["comissoes_total"]))
        assert despesas_total == pytest.approx(float(expected["despesas_total"]))

        por_artista = totais.get("por_artista", [])
        artist_names = {item["artista"] for item in por_artista}
        assert expected["artists_with_commission"] <= artist_names
        assert expected["artists_without_commission"].isdisjoint(artist_names)

        assert verification_session.query(Pagamento).count() == 0
        assert verification_session.query(Sessao).count() == 0
        assert verification_session.query(Comissao).count() == 0
        assert verification_session.query(Gasto).count() == 0

        run_log = (
            verification_session.query(ExtratoRunLog)
            .filter(
                ExtratoRunLog.mes == TEST_MONTH,
                ExtratoRunLog.ano == TEST_YEAR,
                ExtratoRunLog.status == "success",
            )
            .one()
        )
        assert run_log is not None
    finally:
        verification_session.close()


@pytest.mark.integration
def test_check_and_generate_extrato_ignores_future_month_data(db_session):
    _seed_monthly_historico(db_session, mes=TEST_MONTH, ano=TEST_YEAR)

    future_month = (TEST_MONTH % 12) + 1
    future_year = TEST_YEAR + (1 if TEST_MONTH == 12 else 0)
    _seed_monthly_historico(db_session, mes=future_month, ano=future_year)

    check_and_generate_extrato(mes=TEST_MONTH, ano=TEST_YEAR, force=True)

    def month_range(year: int, month: int):
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        return start, end

    target_start, target_end = month_range(TEST_YEAR, TEST_MONTH)
    future_start, future_end = month_range(future_year, future_month)

    verification_session = SessionLocal()
    try:
        extrato = (
            verification_session.query(Extrato)
            .filter(Extrato.mes == TEST_MONTH, Extrato.ano == TEST_YEAR)
            .one()
        )

        pagamentos = _load_json_field(extrato.pagamentos, [])
        sessoes = _load_json_field(extrato.sessoes, [])
        comissoes = _load_json_field(extrato.comissoes, [])
        gastos = _load_json_field(extrato.gastos, [])

        assert len(pagamentos) > 0
        for pagamento in pagamentos:
            assert pagamento["data"] is not None
            pagamento_date = date.fromisoformat(pagamento["data"])
            assert target_start <= pagamento_date < target_end

        assert len(sessoes) > 0
        for sessao in sessoes:
            assert sessao["data"] is not None
            sessao_date = date.fromisoformat(sessao["data"])
            assert target_start <= sessao_date < target_end

        for comissao in comissoes:
            pagamento_data = comissao.get("pagamento_data")
            created_at = comissao.get("created_at")
            if pagamento_data:
                pagamento_date = date.fromisoformat(pagamento_data)
                assert target_start <= pagamento_date < target_end
            elif created_at:
                created_date = date.fromisoformat(created_at.split("T")[0])
                assert target_start <= created_date < target_end

        for gasto in gastos:
            assert gasto["data"] is not None
            gasto_date = date.fromisoformat(gasto["data"])
            assert target_start <= gasto_date < target_end

        assert (
            verification_session.query(Pagamento)
            .filter(Pagamento.data >= target_start, Pagamento.data < target_end)
            .count()
            == 0
        )
        assert (
            verification_session.query(Sessao)
            .filter(Sessao.data >= target_start, Sessao.data < target_end)
            .count()
            == 0
        )
        assert (
            verification_session.query(Comissao)
            .join(Pagamento, Comissao.pagamento)
            .filter(Pagamento.data >= target_start, Pagamento.data < target_end)
            .count()
            == 0
        )
        assert (
            verification_session.query(Gasto)
            .filter(Gasto.data >= target_start, Gasto.data < target_end)
            .count()
            == 0
        )

        assert (
            verification_session.query(Pagamento)
            .filter(Pagamento.data >= future_start, Pagamento.data < future_end)
            .count()
            > 0
        )
        assert (
            verification_session.query(Sessao)
            .filter(Sessao.data >= future_start, Sessao.data < future_end)
            .count()
            > 0
        )
        assert (
            verification_session.query(Comissao)
            .join(Pagamento, Comissao.pagamento)
            .filter(Pagamento.data >= future_start, Pagamento.data < future_end)
            .count()
            > 0
        )
        assert (
            verification_session.query(Gasto)
            .filter(Gasto.data >= future_start, Gasto.data < future_end)
            .count()
            > 0
        )
    finally:
        verification_session.close()


@pytest.mark.integration
def test_extrato_api_returns_data_and_handles_missing(
    db_session, authenticated_client, monkeypatch
):
    monkeypatch.setenv("DISABLE_EXTRATO_BACKGROUND", "true")
    _seed_monthly_historico(db_session)

    check_and_generate_extrato(mes=TEST_MONTH, ano=TEST_YEAR, force=True)

    response = authenticated_client.get(
        f"/extrato/api?mes={TEST_MONTH:02d}&ano={TEST_YEAR}"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["mes"] == TEST_MONTH
    assert payload["data"]["ano"] == TEST_YEAR
    assert len(payload["data"]["pagamentos"]) == 2
    assert len(payload["data"]["comissoes"]) == 1

    missing_response = authenticated_client.get(
        f"/extrato/api?mes={TEST_MONTH:02d}&ano={TEST_YEAR + 1}"
    )
    assert missing_response.status_code == 404
    missing_payload = missing_response.get_json()
    assert missing_payload["success"] is False
    assert "Extrato não encontrado" in missing_payload["message"]


@pytest.mark.integration
def test_extrato_page_renders_bootstrap_and_warning(
    db_session, authenticated_client, monkeypatch
):
    monkeypatch.setenv("DISABLE_EXTRATO_BACKGROUND", "true")
    _seed_monthly_historico(db_session)

    check_and_generate_extrato(mes=TEST_MONTH, ano=TEST_YEAR, force=True)

    response_with_data = authenticated_client.get(f"/extrato/{TEST_YEAR}/{TEST_MONTH}")
    assert response_with_data.status_code == 200
    html_with_data = response_with_data.get_data(as_text=True)
    assert "data-bootstrap=" in html_with_data
    assert f'value="{TEST_MONTH:02d}" selected' in html_with_data
    assert f'value="{TEST_YEAR}" selected' in html_with_data
    assert "carregado automaticamente" in html_with_data

    response_without_data = authenticated_client.get(
        f"/extrato/{TEST_YEAR}/{(TEST_MONTH % 12) + 1}"
    )
    assert response_without_data.status_code == 200
    html_without_data = response_without_data.get_data(as_text=True)
    assert "Nenhum extrato encontrado" in html_without_data
    assert "data-bootstrap=" not in html_without_data
