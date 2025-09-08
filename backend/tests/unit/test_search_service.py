"""
Unit tests for SearchService.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.search_service import SearchService
from app.db.base import Pagamento, Sessao, Comissao, Extrato, Client, User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def search_service(mock_db):
    """Initialize SearchService with mocked database."""
    return SearchService(mock_db)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.search
class TestSearchService:
    """Test SearchService functionality."""

    def test_normalize_query_basic(self, search_service):
        """Test basic query normalization."""
        assert search_service._normalize_query("MARIA SANTOS") == "maria santos"
        assert search_service._normalize_query("  João Silva  ") == "joao silva"
        assert search_service._normalize_query("") == ""

    def test_normalize_query_accents(self, search_service):
        """Test accent normalization."""
        assert search_service._normalize_query("María José") == "maria jose"
        assert search_service._normalize_query("São Paulo") == "sao paulo"

    def test_search_empty_query(self, search_service, mock_db):
        """Test search with empty query returns empty results."""
        mock_db.query.return_value.filter.return_value.all.return_value = []

        results = search_service.search("")

        assert results == {
            "pagamentos": [],
            "sessoes": [],
            "comissoes": [],
            "extratos": [],
        }

    def test_search_pagamentos(self, search_service, mock_db):
        """Test searching pagamentos."""
        # Mock all queries to return empty results
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        results = search_service.search("maria")

        assert isinstance(results, dict)
        assert "pagamentos" in results
        assert "sessoes" in results
        assert "comissoes" in results
        assert "extratos" in results
        assert all(isinstance(v, list) for v in results.values())

    def test_json_contains_query(self, search_service):
        """Test JSON query matching."""
        json_obj = {
            "cliente_name": "Maria Santos",
            "artista_name": "João Silva",
            "observacoes": "Test session",
        }

        assert search_service._json_contains_query(json_obj, "maria") == True
        assert (
            search_service._json_contains_query(json_obj, "joão") == True
        )  # Keep accent for exact match
        assert search_service._json_contains_query(json_obj, "notfound") == False
        assert search_service._json_contains_query(None, "test") == False
        assert search_service._json_contains_query([], "test") == False
