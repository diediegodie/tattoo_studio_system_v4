#!/usr/bin/env python3
"""
Test for zero-commission artist exclusion fix.

This test validates that artists with 0% commission are excluded from the
"Comissões por Artista" summary section while their payment records remain intact.
"""

import os
import sys
import pytest

# Add the backend directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.extrato_core import calculate_totals


class TestZeroCommissionExclusion:
    """Test suite for zero-commission artist exclusion logic."""

    def test_zero_commission_artist_excluded_from_summary(self):
        """Test that artists with 0% commission are excluded from por_artista summary."""

        # Payment data: Artist B has a payment but will have 0% commission
        pagamentos_data = [
            {
                "id": 1,
                "valor": 100.0,
                "artista_name": "Artist A",
                "forma_pagamento": "Dinheiro",
                "sessao_id": None,
            },
            {
                "id": 2,
                "valor": 200.0,
                "artista_name": "Artist B",  # This artist will have 0% commission
                "forma_pagamento": "PIX",
                "sessao_id": None,
            },
        ]

        # Session data: both artists have sessions
        sessoes_data = [
            {
                "id": 1,
                "valor": 100.0,
                "artista_name": "Artist A",
                "data": "2024-09-15",
            },
            {
                "id": 2,
                "valor": 200.0,
                "artista_name": "Artist B",
                "data": "2024-09-16",
            },
        ]

        # Commission data: Only Artist A has commission, Artist B has none
        comissoes_data = [
            {
                "artista_name": "Artist A",
                "valor": 15.0,  # 15% of 100
                "percentual": 15.0,
            },
            # NOTE: No commission entry for Artist B (0% commission)
        ]

        gastos_data = []

        # Calculate totals
        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Verify results
        por_artista = totals["por_artista"]

        # Should only include Artist A (who has commission > 0)
        assert (
            len(por_artista) == 1
        ), f"Expected 1 artist in summary, got {len(por_artista)}"

        # Artist A should be included
        artist_a = por_artista[0]
        assert artist_a["artista"] == "Artist A"
        assert (
            artist_a["receita"] == 200.0
        )  # 100 from payment + 100 from unpaid session
        assert artist_a["comissao"] == 15.0

        # Artist B should NOT be in the summary (despite having payments/sessions)
        artist_names = [a["artista"] for a in por_artista]
        assert (
            "Artist B" not in artist_names
        ), "Artist B with 0% commission should not appear in summary"

    def test_all_zero_commission_artists_excluded(self):
        """Test that when all artists have 0% commission, summary is empty."""

        pagamentos_data = [
            {
                "id": 1,
                "valor": 100.0,
                "artista_name": "Artist A",
                "forma_pagamento": "Dinheiro",
                "sessao_id": None,
            },
            {
                "id": 2,
                "valor": 200.0,
                "artista_name": "Artist B",
                "forma_pagamento": "PIX",
                "sessao_id": None,
            },
        ]

        sessoes_data = []
        comissoes_data = []  # No commissions for any artist
        gastos_data = []

        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        # Summary should be empty
        assert (
            len(totals["por_artista"]) == 0
        ), "Summary should be empty when no artists have commissions"

        # But total revenue should still include all payments
        assert (
            totals["receita_total"] == 300.0
        ), "Total revenue should include all payments"
        assert totals["comissoes_total"] == 0.0, "Total commissions should be zero"

    def test_mixed_commission_scenario(self):
        """Test scenario with mix of artists: some with commissions, some without."""

        pagamentos_data = [
            {
                "id": 1,
                "valor": 100.0,
                "artista_name": "Artist A",
                "forma_pagamento": "Dinheiro",
                "sessao_id": None,
            },
            {
                "id": 2,
                "valor": 200.0,
                "artista_name": "Artist B",
                "forma_pagamento": "PIX",
                "sessao_id": None,
            },
            {
                "id": 3,
                "valor": 300.0,
                "artista_name": "Artist C",
                "forma_pagamento": "Cartão",
                "sessao_id": None,
            },
        ]

        sessoes_data = []

        # Only Artist A and C have commissions
        comissoes_data = [
            {
                "artista_name": "Artist A",
                "valor": 20.0,
                "percentual": 20.0,
            },
            {
                "artista_name": "Artist C",
                "valor": 45.0,
                "percentual": 15.0,
            },
            # Artist B has no commission (0%)
        ]

        gastos_data = []

        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        por_artista = totals["por_artista"]

        # Should only include Artist A and C
        assert (
            len(por_artista) == 2
        ), f"Expected 2 artists in summary, got {len(por_artista)}"

        artist_names = [a["artista"] for a in por_artista]
        assert "Artist A" in artist_names, "Artist A should be in summary"
        assert "Artist C" in artist_names, "Artist C should be in summary"
        assert (
            "Artist B" not in artist_names
        ), "Artist B (0% commission) should not be in summary"

        # Verify total calculations are still correct
        assert (
            totals["receita_total"] == 600.0
        ), "Total revenue should include all payments"
        assert totals["comissoes_total"] == 65.0, "Total commissions should be 20 + 45"

    def test_commission_edge_cases(self):
        """Test edge cases like very small commission amounts."""

        pagamentos_data = [
            {
                "id": 1,
                "valor": 100.0,
                "artista_name": "Artist A",
                "forma_pagamento": "Dinheiro",
                "sessao_id": None,
            },
        ]

        sessoes_data = []

        # Artist with very small commission (0.01)
        comissoes_data = [
            {
                "artista_name": "Artist A",
                "valor": 0.01,
                "percentual": 0.01,
            },
        ]

        gastos_data = []

        totals = calculate_totals(
            pagamentos_data, sessoes_data, comissoes_data, gastos_data
        )

        por_artista = totals["por_artista"]

        # Should include Artist A since commission > 0
        assert len(por_artista) == 1, "Artist with small commission should be included"
        assert por_artista[0]["artista"] == "Artist A"
        assert por_artista[0]["comissao"] == 0.01


def test_zero_commission_exclusion_standalone():
    """Standalone test function that can be run independently."""
    test_instance = TestZeroCommissionExclusion()

    print("Testing zero-commission artist exclusion...")
    test_instance.test_zero_commission_artist_excluded_from_summary()
    print("✅ Test 1 passed: Zero-commission artist excluded")

    test_instance.test_all_zero_commission_artists_excluded()
    print("✅ Test 2 passed: All zero-commission scenario")

    test_instance.test_mixed_commission_scenario()
    print("✅ Test 3 passed: Mixed commission scenario")

    test_instance.test_commission_edge_cases()
    print("✅ Test 4 passed: Edge cases")

    print("🎉 All zero-commission exclusion tests passed!")
    return True


if __name__ == "__main__":
    try:
        success = test_zero_commission_exclusion_standalone()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        sys.exit(1)
