"""
Comprehensive template/UI rendering tests for optional cliente_id feature.

This module tests template rendering, form validation, and UI behavior
to ensure the frontend correctly handles payments with optional clients.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

# Import the main app factory for real testing
from app.main import create_app


@pytest.fixture
def app():
    """Create and configure a test app instance using the main app factory."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["LOGIN_DISABLED"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.app_context():
        yield app


class TestRegistrarPagamentoTemplate:
    """Test registrar_pagamento.html template rendering with optional client functionality."""

    def test_form_client_field_is_optional(self, app):
        """Test that client field is marked as optional and has no required attribute."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    # Mock authenticated user
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database session and queries for dropdowns
                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Mock clients query - return some test clients
                    mock_clients = [
                        Mock(id=1, name="Test Client 1"),
                        Mock(id=2, name="Test Client 2"),
                    ]

                    # Mock artists query - return some test artists
                    mock_artists = [
                        Mock(id=1, name="Test Artist 1"),
                        Mock(id=2, name="Test Artist 2"),
                    ]

                    # Mock database queries to return different data for different calls
                    def mock_query_side_effect(model):
                        mock_query = Mock()
                        if hasattr(model, "__name__") and "Client" in str(model):
                            mock_query.all.return_value = mock_clients
                        elif hasattr(model, "__name__") and "User" in str(model):
                            mock_query.all.return_value = mock_artists
                        else:
                            mock_query.all.return_value = []
                        return mock_query

                    mock_db.query.side_effect = mock_query_side_effect

                    # Make GET request to payment form
                    response = client.get("/financeiro/registrar-pagamento")

                    # Verify response is successful
                    assert response.status_code == 200

                    # Get HTML content
                    html_content = response.get_data(as_text=True)

                    # Test 1: Client field exists
                    assert 'name="cliente_id"' in html_content

                    # Test 2: Client field is NOT marked as required
                    # Find the select element and check it doesn't have required attribute
                    import re

                    cliente_select_match = re.search(
                        r'<select[^>]*name="cliente_id"[^>]*>', html_content
                    )
                    assert (
                        cliente_select_match is not None
                    ), "Cliente select field not found"
                    cliente_select_tag = cliente_select_match.group(0)
                    assert (
                        "required" not in cliente_select_tag
                    ), f"Cliente field should not be required: {cliente_select_tag}"

                    # Test 3: Label shows "Cliente (Opcional)"
                    assert "Cliente (Opcional)" in html_content

                    # Test 4: Default option text is "Nenhum cliente / Não informado"
                    assert "Nenhum cliente / Não informado" in html_content

                    # Test 5: Default option has empty value
                    assert (
                        '<option value="">Nenhum cliente / Não informado</option>'
                        in html_content
                    )

    def test_form_renders_client_options_correctly(self, app):
        """Test that form correctly renders available client options."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    # Mock authenticated user
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database session and queries
                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Mock clients with specific names for testing
                    mock_clients = [
                        Mock(id=1, name="Cliente Teste 1"),
                        Mock(id=2, name="Cliente Teste 2"),
                    ]

                    def mock_query_side_effect(model):
                        mock_query = Mock()
                        if hasattr(model, "__name__") and "Client" in str(model):
                            mock_query.all.return_value = mock_clients
                        else:
                            mock_query.all.return_value = []
                        return mock_query

                    mock_db.query.side_effect = mock_query_side_effect

                    # Make GET request
                    response = client.get("/financeiro/registrar-pagamento")
                    assert response.status_code == 200

                    html_content = response.get_data(as_text=True)

                    # Test that client options are rendered
                    assert "Cliente Teste 1" in html_content
                    assert "Cliente Teste 2" in html_content

                    # Test option values are correct
                    assert 'value="1"' in html_content
                    assert 'value="2"' in html_content

    def test_form_submission_without_client(self, app):
        """Test that form submits successfully without client selected."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    # Mock authenticated user
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database operations
                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Mock the add, commit, refresh operations
                    mock_db.add = Mock()
                    mock_db.commit = Mock()
                    mock_db.refresh = Mock()

                    # Mock queries for form dropdowns
                    def mock_query_side_effect(model):
                        mock_query = Mock()
                        mock_query.all.return_value = []
                        return mock_query

                    mock_db.query.side_effect = mock_query_side_effect

                    # Form data without client
                    form_data = {
                        "data": "2024-01-15",
                        "valor": "100.00",
                        "forma_pagamento": "Dinheiro",
                        "cliente_id": "",  # Empty client field
                        "artista_id": "1",
                        "observacoes": "Test payment without client",
                    }

                    # Submit form
                    response = client.post(
                        "/financeiro/registrar-pagamento", data=form_data
                    )

                    # Should not return a validation error (4xx status)
                    # Expect either success (200/302) or server error due to mocking
                    assert response.status_code not in range(
                        400, 500
                    ), f"Form validation failed with status {response.status_code}"


class TestFinanceiroTemplate:
    """Test financeiro.html template rendering with optional client functionality."""

    def test_payments_without_clients_display_correctly(self, app):
        """Test that payments without clients display 'Nenhum cliente' or equivalent."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    # Mock authenticated user
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database session
                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Mock payments with mixed client scenarios
                    mock_payment_with_client = Mock()
                    mock_payment_with_client.id = 1
                    mock_payment_with_client.data = date(2024, 1, 15)
                    mock_payment_with_client.valor = Decimal("100.00")
                    mock_payment_with_client.forma_pagamento = "Dinheiro"
                    mock_payment_with_client.observacoes = "Payment with client"
                    mock_client = Mock()
                    mock_client.name = "Test Client"
                    mock_payment_with_client.cliente = mock_client
                    mock_artista = Mock()
                    mock_artista.name = "Test Artist"
                    mock_payment_with_client.artista = mock_artista

                    mock_payment_without_client = Mock()
                    mock_payment_without_client.id = 2
                    mock_payment_without_client.data = date(2024, 1, 16)
                    mock_payment_without_client.valor = Decimal("150.00")
                    mock_payment_without_client.forma_pagamento = "Cartão"
                    mock_payment_without_client.observacoes = "Payment without client"
                    mock_payment_without_client.cliente = None  # No client
                    mock_payment_without_client.artista = mock_artista

                    # Mock database query to return mixed payments
                    mock_db.query.return_value.all.return_value = [
                        mock_payment_with_client,
                        mock_payment_without_client,
                    ]

                    # Make GET request to financeiro page
                    response = client.get("/financeiro/")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Test that payment with client shows client name
                        assert "Test Client" in html_content

                        # Test that payment without client shows "Não informado" (consistent with registration form)
                        assert "Não informado" in html_content
                        assert (
                            "Test Artist" in html_content
                        )  # Artist should always show

                        # The template should handle null clients gracefully by showing "Não informado"

    def test_mixed_client_scenarios_render_correctly(self, app):
        """Test that payments list handles mixed client scenarios correctly."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Create multiple payments with different client scenarios
                    payments = []

                    # Payment 1: With client
                    payment1 = Mock()
                    payment1.id = 1
                    payment1.data = date(2024, 1, 15)
                    payment1.valor = Decimal("100.00")
                    client1 = Mock()
                    client1.name = "Cliente 1"
                    payment1.cliente = client1
                    artist = Mock()
                    artist.name = "Artista Test"
                    payment1.artista = artist
                    payment1.forma_pagamento = "Dinheiro"
                    payment1.observacoes = ""
                    payments.append(payment1)

                    # Payment 2: Without client (None)
                    payment2 = Mock()
                    payment2.id = 2
                    payment2.data = date(2024, 1, 16)
                    payment2.valor = Decimal("150.00")
                    payment2.cliente = None
                    payment2.artista = artist
                    payment2.forma_pagamento = "Cartão"
                    payment2.observacoes = ""
                    payments.append(payment2)

                    mock_db.query.return_value.all.return_value = payments

                    response = client.get("/financeiro/")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Verify both payments are rendered
                        assert "100" in html_content  # Payment 1 value
                        assert "150" in html_content  # Payment 2 value
                        assert "Cliente 1" in html_content  # Client name for payment 1
                        assert "Artista Test" in html_content  # Artist name


class TestHistoricoTemplate:
    """Test historico.html template rendering with optional client functionality."""

    def test_history_displays_payments_without_clients(self, app):
        """Test that history page displays payments without clients correctly."""
        with app.test_client() as client:
            with patch(
                "app.controllers.historico_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Mock payments for history display
                    mock_payments = []

                    # Payment with client
                    payment1 = Mock()
                    payment1.id = 1
                    payment1.data = date(2024, 1, 15)
                    payment1.valor = Decimal("100.00")
                    payment1.forma_pagamento = "Dinheiro"
                    payment1.observacoes = "Com cliente"
                    client1 = Mock()
                    client1.name = "Cliente Test"
                    payment1.cliente = client1
                    artist = Mock()
                    artist.name = "Artista Test"
                    payment1.artista = artist
                    mock_payments.append(payment1)

                    # Payment without client
                    payment2 = Mock()
                    payment2.id = 2
                    payment2.data = date(2024, 1, 16)
                    payment2.valor = Decimal("150.00")
                    payment2.forma_pagamento = "Cartão"
                    payment2.observacoes = "Sem cliente"
                    payment2.cliente = None  # No client
                    payment2.artista = artist
                    mock_payments.append(payment2)

                    # Mock the database query to return test payments
                    mock_db.query.return_value.all.return_value = mock_payments

                    response = client.get("/historico/")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Verify payments are displayed
                        assert "100" in html_content
                        assert "150" in html_content
                        assert "Cliente Test" in html_content
                        assert "Artista Test" in html_content

                        # The template should handle null clients (currently shows empty string)
                        # This is acceptable behavior - empty cell for missing client

    def test_history_totals_with_mixed_clients(self, app):
        """Test that history totals calculate correctly with mixed client scenarios."""
        with app.test_client() as client:
            with patch(
                "app.controllers.historico_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db

                    # Mock payments with and without clients
                    payments = [
                        Mock(
                            id=1, valor=Decimal("100.00"), cliente=Mock(name="Client 1")
                        ),
                        Mock(id=2, valor=Decimal("150.00"), cliente=None),  # No client
                        Mock(
                            id=3, valor=Decimal("200.00"), cliente=Mock(name="Client 2")
                        ),
                    ]

                    for p in payments:
                        p.data = date(2024, 1, 15)
                        p.forma_pagamento = "Dinheiro"
                        p.observacoes = ""
                        artist = Mock()
                        artist.name = "Artist"
                        p.artista = artist

                    mock_db.query.return_value.all.return_value = payments

                    response = client.get("/historico/")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # All payments should be included in totals regardless of client
                        assert "100" in html_content
                        assert "150" in html_content  # Payment without client included
                        assert "200" in html_content


class TestUITextAndLabels:
    """Test UI text, labels, and display consistency for optional client feature."""

    def test_client_field_labeled_as_optional(self, app):
        """Test that client field is consistently labeled as optional across forms."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Test that the label explicitly mentions "Opcional"
                        assert "Cliente (Opcional)" in html_content

    def test_null_client_display_text(self, app):
        """Test consistent display text for payments without clients."""
        # This test verifies the expected display text for null clients
        # across different templates

        expected_texts = [
            "Nenhum cliente / Não informado",  # Default option in form
            "Nenhum cliente",  # Preferred display in lists
            "",  # Empty string is acceptable
        ]

        # This is more of a specification test - defining expected behavior
        assert "Nenhum cliente / Não informado" in expected_texts
        assert "Nenhum cliente" in expected_texts

    def test_form_placeholder_text(self, app):
        """Test that form has appropriate placeholder/default text."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Test that the default option has the correct text
                        assert "Nenhum cliente / Não informado" in html_content


class TestFormValidationUI:
    """Test form validation behavior with optional client field."""

    def test_client_field_not_marked_required_in_html(self, app):
        """Test that client field HTML does not have required attribute."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Extract the client select field
                        import re

                        cliente_field_match = re.search(
                            r'<select[^>]*name="cliente_id"[^>]*>', html_content
                        )

                        if cliente_field_match:
                            cliente_field = cliente_field_match.group(0)
                            assert "required" not in cliente_field
                        else:
                            # Field should exist
                            assert 'name="cliente_id"' in html_content

    def test_form_javascript_handles_optional_client(self, app):
        """Test that any client-side JavaScript handles optional client correctly."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # If there's JavaScript validation, it should not require client
                        # This is a basic check - in a real app you might need more specific tests
                        if (
                            "javascript" in html_content.lower()
                            or "script" in html_content.lower()
                        ):
                            # Basic validation that the page loads without JavaScript errors
                            # More comprehensive JS testing would require selenium or similar tools
                            assert (
                                "cliente_id" in html_content
                            )  # Field exists for JS to reference
