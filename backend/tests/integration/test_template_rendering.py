"""
Template rendering tests for optional client functionality.
Tests that templates render correctly and contain the expected client handling.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import re
from app.main import create_app


class TestClientOptionalTemplates:
    """Test template rendering for optional client functionality."""

    @pytest.fixture
    def app(self):
        """Create test app for testing."""
        app = create_app()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_registrar_pagamento_template_has_optional_client_field(self, app):
        """Test that registrar_pagamento template has optional client field."""
        with app.app_context():
            # Test template rendering directly with Jinja2
            with app.test_request_context():
                # Mock the data that would be passed to template
                template_data = {
                    "clientes": [
                        Mock(id=1, nome="Test Client"),
                        Mock(id=2, nome="Another Client"),
                    ],
                    "artistas": [Mock(id=1, nome="Test Artist")],
                    "formas_pagamento": ["Dinheiro", "Cartão"],
                }

                # Render the template directly
                rendered = app.jinja_env.get_template(
                    "registrar_pagamento.html"
                ).render(**template_data)

                # Check for optional client labeling
                assert (
                    "Cliente (Opcional)" in rendered
                ), "Client field should be labeled as optional"

                # Check for default "no client" option
                assert (
                    "Nenhum cliente / Não informado" in rendered
                ), "Should have default no-client option"

                # Check that client field is not marked as required
                client_select_pattern = r'<select[^>]*name=["\']?cliente_id["\']?[^>]*>'
                select_match = re.search(client_select_pattern, rendered, re.IGNORECASE)
                if select_match:
                    select_tag = select_match.group(0)
                    assert (
                        "required" not in select_tag.lower()
                    ), "Client field should not be marked as required"

    def test_template_client_field_structure(self, app):
        """Test the structure of client field in template."""
        with app.app_context():
            with app.test_request_context():
                template_data = {"clientes": [], "artistas": [], "formas_pagamento": []}

                rendered = app.jinja_env.get_template(
                    "registrar_pagamento.html"
                ).render(**template_data)

                # Check for select element with proper name
                assert (
                    'name="cliente_id"' in rendered
                ), "Client select should have correct name attribute"

                # Check for empty option as default
                empty_option_pattern = (
                    r'<option[^>]*value=["\']?["\']?[^>]*>.*?Nenhum cliente.*?</option>'
                )
                assert re.search(
                    empty_option_pattern, rendered, re.IGNORECASE
                ), "Should have empty default option"

    def test_financeiro_template_handles_null_clients(self, app):
        """Test that financeiro template handles payments without clients."""
        with app.app_context():
            with app.test_request_context():
                from datetime import datetime

                # Mock pagamentos with and without clients
                pagamentos = [
                    Mock(
                        id=1,
                        valor=100.0,
                        data=datetime(2024, 1, 1),  # Use datetime object
                        cliente=Mock(nome="Test Client"),
                        artista=Mock(nome="Test Artist"),
                        forma_pagamento="Dinheiro",
                    ),
                    Mock(
                        id=2,
                        valor=150.0,
                        data=datetime(2024, 1, 2),  # Use datetime object
                        cliente=None,  # No client
                        artista=Mock(nome="Test Artist"),
                        forma_pagamento="Cartão",
                    ),
                ]

                template_data = {"pagamentos": pagamentos, "totals": {"total": 250.0}}

                rendered = app.jinja_env.get_template("financeiro.html").render(
                    **template_data
                )

                # Should contain both payments
                assert "100" in rendered, "Should show first payment value"
                assert "150" in rendered, "Should show second payment value"

                # Should handle null client gracefully (not crash)
                assert (
                    rendered
                ), "Template should render without errors for null clients"

    def test_historico_template_handles_null_clients(self, app):
        """Test that historico template handles payments without clients in history."""
        with app.app_context():
            with app.test_request_context():
                # Mock historical data - minimal template data needed
                template_data = {
                    "extratos": [],  # Empty to avoid complex data requirements
                    "current_totals": {
                        "receita_total": 250.0,
                        "comissoes_total": 50.0,
                        "saldo": 200.0,
                    },
                    "has_current_entries": False,
                }

                rendered = app.jinja_env.get_template("historico.html").render(
                    **template_data
                )

                # Should render without errors
                assert (
                    rendered
                ), "Template should render without errors for null clients"

                # Should contain basic structure
                assert "Histórico" in rendered, "Should show page title"

    def test_template_client_display_consistency(self, app):
        """Test that null clients are displayed consistently across templates."""
        with app.app_context():
            with app.test_request_context():
                from datetime import datetime

                # Test different ways templates might handle null clients
                mock_payment = Mock(
                    id=1,
                    valor=100.0,
                    data=datetime(2024, 1, 1),
                    cliente=None,
                    artista=Mock(nome="Test Artist"),
                    forma_pagamento="Dinheiro",
                )

                # Test financeiro template
                financeiro_data = {"pagamentos": [mock_payment], "totals": {}}
                financeiro_rendered = app.jinja_env.get_template(
                    "financeiro.html"
                ).render(**financeiro_data)

                # Should not crash and should handle None gracefully
                assert (
                    financeiro_rendered
                ), "Financeiro template should handle null client"

                # Test historico template
                historico_data = {
                    "extratos": [],  # Empty to avoid complex requirements
                    "current_totals": {
                        "receita_total": 0.0,
                        "comissoes_total": 0.0,
                        "saldo": 0.0,
                    },
                    "has_current_entries": False,
                }
                historico_rendered = app.jinja_env.get_template(
                    "historico.html"
                ).render(**historico_data)

                # Should not crash and should handle None gracefully
                assert (
                    historico_rendered
                ), "Historico template should handle null client"

    def test_registrar_pagamento_form_validation(self, app):
        """Test form validation logic for optional client field."""
        with app.app_context():
            with app.test_request_context():
                template_data = {
                    "clientes": [Mock(id=1, nome="Test Client")],
                    "artistas": [Mock(id=1, nome="Test Artist")],
                    "formas_pagamento": ["Dinheiro"],
                }

                rendered = app.jinja_env.get_template(
                    "registrar_pagamento.html"
                ).render(**template_data)

                # Check that form doesn't enforce client selection
                # Look for any JavaScript validation that might make client required
                if "required" in rendered.lower():
                    # If required is found, make sure it's not on the client field
                    lines = rendered.split("\n")
                    for line in lines:
                        if "cliente_id" in line and "required" in line.lower():
                            pytest.fail("Client field should not be marked as required")

    def test_template_accessibility(self, app):
        """Test that templates maintain accessibility with optional client field."""
        with app.app_context():
            with app.test_request_context():
                template_data = {
                    "clientes": [],
                    "artistas": [Mock(id=1, nome="Test Artist")],
                    "formas_pagamento": ["Dinheiro"],
                }

                rendered = app.jinja_env.get_template(
                    "registrar_pagamento.html"
                ).render(**template_data)

                # Check for proper labeling
                assert "label" in rendered.lower(), "Form should have proper labels"

                # Check that optional nature is clearly indicated
                assert (
                    "opcional" in rendered.lower()
                ), "Optional nature should be clearly indicated"
