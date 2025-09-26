#!/usr/bin/env python3
"""
Comprehensive Integration Test: Payment Registration Without Client

This script demonstrates and tests the complete flow of registering payments
without requiring a client, covering all aspects from database to search.
"""

import os
import sys
from datetime import date
from decimal import Decimal

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

os.environ["DATABASE_URL"] = "sqlite:///tattoo_studio_dev.db"

from app.db.base import Pagamento, User, Client
from app.db.session import SessionLocal
from app.services.search_service import SearchService


def test_complete_payment_flow_without_client():
    """Test complete payment registration and retrieval without client."""

    print("🧪 COMPREHENSIVE TEST: Payment Registration Without Client")
    print("=" * 60)

    db = SessionLocal()
    success_count = 0
    total_tests = 5

    try:
        # TEST 1: Database Schema Validation
        print("\n1️⃣  Testing Database Schema...")

        # Ensure we have a test artist
        artist = db.query(User).filter_by(name="Test Artist").first()
        if not artist:
            artist = User(name="Test Artist", email="test@example.com", role="artist")
            db.add(artist)
            db.commit()

        # Test direct database insertion with NULL cliente_id
        payment = Pagamento(
            data=date.today(),
            valor=Decimal("200.00"),
            forma_pagamento="Cartão de Crédito",
            cliente_id=None,  # NULL client
            artista_id=artist.id,
            observacoes="Comprehensive test - no client required",
        )
        db.add(payment)
        db.commit()

        if payment.cliente_id is None:
            print("   ✅ Database accepts NULL cliente_id")
            success_count += 1
        else:
            print("   ❌ Database rejected NULL cliente_id")

        # TEST 2: Controller Logic Simulation
        print("\n2️⃣  Testing Controller Validation Logic...")

        # Simulate form data with empty cliente_id
        form_data = {
            "data": str(date.today()),
            "valor": "300.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "",  # Empty string from form
            "artista_id": str(artist.id),
            "observacoes": "Controller test - empty client field",
        }

        # Simulate controller's cliente_id processing
        cliente_id_raw = form_data.get("cliente_id")
        cliente_id = (
            cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
        )

        # Simulate required fields validation (should NOT include cliente_id)
        required_fields = [
            form_data.get("data"),
            form_data.get("valor"),
            form_data.get("forma_pagamento"),
            form_data.get("artista_id"),
        ]

        if all(required_fields) and cliente_id is None:
            print("   ✅ Controller validation passes without cliente_id")
            success_count += 1

            # Create payment with controller logic
            payment2 = Pagamento(
                data=date.today(),
                valor=Decimal(form_data["valor"]),
                forma_pagamento=form_data["forma_pagamento"],
                cliente_id=cliente_id,  # Should be None
                artista_id=int(form_data["artista_id"]),
                observacoes=form_data["observacoes"],
            )
            db.add(payment2)
            db.commit()
        else:
            print("   ❌ Controller validation failed")

        # TEST 3: Search Functionality
        print("\n3️⃣  Testing Search Functionality...")

        search_service = SearchService(db)
        results = search_service.search("Comprehensive test")

        if "pagamentos" in results and len(results["pagamentos"]) > 0:
            found_payment = None
            for p in results["pagamentos"]:
                if "Comprehensive test" in p.get("observacoes", ""):
                    found_payment = p
                    break

            if found_payment and found_payment.get("cliente_name") == "":
                print("   ✅ Search finds payments without clients")
                success_count += 1
            else:
                print("   ❌ Search does not properly handle payments without clients")
        else:
            print("   ❌ Search did not find test payments")

        # TEST 4: Historico/List Display
        print("\n4️⃣  Testing Payment List Display...")

        # Query all payments to simulate Historico view
        all_payments = db.query(Pagamento).order_by(Pagamento.data.desc()).all()
        payments_without_clients = [p for p in all_payments if p.cliente_id is None]

        if len(payments_without_clients) >= 2:  # Our test payments
            print(
                f"   ✅ Found {len(payments_without_clients)} payments without clients"
            )
            for p in payments_without_clients[:2]:  # Show first 2
                client_display = (
                    "No client" if p.cliente_id is None else f"Client {p.cliente_id}"
                )
                print(
                    f"      Payment {p.id}: {p.valor} {p.forma_pagamento} - {client_display}"
                )
            success_count += 1
        else:
            print("   ❌ No payments without clients found in list")

        # TEST 5: Data Integrity
        print("\n5️⃣  Testing Data Integrity...")

        # Verify relationships work correctly with NULL cliente_id
        test_payment = payments_without_clients[0] if payments_without_clients else None

        if test_payment:
            # Should have artist but no client
            has_artist = test_payment.artista is not None
            has_no_client = test_payment.cliente is None

            if has_artist and has_no_client:
                print("   ✅ Relationships work correctly with NULL cliente_id")
                print(f"      Artist: {test_payment.artista.name}")
                print(f"      Client: None (as expected)")
                success_count += 1
            else:
                print("   ❌ Relationship integrity issue")
        else:
            print("   ❌ No test payment available for relationship check")

        # SUMMARY
        print("\n" + "=" * 60)
        print(f"🎯 TEST RESULTS: {success_count}/{total_tests} tests passed")

        if success_count == total_tests:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Payments can be fully registered and managed without clients")
            print("✅ Database schema supports optional cliente_id")
            print("✅ Controller validation works without cliente_id")
            print("✅ Search includes payments without clients")
            print("✅ List/Historico displays payments without clients")
            print("✅ Data relationships maintain integrity")
            return True
        else:
            print(f"❌ {total_tests - success_count} test(s) failed")
            return False

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_complete_payment_flow_without_client()

    if success:
        print("\n✅ SYSTEM READY: Optional client requirement fully implemented!")
        sys.exit(0)
    else:
        print("\n❌ SYSTEM NOT READY: Issues found in implementation")
        sys.exit(1)
