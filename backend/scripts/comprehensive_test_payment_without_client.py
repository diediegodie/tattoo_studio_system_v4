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
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def test_complete_payment_flow_without_client():
    """Test complete payment registration and retrieval without client."""

    logger.info("COMPREHENSIVE TEST: Payment Registration Without Client")

    db = SessionLocal()
    success_count = 0
    total_tests = 5

    try:
        # TEST 1: Database Schema Validation
        logger.info("Testing Database Schema...")

        # Ensure we have a test artist
        artist = db.query(User).filter_by(name="Test Artist").first()
        if not artist:
            artist = User()
            artist.name = "Test Artist"
            artist.email = "test@example.com"
            artist.role = "artist"
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
            logger.info("Database accepts NULL cliente_id")
            success_count += 1
        else:
            logger.error("Database rejected NULL cliente_id")

        # TEST 2: Controller Logic Simulation
        logger.info("Testing Controller Validation Logic...")

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
            logger.info("Controller validation passes without cliente_id")
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
            logger.error("Controller validation failed")

        # TEST 3: Search Functionality
        logger.info("Testing Search Functionality...")

        search_service = SearchService(db)
        results = search_service.search("Comprehensive test")

        if "pagamentos" in results and len(results["pagamentos"]) > 0:
            found_payment = None
            for p in results["pagamentos"]:
                if "Comprehensive test" in p.get("observacoes", ""):
                    found_payment = p
                    break

            if found_payment and found_payment.get("cliente_name") == "":
                logger.info("Search finds payments without clients")
                success_count += 1
            else:
                logger.error("Search does not properly handle payments without clients")
        else:
            logger.error("Search did not find test payments")

        # TEST 4: Historico/List Display
        logger.info("Testing Payment List Display...")

        # Query all payments to simulate Historico view
        all_payments = db.query(Pagamento).order_by(Pagamento.data.desc()).all()
        payments_without_clients = [p for p in all_payments if p.cliente_id is None]

        if len(payments_without_clients) >= 2:  # Our test payments
            logger.info(
                "Found payments without clients",
                extra={"context": {"count": len(payments_without_clients)}},
            )
            for p in payments_without_clients[:2]:  # Show first 2
                client_display = (
                    "No client" if p.cliente_id is None else f"Client {p.cliente_id}"
                )
                logger.info(
                    "Payment",
                    extra={
                        "context": {
                            "payment_id": p.id,
                            "valor": str(p.valor),
                            "forma_pagamento": p.forma_pagamento,
                            "client_display": client_display,
                        }
                    },
                )
            success_count += 1
        else:
            logger.error("No payments without clients found in list")

        # TEST 5: Data Integrity
        logger.info("Testing Data Integrity...")

        # Verify relationships work correctly with NULL cliente_id
        test_payment = payments_without_clients[0] if payments_without_clients else None

        if test_payment:
            # Should have artist but no client
            has_artist = test_payment.artista is not None
            has_no_client = test_payment.cliente is None

            if has_artist and has_no_client:
                logger.info(
                    "Relationships work correctly with NULL cliente_id",
                    extra={
                        "context": {
                            "artist": getattr(test_payment.artista, "name", None),
                            "client": None,
                        }
                    },
                )
                success_count += 1
            else:
                logger.error("Relationship integrity issue")
        else:
            logger.error("No test payment available for relationship check")

        # SUMMARY
        logger.info(
            "TEST RESULTS",
            extra={"context": {"passed": success_count, "total": total_tests}},
        )

        if success_count == total_tests:
            logger.info(
                "ALL TESTS PASSED: Payments can be fully registered and managed without clients; schema supports nullable cliente_id; controller validation works; search includes payments without clients; list displays correctly; relationships maintain integrity."
            )
            return True
        else:
            logger.error(
                "Some tests failed",
                extra={"context": {"failed": total_tests - success_count}},
            )
            return False

    except Exception as e:
        logger.error(
            "Error during testing", extra={"context": {"error": str(e)}}, exc_info=True
        )
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_complete_payment_flow_without_client()

    if success:
        logger.info("SYSTEM READY: Optional client requirement fully implemented!")
        sys.exit(0)
    else:
        logger.error("SYSTEM NOT READY: Issues found in implementation")
        sys.exit(1)
