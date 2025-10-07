"""
Core Commission Exclusion Regression Test

This is a simplified regression test that validates the critical commission exclusion fix:
- Artists with 0% commission should NOT appear in "Comissões por Artista" summary
- But they SHOULD appear in "Pagamentos realizados" records
- All payment totals should still be calculated correctly

This test runs the actual calculate_totals function with realistic test data
to ensure the commission filtering logic works as expected.
"""

import pytest
from app.services.extrato_core import calculate_totals


class TestCommissionExclusionRegression:
    """Core regression tests for commission exclusion logic."""

    def test_commission_exclusion_basic_scenario(self):
        """Test basic commission exclusion scenario."""
        # Test data with mixed commission scenarios
        pagamentos = [
            {
                "id": 1,
                "valor": 200.00,
                "artista_name": "Artist With Commission",
                "data": "2025-09-30",
                "forma_pagamento": "cartao",
                "cliente_name": "Cliente A",
            },
            {
                "id": 2,
                "valor": 150.00,
                "artista_name": "Artist Zero Commission",
                "data": "2025-09-30",
                "forma_pagamento": "dinheiro",
                "cliente_name": None,  # Walk-in
            },
            {
                "id": 3,
                "valor": 300.00,
                "artista_name": "Owner Artist",
                "data": "2025-09-30",
                "forma_pagamento": "pix",
                "cliente_name": "Cliente B",
            },
        ]

        sessoes = []  # Not needed for this test

        comissoes = [
            {
                "id": 1,
                "valor": 60.00,  # 30% of 200
                "artista_name": "Artist With Commission",
                "pagamento_id": 1,
            }
            # NOTE: No commission records for "Artist Zero Commission" or "Owner Artist"
        ]

        gastos = [
            {
                "id": 1,
                "valor": 50.00,
                "descricao": "Supplies",
                "forma_pagamento": "cartao",
            }
        ]

        # Execute the function under test
        totals = calculate_totals(pagamentos, sessoes, comissoes, gastos)

        # Validate calculations
        assert (
            totals["receita_total"] == 650.00
        )  # All payments counted: 200 + 150 + 300
        assert (
            totals["comissoes_total"] == 60.00
        )  # Only commission for Artist With Commission
        assert totals["despesas_total"] == 50.00
        assert totals["receita_liquida"] == 540.00  # 650 - 60 - 50

        # CRITICAL TEST: Commission summary should exclude zero-commission artists
        por_artista = totals["por_artista"]
        assert (
            len(por_artista) == 1
        ), f"Expected 1 artist in commission summary, got {len(por_artista)}"

        assert por_artista[0]["artista"] == "Artist With Commission"
        assert por_artista[0]["receita"] == 200.00
        assert por_artista[0]["comissao"] == 60.00

        # Verify excluded artists
        artist_names = [item["artista"] for item in por_artista]
        assert "Artist Zero Commission" not in artist_names
        assert "Owner Artist" not in artist_names

    def test_commission_exclusion_with_multiple_artists(self):
        """Test commission exclusion with multiple artists having different scenarios."""
        pagamentos = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Artist A",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 200.00,
                "artista_name": "Artist B",
                "forma_pagamento": "dinheiro",
            },
            {
                "id": 3,
                "valor": 150.00,
                "artista_name": "Artist Zero",
                "forma_pagamento": "pix",
            },
            {
                "id": 4,
                "valor": 300.00,
                "artista_name": "Artist C",
                "forma_pagamento": "cartao",
            },
            {
                "id": 5,
                "valor": 250.00,
                "artista_name": "Artist Zero 2",
                "forma_pagamento": "dinheiro",
            },
        ]

        comissoes = [
            {"id": 1, "valor": 30.00, "artista_name": "Artist A", "pagamento_id": 1},
            {"id": 2, "valor": 80.00, "artista_name": "Artist B", "pagamento_id": 2},
            {"id": 3, "valor": 120.00, "artista_name": "Artist C", "pagamento_id": 4},
            # No commissions for "Artist Zero" and "Artist Zero 2"
        ]

        totals = calculate_totals(pagamentos, [], comissoes, [])

        # Validate totals
        assert totals["receita_total"] == 1000.00  # All payments: 100+200+150+300+250
        assert totals["comissoes_total"] == 230.00  # Only for artists A, B, C

        # Validate commission summary only includes artists with commissions > 0
        por_artista = totals["por_artista"]
        assert (
            len(por_artista) == 3
        ), f"Expected 3 artists with commissions, got {len(por_artista)}"

        artist_names = [item["artista"] for item in por_artista]
        assert "Artist A" in artist_names
        assert "Artist B" in artist_names
        assert "Artist C" in artist_names
        assert "Artist Zero" not in artist_names
        assert "Artist Zero 2" not in artist_names

    def test_commission_exclusion_edge_cases(self):
        """Test edge cases for commission exclusion."""
        # Edge case 1: Very small commission (should be included)
        pagamentos_small = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Small Commission Artist",
                "forma_pagamento": "cartao",
            }
        ]
        comissoes_small = [
            {
                "id": 1,
                "valor": 0.01,
                "artista_name": "Small Commission Artist",
                "pagamento_id": 1,
            }
        ]

        totals_small = calculate_totals(pagamentos_small, [], comissoes_small, [])

        # Should include artist with commission = 0.01 (> 0)
        assert len(totals_small["por_artista"]) == 1
        assert totals_small["por_artista"][0]["comissao"] == 0.01

        # Edge case 2: Only zero-commission artists
        pagamentos_zero = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Zero Artist 1",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 200.00,
                "artista_name": "Zero Artist 2",
                "forma_pagamento": "dinheiro",
            },
        ]
        comissoes_zero = []  # No commissions

        totals_zero = calculate_totals(pagamentos_zero, [], comissoes_zero, [])

        # Should have empty commission summary but total revenue counted
        assert len(totals_zero["por_artista"]) == 0
        assert totals_zero["receita_total"] == 300.00
        assert totals_zero["comissoes_total"] == 0.00

    def test_commission_exclusion_preserves_payment_data(self):
        """Verify that payment data is preserved even for excluded artists."""
        pagamentos = [
            {
                "id": 1,
                "valor": 100.00,
                "artista_name": "Normal Artist",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 200.00,
                "artista_name": "Zero Commission Artist",
                "forma_pagamento": "dinheiro",
            },
        ]

        comissoes = [
            {
                "id": 1,
                "valor": 30.00,
                "artista_name": "Normal Artist",
                "pagamento_id": 1,
            }
        ]

        totals = calculate_totals(pagamentos, [], comissoes, [])

        # Commission summary should exclude zero-commission artist
        por_artista = totals["por_artista"]
        assert len(por_artista) == 1
        assert por_artista[0]["artista"] == "Normal Artist"

        # But total revenue should include ALL payments
        assert totals["receita_total"] == 300.00  # 100 + 200

        # And payment method breakdown should include all payments
        por_forma = totals["por_forma_pagamento"]
        cartao_total = next(
            (item["total"] for item in por_forma if item["forma"] == "cartao"), 0
        )
        dinheiro_total = next(
            (item["total"] for item in por_forma if item["forma"] == "dinheiro"), 0
        )

        assert cartao_total == 100.00  # Normal Artist payment
        assert (
            dinheiro_total == 200.00
        )  # Zero Commission Artist payment (should be included)

    def test_commission_exclusion_realistic_scenario(self):
        """Test with realistic studio scenario data."""
        # Real-world scenario: Studio with mix of employees and contractors
        pagamentos = [
            # Employee artist (gets commission)
            {
                "id": 1,
                "valor": 250.00,
                "artista_name": "João Silva",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 180.00,
                "artista_name": "João Silva",
                "forma_pagamento": "pix",
            },
            # Apprentice (no commission yet)
            {
                "id": 3,
                "valor": 120.00,
                "artista_name": "Maria Aprendiz",
                "forma_pagamento": "dinheiro",
            },
            # Studio owner (no commission record - keeps 100%)
            {
                "id": 4,
                "valor": 400.00,
                "artista_name": "Carlos Dono",
                "forma_pagamento": "cartao",
            },
            # Guest artist (gets commission)
            {
                "id": 5,
                "valor": 300.00,
                "artista_name": "Ana Convidada",
                "forma_pagamento": "pix",
            },
        ]

        comissoes = [
            {
                "id": 1,
                "valor": 75.00,
                "artista_name": "João Silva",
                "pagamento_id": 1,
            },  # 30% of 250
            {
                "id": 2,
                "valor": 54.00,
                "artista_name": "João Silva",
                "pagamento_id": 2,
            },  # 30% of 180
            {
                "id": 3,
                "valor": 150.00,
                "artista_name": "Ana Convidada",
                "pagamento_id": 5,
            },  # 50% of 300
            # No commission for Maria Aprendiz (apprentice) or Carlos Dono (owner)
        ]

        gastos = [
            {
                "id": 1,
                "valor": 80.00,
                "descricao": "Materiais",
                "forma_pagamento": "cartao",
            },
            {
                "id": 2,
                "valor": 150.00,
                "descricao": "Aluguel",
                "forma_pagamento": "debito",
            },
        ]

        totals = calculate_totals(pagamentos, [], comissoes, gastos)

        # Validate totals
        assert totals["receita_total"] == 1250.00  # All payments: 250+180+120+400+300
        assert totals["comissoes_total"] == 279.00  # Only for João and Ana: 75+54+150
        assert totals["despesas_total"] == 230.00  # 80+150
        assert totals["receita_liquida"] == 741.00  # 1250 - 279 - 230

        # Commission summary should only include artists with commissions > 0
        por_artista = totals["por_artista"]
        assert (
            len(por_artista) == 2
        ), f"Expected 2 artists with commissions, got {len(por_artista)}"

        artist_names = [item["artista"] for item in por_artista]
        assert "João Silva" in artist_names
        assert "Ana Convidada" in artist_names
        assert "Maria Aprendiz" not in artist_names  # Apprentice excluded
        assert "Carlos Dono" not in artist_names  # Owner excluded

        # Find João Silva's summary
        joao_summary = next(
            item for item in por_artista if item["artista"] == "João Silva"
        )
        assert joao_summary["receita"] == 430.00  # 250 + 180
        assert joao_summary["comissao"] == 129.00  # 75 + 54

        # Find Ana Convidada's summary
        ana_summary = next(
            item for item in por_artista if item["artista"] == "Ana Convidada"
        )
        assert ana_summary["receita"] == 300.00
        assert ana_summary["comissao"] == 150.00


