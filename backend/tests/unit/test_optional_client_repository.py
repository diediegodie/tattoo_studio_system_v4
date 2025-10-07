"""Tests for PagamentoRepository operations with optional client handling."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

pagamento_repo_module = pytest.importorskip("app.repositories.pagamento_repository")
PagamentoRepository = pagamento_repo_module.PagamentoRepository


def make_pagamento(**overrides: object) -> SimpleNamespace:
    base_data = {
        "id": 1,
        "data": date(2024, 1, 15),
        "valor": Decimal("100.00"),
        "forma_pagamento": "Dinheiro",
        "cliente_id": None,
        "artista_id": 1,
        "observacoes": "Test payment",
    }
    base_data.update(overrides)
    return SimpleNamespace(**base_data)


@pytest.fixture
def mock_db_session() -> MagicMock:
    return MagicMock()


@pytest.fixture
def repo(mock_db_session: MagicMock) -> PagamentoRepository:
    return PagamentoRepository(mock_db_session)


def test_create_pagamento_without_client(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    pagamento = make_pagamento(cliente_id=None)

    result = repo.create(pagamento)

    assert result is pagamento
    assert pagamento.cliente_id is None
    mock_db_session.add.assert_called_once_with(pagamento)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(pagamento)


def test_create_pagamento_with_client(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    pagamento = make_pagamento(cliente_id=5)

    result = repo.create(pagamento)

    assert result is pagamento
    assert pagamento.cliente_id == 5
    mock_db_session.add.assert_called_once_with(pagamento)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(pagamento)


def test_create_pagamento_handles_add_error(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    pagamento = make_pagamento()
    mock_db_session.add.side_effect = SQLAlchemyError("db error")

    result = repo.create(pagamento)

    assert result is None
    mock_db_session.rollback.assert_called_once()
    mock_db_session.commit.assert_not_called()
    mock_db_session.refresh.assert_not_called()


def test_create_pagamento_handles_commit_error(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    pagamento = make_pagamento()
    mock_db_session.commit.side_effect = SQLAlchemyError("commit error")

    result = repo.create(pagamento)

    assert result is None
    mock_db_session.add.assert_called_once_with(pagamento)
    mock_db_session.rollback.assert_called_once()
    mock_db_session.refresh.assert_not_called()


def test_get_by_id_returns_pagamento(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    expected = make_pagamento(id=5, cliente_id=None)
    query_mock = MagicMock()
    filter_mock = query_mock.filter.return_value
    filter_mock.first.return_value = expected
    mock_db_session.query.return_value = query_mock

    result = repo.get_by_id(5)

    assert result is expected
    mock_db_session.query.assert_called_once()
    query_mock.filter.assert_called_once()
    filter_mock.first.assert_called_once()


def test_get_by_id_returns_none_when_missing(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    query_mock = MagicMock()
    query_mock.filter.return_value.first.return_value = None
    mock_db_session.query.return_value = query_mock

    result = repo.get_by_id(404)

    assert result is None


def test_list_all_includes_payments_with_and_without_client(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    payments = [
        make_pagamento(id=1, cliente_id=None),
        make_pagamento(id=2, cliente_id=7),
    ]
    query_mock = MagicMock()
    order_mock = query_mock.order_by.return_value
    order_mock.all.return_value = payments
    mock_db_session.query.return_value = query_mock

    result = repo.list_all()

    assert result == payments
    mock_db_session.query.assert_called_once()
    query_mock.order_by.assert_called_once()
    order_mock.all.assert_called_once()
    assert any(p.cliente_id is None for p in result)
    assert any(p.cliente_id is not None for p in result)


def test_list_all_returns_empty_when_no_records(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    query_mock = MagicMock()
    order_mock = query_mock.order_by.return_value
    order_mock.all.return_value = []
    mock_db_session.query.return_value = query_mock

    result = repo.list_all()

    assert result == []
    mock_db_session.query.assert_called_once()
    query_mock.order_by.assert_called_once()
    order_mock.all.assert_called_once()


def test_update_pagamento_removes_client(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    existing = make_pagamento(id=10, cliente_id=3, valor=Decimal("200.00"))
    update_data = {"cliente_id": None, "valor": Decimal("150.00")}

    with patch.object(repo, "get_by_id", return_value=existing):
        result = repo.update(existing.id, update_data)

    assert result is existing
    assert existing.cliente_id is None
    assert existing.valor == Decimal("150.00")
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(existing)


def test_update_pagamento_adds_client(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    existing = make_pagamento(id=11, cliente_id=None, valor=Decimal("120.00"))
    update_data = {"cliente_id": 9, "valor": Decimal("175.00")}

    with patch.object(repo, "get_by_id", return_value=existing):
        result = repo.update(existing.id, update_data)

    assert result is existing
    assert existing.cliente_id == 9
    assert existing.valor == Decimal("175.00")
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(existing)


def test_update_returns_none_when_payment_missing(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    with patch.object(repo, "get_by_id", return_value=None):
        result = repo.update(999, {"cliente_id": None})

    assert result is None
    mock_db_session.commit.assert_not_called()
    mock_db_session.refresh.assert_not_called()


def test_update_handles_db_error(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    existing = make_pagamento(id=12, cliente_id=None)
    mock_db_session.commit.side_effect = SQLAlchemyError("update error")

    with patch.object(repo, "get_by_id", return_value=existing):
        result = repo.update(existing.id, {"cliente_id": 4})

    assert result is None
    mock_db_session.rollback.assert_called_once()
    mock_db_session.refresh.assert_not_called()


def test_delete_pagamento_without_client(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    existing = make_pagamento(id=13, cliente_id=None)
    comissao_query = MagicMock()
    sessao_query = MagicMock()
    comissao_query.filter.return_value.update.return_value = 1
    sessao_query.filter.return_value.update.return_value = 1
    mock_db_session.query.side_effect = [comissao_query, sessao_query]

    with patch.object(repo, "get_by_id", return_value=existing):
        result = repo.delete(existing.id)

    assert result is True
    mock_db_session.delete.assert_called_once_with(existing)
    mock_db_session.commit.assert_called_once()


def test_delete_returns_false_when_payment_missing(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    with patch.object(repo, "get_by_id", return_value=None):
        result = repo.delete(404)

    assert result is False
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()


def test_delete_handles_db_error(
    repo: PagamentoRepository, mock_db_session: MagicMock
) -> None:
    existing = make_pagamento(id=14, cliente_id=None)
    comissao_query = MagicMock()
    sessao_query = MagicMock()
    comissao_query.filter.return_value.update.return_value = 1
    sessao_query.filter.return_value.update.return_value = 1
    mock_db_session.query.side_effect = [comissao_query, sessao_query]
    mock_db_session.commit.side_effect = SQLAlchemyError("delete error")

    with patch.object(repo, "get_by_id", return_value=existing):
        result = repo.delete(existing.id)

    assert result is False
    mock_db_session.delete.assert_called_once_with(existing)
    mock_db_session.rollback.assert_called_once()
