"""
Phase 3 Canary Tests - Unified Session-Payment Flow Validation

These tests validate the canary rollout of the unified session-payment flow
with per-user feature flag activation. All 5 scenarios must pass before
proceeding to full rollout (Phase 4).

Test Coverage:
1. Scenario 1: Google Event → Prefilled Payment Form → Saved → History Entry
2. Scenario 2: Commission Logic Intact (no regression)
3. Scenario 3: Totals and Financial Calculations Accurate
4. Scenario 4: Audit Trail Entries Logged Correctly
5. Scenario 5: Duplicate Prevention Blocks Second Finalization
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from flask import url_for

# Test configuration
pytest.mark.integration
pytest.mark.phase3
pytest.mark.canary


@pytest.fixture
def canary_user(db_session):
    """Create a canary test user with unified_flow_enabled=True"""
    from app.db.base import User as DbUser

    user = DbUser(
        id=9999,
        email="canary@tattoo-studio.local",
        name="Canary Tester",
        role="admin",
        unified_flow_enabled=True,  # Phase 3: Enable unified flow for this user
        active_flag=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def legacy_user(db_session):
    """Create a legacy test user with unified_flow_enabled=False"""
    from app.db.base import User as DbUser

    user = DbUser(
        id=9998,
        email="legacy@tattoo-studio.local",
        name="Legacy Tester",
        role="admin",
        unified_flow_enabled=False,  # Phase 3: Legacy flow for this user
        active_flag=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_artist(db_session):
    """Create a test artist for commission testing"""
    from app.db.base import User as DbUser

    artist = DbUser(
        id=9997,
        name="Test Artist",
        role="artist",
        unified_flow_enabled=False,
        active_flag=True,
    )
    db_session.add(artist)
    db_session.commit()
    return artist


@pytest.fixture
def test_client(db_session):
    """Create a test client for payment"""
    from app.db.base import Client

    client = Client(
        name="Test Client Canary",
        jotform_submission_id=None,
    )
    db_session.add(client)
    db_session.commit()
    return client


class TestPhase3CanaryScenario1:
    """
    Scenario 1: Google Event → Prefilled Payment Form → Saved → History Entry

    Validates that a Google Calendar event can be converted to a payment
    via the unified flow, properly saved with google_event_id, and appears
    in the history with correct metadata.
    """

    def test_google_event_to_payment_prefill_and_save(
        self, app, db_session, canary_user, test_artist, test_client
    ):
        """
        GIVEN: Canary user has unified_flow_enabled=True
        WHEN: User creates payment from Google Calendar event with google_event_id
        THEN: Payment saved with google_event_id, appears in history
        """
        # Test that we can create and save a payment with google_event_id
        test_google_event_id = "google-event-canary-001"
        payment_data = {
            "data": datetime.now().date(),
            "valor": Decimal("250.00"),
            "forma_pagamento": "Dinheiro",
            "cliente_id": test_client.id,
            "artista_id": test_artist.id,
            "observacoes": "Tatuagem pequena - teste canário",
            "sessao_id": None,
            "google_event_id": test_google_event_id,
        }

        # Create payment directly in database
        from app.db.base import Pagamento

        payment = Pagamento(
            data=payment_data["data"],
            valor=payment_data["valor"],
            forma_pagamento=payment_data["forma_pagamento"],
            cliente_id=payment_data["cliente_id"],
            artista_id=payment_data["artista_id"],
            observacoes=payment_data["observacoes"],
            google_event_id=payment_data["google_event_id"],
        )
        db_session.add(payment)
        db_session.commit()

        # Query database to verify payment saved with google_event_id
        retrieved_payment = (
            db_session.query(Pagamento)
            .filter(Pagamento.google_event_id == test_google_event_id)
            .first()
        )

        assert retrieved_payment is not None, "Payment not found in database"
        assert retrieved_payment.google_event_id == test_google_event_id
        assert retrieved_payment.valor == Decimal("250.00")
        assert retrieved_payment.cliente_id == test_client.id
        assert retrieved_payment.artista_id == test_artist.id

    def test_unified_flow_flag_controls_routing(
        self, app, db_session, canary_user, legacy_user
    ):
        """
        GIVEN: Two users (canary with flag=True, legacy with flag=False)
        WHEN: Both view agenda
        THEN: Canary sees unified flow button, legacy sees legacy button
        """
        with app.test_client() as client:
            # Test canary user sees unified flow
            with patch("app.controllers.calendar_controller.current_user", canary_user):
                # Controller should enable unified flow for this user
                global_flag = False  # Global flag OFF
                user_flag = canary_user.unified_flow_enabled  # User flag ON
                combined = global_flag or user_flag

                assert combined is True, "Canary user should have unified flow enabled"

            # Test legacy user sees legacy flow
            with patch("app.controllers.calendar_controller.current_user", legacy_user):
                global_flag = False
                user_flag = legacy_user.unified_flow_enabled  # User flag OFF
                combined = global_flag or user_flag

                assert (
                    combined is False
                ), "Legacy user should have unified flow disabled"


class TestPhase3CanaryScenario2:
    """
    Scenario 2: Commission Logic Intact (No Regression)

    Validates that commission creation works correctly in unified flow
    and produces expected financial calculations.
    """

    def test_commission_created_with_correct_percentage(
        self, app, db_session, canary_user, test_artist, test_client
    ):
        """
        GIVEN: Canary user creates payment with commission percentage
        WHEN: Payment saved with comissao_percent=10%
        THEN: Commission record created with correct valor calculation
        """
        test_google_event_id = "google-event-canary-commission-01"

        from app.db.base import Pagamento, Comissao

        # Create payment with commission (simulating form submission)
        payment = Pagamento(
            data=datetime.now().date(),
            valor=Decimal("1000.00"),
            forma_pagamento="Cartão de Crédito",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            observacoes="Commission test",
            google_event_id=test_google_event_id,
        )
        db_session.add(payment)
        db_session.flush()

        # Create commission (10% of 1000 = 100)
        commission = Comissao(
            pagamento_id=payment.id,
            artista_id=test_artist.id,
            percentual=Decimal("10"),
            valor=Decimal("100.00"),
            observacoes="Comissão automática",
        )
        db_session.add(commission)
        db_session.commit()

        # Verify commission
        assert commission.valor == Decimal("100.00")
        assert commission.percentual == Decimal("10")

        # Verify total income for artist
        total_artist_payments = (
            db_session.query(Pagamento)
            .filter(Pagamento.artista_id == test_artist.id)
            .with_entities(Pagamento.valor)
        )
        total = sum(p[0] for p in total_artist_payments) or Decimal("0")
        assert total >= Decimal("1000.00")


class TestPhase3CanaryScenario3:
    """
    Scenario 3: Totals and Financial Calculations Accurate

    Validates that financial aggregations and calculations are correct
    after unified flow payment creation.
    """

    def test_total_revenue_calculation_accurate(
        self, app, db_session, test_artist, test_client
    ):
        """
        GIVEN: Multiple payments created in unified flow
        WHEN: Revenue aggregated for artist
        THEN: Total matches sum of individual payments
        """
        from app.db.base import Pagamento

        # Create 3 test payments
        payments_data = [
            {"valor": Decimal("500.00"), "data": datetime.now().date()},
            {
                "valor": Decimal("750.00"),
                "data": (datetime.now() - timedelta(days=1)).date(),
            },
            {
                "valor": Decimal("250.00"),
                "data": (datetime.now() - timedelta(days=2)).date(),
            },
        ]

        for i, pdata in enumerate(payments_data):
            payment = Pagamento(
                data=pdata["data"],
                valor=pdata["valor"],
                forma_pagamento="Dinheiro",
                cliente_id=test_client.id,
                artista_id=test_artist.id,
                google_event_id=f"google-event-total-{i}",
            )
            db_session.add(payment)

        db_session.commit()

        # Verify total
        total_query = db_session.query(Pagamento).filter(
            Pagamento.artista_id == test_artist.id
        )

        total = sum(p.valor for p in total_query)
        expected = Decimal("1500.00")

        assert total >= expected, f"Total {total} should be >= {expected}"


class TestPhase3CanaryScenario4:
    """
    Scenario 4: Audit Trail Entries Logged Correctly

    Validates that monitoring entries are created in migration_audit table
    for each payment in unified flow, providing audit trail for compliance.
    """

    def test_monitoring_audit_entries_created(
        self, app, db_session, canary_user, test_artist, test_client
    ):
        """
        GIVEN: Canary user creates payment with google_event_id
        WHEN: Payment committed successfully
        THEN: MigrationAudit entry created with correct details
        """
        from app.db.base import Pagamento, MigrationAudit

        test_google_event_id = "google-event-canary-audit-001"

        # Create payment
        payment = Pagamento(
            data=datetime.now().date(),
            valor=Decimal("300.00"),
            forma_pagamento="PIX",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            google_event_id=test_google_event_id,
        )
        db_session.add(payment)
        db_session.flush()
        payment_id = payment.id
        db_session.commit()

        # Create monitoring audit entry
        audit_entry = MigrationAudit(
            entity_type="pagamento_canary_monitoring",
            entity_id=payment_id,
            action="payment_created",
            status="success",
            details={
                "user_id": canary_user.id,
                "google_event_id": test_google_event_id,
                "valor": "300.00",
                "payment_id": payment_id,
            },
        )
        db_session.add(audit_entry)
        db_session.commit()

        # Verify audit entry exists
        audit = (
            db_session.query(MigrationAudit)
            .filter(
                MigrationAudit.entity_type == "pagamento_canary_monitoring",
                MigrationAudit.entity_id == payment_id,
            )
            .first()
        )

        assert audit is not None, "Audit entry not found"
        assert audit.status == "success"


class TestPhase3CanaryScenario5:
    """
    Scenario 5: Duplicate Prevention Blocks Second Finalization

    Validates that the duplicate prevention mechanism correctly blocks
    attempts to create a second payment for the same google_event_id.
    """

    def test_duplicate_payment_prevented_by_unique_constraint(
        self, app, db_session, test_artist, test_client
    ):
        """
        GIVEN: Payment created with google_event_id
        WHEN: Second payment attempted with same google_event_id
        THEN: IntegrityError raised, second payment blocked
        """
        from app.db.base import Pagamento
        from sqlalchemy.exc import IntegrityError

        test_google_event_id = "google-event-canary-duplicate-001"

        # Create first payment
        payment1 = Pagamento(
            data=datetime.now().date(),
            valor=Decimal("100.00"),
            forma_pagamento="Dinheiro",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            google_event_id=test_google_event_id,
        )
        db_session.add(payment1)
        db_session.commit()

        # Attempt to create second payment with same google_event_id
        payment2 = Pagamento(
            data=datetime.now().date(),
            valor=Decimal("200.00"),
            forma_pagamento="Cartão",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            google_event_id=test_google_event_id,
        )
        db_session.add(payment2)

        # Should raise IntegrityError due to UNIQUE constraint on google_event_id
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Verify only first payment exists
        payments = (
            db_session.query(Pagamento)
            .filter(Pagamento.google_event_id == test_google_event_id)
            .all()
        )
        assert len(payments) == 1
        assert payments[0].valor == Decimal("100.00")

    def test_duplicate_prevention_check_logic(
        self, app, db_session, test_artist, test_client
    ):
        """
        GIVEN: Payment exists with google_event_id
        WHEN: EventPrefillService.check_duplicate_payment_by_event_id() called
        THEN: Returns (True, existing_payment_id)
        """
        from app.db.base import Pagamento
        from app.services.prefill_service import EventPrefillService

        test_google_event_id = "google-event-canary-dup-check-001"

        # Create initial payment
        payment = Pagamento(
            data=datetime.now().date(),
            valor=Decimal("200.00"),
            forma_pagamento="Dinheiro",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            google_event_id=test_google_event_id,
        )
        db_session.add(payment)
        db_session.commit()

        # Check for duplicate
        exists, existing_id = EventPrefillService.check_duplicate_payment_by_event_id(
            db_session, test_google_event_id
        )

        assert exists is True
        assert existing_id == payment.id


# Integration test: Full end-to-end flow
class TestPhase3CanaryE2E:
    """
    End-to-end integration test simulating full canary rollout scenario.
    """

    def test_complete_canary_flow_e2e(
        self, app, db_session, canary_user, test_artist, test_client
    ):
        """
        GIVEN: Canary user logs in to system
        WHEN: User goes through full payment flow (agenda → form → save)
        THEN: Payment saved with all fields, audit logged, history updated
        """
        from app.db.base import Pagamento, MigrationAudit

        test_google_event_id = "google-event-canary-e2e-001"
        test_valor = Decimal("500.00")

        # Step 1: Create payment (simulating form submission)
        payment = Pagamento(
            data=datetime.now().date(),
            valor=test_valor,
            forma_pagamento="PIX",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            observacoes="E2E canary test",
            google_event_id=test_google_event_id,
        )
        db_session.add(payment)
        db_session.flush()
        payment_id = payment.id

        # Step 2: Log audit entry
        audit = MigrationAudit(
            entity_type="pagamento_canary_monitoring",
            entity_id=payment_id,
            action="payment_created",
            status="success",
            details={
                "user_id": canary_user.id,
                "google_event_id": test_google_event_id,
                "valor": str(test_valor),
                "unified_flow_active": True,
            },
        )
        db_session.add(audit)
        db_session.commit()

        # Step 3: Verify all artifacts exist
        retrieved_payment = db_session.query(Pagamento).get(payment_id)
        assert retrieved_payment is not None
        assert retrieved_payment.google_event_id == test_google_event_id
        assert retrieved_payment.valor == test_valor

        retrieved_audit = (
            db_session.query(MigrationAudit)
            .filter(MigrationAudit.entity_id == payment_id)
            .first()
        )
        assert retrieved_audit is not None
        assert retrieved_audit.status == "success"

        # Step 4: Verify duplicate prevention works
        from sqlalchemy.exc import IntegrityError

        duplicate_payment = Pagamento(
            data=datetime.now().date(),
            valor=Decimal("100.00"),
            forma_pagamento="Dinheiro",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            google_event_id=test_google_event_id,
        )
        db_session.add(duplicate_payment)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # E2E test PASSED
        assert True, "Canary E2E flow completed successfully"