# Additional validation to ensure the fix is working as expected
def test_commission_exclusion_before_vs_after_fix():
    """
    Test to validate that the commission exclusion fix is working.

    Before the fix: Artists with 0% commission would appear in por_artista summary
    After the fix: Only artists with commission > 0 appear in por_artista summary
    """
    pagamentos = [
        {
            "id": 1,
            "valor": 200.00,
            "artista_name": "Artist Normal",
            "forma_pagamento": "cartao",
        },
        {
            "id": 2,
            "valor": 150.00,
            "artista_name": "Artist Zero Commission",
            "forma_pagamento": "dinheiro",
        },
    ]

    comissoes = [
        {"id": 1, "valor": 60.00, "artista_name": "Artist Normal", "pagamento_id": 1}
        # IMPORTANTLY: No commission record for "Artist Zero Commission"
    ]

    totals = calculate_totals(pagamentos, [], comissoes, [])

    # BEFORE THE FIX: This test would fail because por_artista would have 2 items
    # AFTER THE FIX: This test passes because por_artista only has 1 item

    por_artista = totals["por_artista"]
    assert len(por_artista) == 1, (
        f"Commission exclusion fix validation failed: "
        f"Expected 1 artist in commission summary (only those with commission > 0), "
        f"but got {len(por_artista)}: {[item['artista'] for item in por_artista]}"
    )

    assert por_artista[0]["artista"] == "Artist Normal"
    assert por_artista[0]["comissao"] == 60.00

    # But total revenue should still include all payments
    assert totals["receita_total"] == 350.00  # 200 + 150

    print("✓ Commission exclusion fix is working correctly!")
    print(
        f"✓ Artists in commission summary: {[item['artista'] for item in por_artista]}"
    )
    print(f"✓ Total revenue includes all payments: R$ {totals['receita_total']}")
