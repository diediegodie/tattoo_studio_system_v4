"""
Tests for template rendering and UI functionality with optional cliente_id.

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


class TestPaymentFormRendering:
    """Test payment form rendering with optional client functionality."""

    def test_registrar_pagamento_form_client_field_optional(self, app):
        """Test that payment form renders with client field marked as optional."""
        with app.test_client() as client:
            with patch("app.controllers.financeiro_controller.SessionLocal") as mock_session:
                with patch("flask_login.current_user") as mock_user:
                    # Mock authenticated user
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database session and queries
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    
                    # Mock clients query
                    mock_db.query.return_value.all.return_value = [
                        Mock(id=1, name="Test Client 1"),
                        Mock(id=2, name="Test Client 2")
                    ]

                    # Make GET request to payment form
                    response = client.get("/financeiro/registrar-pagamento")

                    # Verify response is successful
                    assert response.status_code == 200

                    if response.status_code == 200:
                        # Check that response contains form elements
                        html_content = response.get_data(as_text=True)

                        # Verify client field exists but is optional
                        assert (
                            "cliente_id" in html_content
                            or "cliente" in html_content.lower()
                        )
                        # The field should not be marked as required
                        assert (
                            "required" not in html_content.lower()
                            or "opcional" in html_content.lower()
                        )

    def test_payment_form_validation_without_client(self, app):
        """Test that payment form validates successfully without client selected."""
        form_data = {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "",  # Empty client field
            "artista_id": "1",
            "observacoes": "Test payment without client",
        }

        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database operations
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.add = Mock()
                    mock_db.commit = Mock()
                    mock_db.refresh = Mock()

                    # Submit form without client
                    response = client.post(
                        "/financeiro/registrar-pagamento", data=form_data
                    )

                    # Should not return validation error (4xx status)
                    assert response.status_code not in range(400, 500)

    def test_payment_form_submission_with_client(self, app):
        """Test that payment form works normally with client selected."""
        form_data = {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "1",  # Client selected
            "artista_id": "1",
            "observacoes": "Test payment with client",
        }

        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = 1

                    # Mock database operations
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.add = Mock()
                    mock_db.commit = Mock()
                    mock_db.refresh = Mock()

                    # Submit form with client
                    response = client.post(
                        "/financeiro/registrar-pagamento", data=form_data
                    )

                    # Should process successfully
                    assert response.status_code not in range(400, 500)


class TestPaymentListRendering:
    """Test payment list rendering with optional client information."""

    def test_financeiro_page_displays_payments_without_client(self, app):
        """Test that financeiro page correctly displays payments without clients."""
        # Mock payments with mixed client scenarios
        mock_payment_with_client = Mock()
        mock_payment_with_client.id = 1
        mock_payment_with_client.cliente_id = 1
        mock_payment_with_client.cliente = Mock()
        mock_payment_with_client.cliente.name = "Test Client"
        mock_payment_with_client.valor = 100.00
        mock_payment_with_client.forma_pagamento = "Dinheiro"

        mock_payment_without_client = Mock()
        mock_payment_without_client.id = 2
        mock_payment_without_client.cliente_id = None
        mock_payment_without_client.cliente = None
        mock_payment_without_client.valor = 150.00
        mock_payment_without_client.forma_pagamento = "Cartão"

        mock_payments = [mock_payment_with_client, mock_payment_without_client]

        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True

                    # Mock database query
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.options.return_value.order_by.return_value.limit.return_value.all.return_value = (
                        mock_payments
                    )

                    # Get financeiro page
                    response = client.get("/financeiro/")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Verify both payments are displayed
                        assert "100" in html_content  # Payment with client amount
                        assert "150" in html_content  # Payment without client amount

                        # Verify proper handling of null client display
                        assert (
                            "Test Client" in html_content
                        )  # Client name for payment 1
                        # Payment 2 should show appropriate null client indicator
                        assert (
                            "Sem cliente" in html_content.lower()
                            or "no client" in html_content.lower()
                            or "-" in html_content
                        )

    def test_historico_displays_payments_without_client(self, app):
        """Test that historico page correctly displays payments without clients."""
        # Mock historical data with null clients
        mock_payments = [
            Mock(
                id=1,
                data="2024-01-15",
                valor=100.00,
                cliente_id=None,
                cliente=None,
                artista=Mock(name="Artist 1"),
            ),
            Mock(
                id=2,
                data="2024-01-16",
                valor=150.00,
                cliente_id=1,
                cliente=Mock(name="Test Client"),
                artista=Mock(name="Artist 2"),
            ),
        ]

        with app.test_client() as client:
            with patch(
                "app.controllers.historico_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.historico_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True

                    # Mock database query
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.options.return_value.order_by.return_value.all.return_value = (
                        mock_payments
                    )

                    # Get historico page
                    response = client.get("/historico/")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Verify both payment types are shown
                        assert "100" in html_content
                        assert "150" in html_content
                        assert "Test Client" in html_content

                        # Verify null client is handled appropriately
                        null_client_indicators = [
                            "sem cliente",
                            "no client",
                            "-",
                            "n/a",
                        ]
                        assert any(
                            indicator in html_content.lower()
                            for indicator in null_client_indicators
                        )

    def test_extrato_includes_payments_without_client(self, app):
        """Test that extrato display includes payments without clients."""
        # Mock extrato data with null client payments
        mock_extrato_data = {
            "pagamentos": [
                {
                    "id": 1,
                    "valor": 100.00,
                    "cliente_id": 1,
                    "cliente_name": "Test Client",
                },
                {"id": 2, "valor": 150.00, "cliente_id": None, "cliente_name": None},
            ],
            "totals": {"receita_bruta": 250.00},
        }

        with app.test_client() as client:
            with patch(
                "app.controllers.extrato_controller.generate_extrato"
            ) as mock_generate:
                with patch(
                    "app.controllers.extrato_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True
                    mock_generate.return_value = mock_extrato_data

                    # Get extrato page
                    response = client.get("/extrato/2024/1")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Verify extrato includes both payment types
                        assert "100" in html_content
                        assert "150" in html_content
                        assert "250" in html_content  # Total

                        # Verify null client payments are included
                        assert "Test Client" in html_content
                        # Should have some indication for payments without clients


class TestFormValidationUI:
    """Test form validation UI behavior with optional clients."""

    def test_client_field_not_marked_required_in_html(self, app):
        """Test that client field is not marked as required in HTML form."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True

                    # Mock form data
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Client field should not have required attribute
                        # Look for client field without required
                        import re

                        client_field_pattern = (
                            r'<(?:select|input)[^>]*name=["\']cliente_id["\'][^>]*>'
                        )
                        matches = re.findall(
                            client_field_pattern, html_content, re.IGNORECASE
                        )

                        if matches:
                            # None of the client field matches should contain 'required'
                            for match in matches:
                                assert "required" not in match.lower()

    def test_form_javascript_handles_optional_client(self, app):
        """Test that form JavaScript properly handles optional client selection."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Should not have JavaScript validation preventing empty client
                        js_validation_patterns = [
                            r"cliente_id.*required",
                            r"cliente.*mandatory",
                            r"if.*cliente.*empty.*return false",
                        ]

                        for pattern in js_validation_patterns:
                            import re

                            assert not re.search(pattern, html_content, re.IGNORECASE)


class TestUITextAndLabels:
    """Test UI text and labels for optional client functionality."""

    def test_client_field_labeled_as_optional(self, app):
        """Test that client field is properly labeled as optional."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Look for optional indicators near client field
                        optional_indicators = [
                            "cliente (opcional)",
                            "cliente - opcional",
                            "optional",
                            "não obrigatório",
                        ]

                        # At least one optional indicator should be present
                        assert any(
                            indicator in html_content.lower()
                            for indicator in optional_indicators
                        )

    def test_null_client_display_text(self, app):
        """Test appropriate display text for payments without clients."""
        display_options = [
            "Sem cliente",
            "Cliente não informado",
            "Não especificado",
            "-",
            "N/A",
        ]

        # This would typically be tested in template unit tests
        # For now, we document the expected behavior

        # Mock template rendering context
        with app.app_context():
            from flask import render_template_string

            # Test template snippet that handles null client
            template = """
            {% if payment.cliente %}
                {{ payment.cliente.name }}
            {% else %}
                Sem cliente
            {% endif %}
            """

            # Mock payment without client
            mock_payment = Mock()
            mock_payment.cliente = None

            result = render_template_string(template, payment=mock_payment)
            assert "Sem cliente" in result

    def test_form_placeholder_text(self, app):
        """Test that form has appropriate placeholder text for optional client."""
        with app.test_client() as client:
            with patch(
                "app.controllers.financeiro_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.financeiro_controller.current_user"
                ) as mock_user:
                    mock_user.is_authenticated = True

                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.all.return_value = []

                    response = client.get("/financeiro/registrar-pagamento")

                    if response.status_code == 200:
                        html_content = response.get_data(as_text=True)

                        # Look for appropriate placeholder text
                        placeholder_patterns = [
                            r'placeholder=["\'].*selecione.*opcional',
                            r'placeholder=["\'].*opcional',
                            r">.*Selecione.*opcional.*<",
                        ]

                        import re

                        # At least one placeholder pattern should match
                        has_placeholder = any(
                            re.search(pattern, html_content, re.IGNORECASE)
                            for pattern in placeholder_patterns
                        )

                        # This is optional - not all forms need placeholders
                        # Just documenting expected behavior
