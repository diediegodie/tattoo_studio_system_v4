#!/usr/bin/env python3
"""
Test script to verify the "Commissions by Artist" fix.
This script simulates the scenario where an artist has commissions but no payments/sessions.
"""

import os
import sys

# Add the backend directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.extrato_core import calculate_totals


def test_commissions_by_artist_fix():
    """Test that artists with only commissions are included in por_artista."""

    # Simulate data: artist with only commissions, no payments or sessions
    pagamentos_data = [
        # No payments for Artist C
    ]

    sessoes_data = [
        # No sessions for Artist C
    ]

    comissoes_data = [
        {
            "created_at": "2024-09-15T10:00:00",
            "artista_name": "Artist A",
            "cliente_name": "Client 1",
            "pagamento_valor": 100.0,
            "percentual": 20.0,
            "valor": 20.0,
            "observacoes": "Commission for tattoo",
        },
        {
            "created_at": "2024-09-16T11:00:00",
            "artista_name": "Artist B",
            "cliente_name": "Client 2",
            "pagamento_valor": 200.0,
            "percentual": 15.0,
            "valor": 30.0,
            "observacoes": "Commission for piercing",
        },
        {
            "created_at": "2024-09-17T12:00:00",
            "artista_name": "Artist C",  # This artist has NO payments/sessions, only commissions
            "cliente_name": "Client 3",
            "pagamento_valor": 150.0,
            "percentual": 25.0,
            "valor": 37.5,
            "observacoes": "Commission for Artist C",
        },
    ]

    gastos_data = []

    # Calculate totals
    totals = calculate_totals(
        pagamentos_data, sessoes_data, comissoes_data, gastos_data
    )

    # Check results
    por_artista = totals["por_artista"]

    print("=== Test Results ===")
    print(f"Number of artists in por_artista: {len(por_artista)}")

    for artist in por_artista:
        print(
            f"Artist: {artist['artista']}, Revenue: {artist['receita']}, Commission: {artist['comissao']}"
        )

    # Verify that Artist C is included
    artist_c_found = any(a["artista"] == "Artist C" for a in por_artista)

    if artist_c_found:
        artist_c = next(a for a in por_artista if a["artista"] == "Artist C")
        print("\n✅ SUCCESS: Artist C is included in por_artista")
        print(f"   Revenue: {artist_c['receita']} (should be 0)")
        print(f"   Commission: {artist_c['comissao']} (should be 37.5)")

        if artist_c["receita"] == 0 and artist_c["comissao"] == 37.5:
            print(
                "✅ CORRECT VALUES: Artist C has correct revenue (0) and commission (37.5)"
            )
            return True
        else:
            print("❌ INCORRECT VALUES: Artist C has wrong values")
            return False
    else:
        print("❌ FAILURE: Artist C is NOT included in por_artista")
        return False


if __name__ == "__main__":
    success = test_commissions_by_artist_fix()
    sys.exit(0 if success else 1)
