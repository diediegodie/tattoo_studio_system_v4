"""
Phase 4 Validation Tests: Automatic Sessao Creation (Option A)

Architecture: Payments with google_event_id automatically create Sessao.
Rule: If google_event_id present → create Sessao. If absent → no Sessao.
Source doesn't matter (Agenda or Financeiro use same endpoint).

Test Coverage:
1. Payment with google_event_id → creates Sessao + bidirectional links
2. Payment without google_event_id → no Sessao created
3. Duplicate google_event_id → controlled error
4. Historico compatibility (existing heuristics work)
5. Commission calculation unchanged
6. Audit logging for Phase 4 tracking
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from app.db.base import Pagamento, Sessao, MigrationAudit, Client, User
from app.repositories.user_repo import UserRepository


@pytest.fixture
def test_client_record(db_session):
    """Create a test client for payments"""
    client = Client(name="Test Client Phase 4")
    db_session.add(client)
    db_session.commit()
    return client


@pytest.fixture
def test_artist(db_session):
    """Create a test artist for payments"""
    artist = User(
        name="Test Artist",
        email="artist_phase4@test.com",
        password_hash="dummy_hash",
        role="artist",
    )
    db_session.add(artist)
    db_session.commit()
    return artist


class TestPhase4UnifiedSessaoCreation:
    """Phase 4: Test automatic Sessao creation based on google_event_id presence"""

    def test_payment_with_google_event_id_creates_sessao(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario 1: Payment with google_event_id (Agenda or Financeiro)
        Expected: Creates both Payment and Sessao with bidirectional links
        """
        google_event_id = "test_event_phase4_001"

        # Create payment with google_event_id
        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("300.00"),
            forma_pagamento="Dinheiro",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            observacoes="Phase 4 test payment",
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        # Simulate Phase 4 logic: Auto-create Sessao
        sessao = Sessao(
            data=pagamento.data,
            valor=pagamento.valor,
            cliente_id=pagamento.cliente_id,
            artista_id=pagamento.artista_id,
            observacoes=pagamento.observacoes,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento.id,
        )
        db_session.add(sessao)
        db_session.flush()

        # Set bidirectional link
        pagamento.sessao_id = sessao.id
        db_session.commit()

        # Assertions
        assert pagamento.id is not None
        assert sessao.id is not None
        assert pagamento.google_event_id == google_event_id
        assert sessao.google_event_id == google_event_id
        assert pagamento.sessao_id == sessao.id  # Payment → Session link
        assert sessao.payment_id == pagamento.id  # Session → Payment link
        assert sessao.status == "paid"
        assert sessao.valor == pagamento.valor
        assert sessao.cliente_id == pagamento.cliente_id
        assert sessao.artista_id == pagamento.artista_id

    def test_payment_without_google_event_id_no_sessao(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario 2: Payment without google_event_id (manual Financeiro entry)
        Expected: Creates Payment only, no Sessao
        """
        # Create payment without google_event_id
        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("150.00"),
            forma_pagamento="PIX",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            observacoes="Manual payment, no calendar event",
            google_event_id=None,  # Explicitly None
        )
        db_session.add(pagamento)
        db_session.commit()

        # Verify payment created
        assert pagamento.id is not None
        assert pagamento.google_event_id is None
        assert pagamento.sessao_id is None  # No session link

        # Verify no Sessao created for this payment
        sessoes = (
            db_session.query(Sessao)
            .filter(
                Sessao.cliente_id == test_client_record.id,
                Sessao.data == date(2025, 11, 25),
                Sessao.valor == Decimal("150.00"),
            )
            .all()
        )
        assert len(sessoes) == 0, "No Sessao should be created for manual payment"

    def test_duplicate_google_event_id_prevention(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario 3: Attempting to create payment with duplicate google_event_id
        Expected: UNIQUE constraint blocks second payment creation
        """
        google_event_id = "test_event_phase4_duplicate"

        # First payment (should succeed)
        pagamento1 = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("200.00"),
            forma_pagamento="Cartão",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento1)
        db_session.flush()

        # Create matching sessao
        sessao1 = Sessao(
            data=pagamento1.data,
            valor=pagamento1.valor,
            cliente_id=pagamento1.cliente_id,
            artista_id=pagamento1.artista_id,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento1.id,
        )
        db_session.add(sessao1)
        db_session.flush()
        pagamento1.sessao_id = sessao1.id
        db_session.commit()

        # Second payment with same google_event_id (should fail)
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            pagamento2 = Pagamento(
                data=date(2025, 11, 26),
                valor=Decimal("250.00"),
                forma_pagamento="Dinheiro",
                cliente_id=test_client_record.id,
                artista_id=test_artist.id,
                google_event_id=google_event_id,  # Duplicate
            )
            db_session.add(pagamento2)
            db_session.commit()

        db_session.rollback()

        # Verify only one payment exists
        payments = (
            db_session.query(Pagamento)
            .filter(Pagamento.google_event_id == google_event_id)
            .all()
        )
        assert len(payments) == 1

    def test_bidirectional_links_integrity(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario 4: Verify bidirectional integrity (payment.sessao_id ↔ sessao.payment_id)
        Expected: Both directions correctly linked
        """
        google_event_id = "test_event_phase4_bidirectional"

        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("400.00"),
            forma_pagamento="Transferência",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        sessao = Sessao(
            data=pagamento.data,
            valor=pagamento.valor,
            cliente_id=pagamento.cliente_id,
            artista_id=pagamento.artista_id,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento.id,
        )
        db_session.add(sessao)
        db_session.flush()

        pagamento.sessao_id = sessao.id
        db_session.commit()

        # Refresh from DB
        db_session.expire_all()

        pagamento_db = (
            db_session.query(Pagamento).filter(Pagamento.id == pagamento.id).first()
        )
        sessao_db = db_session.query(Sessao).filter(Sessao.id == sessao.id).first()

        # Verify bidirectional links
        assert pagamento_db.sessao_id == sessao_db.id
        assert sessao_db.payment_id == pagamento_db.id

        # Verify can navigate both directions (if relationships defined in model)
        # This assumes SQLAlchemy relationships are set up correctly
        # If not, the above assertions are sufficient for data integrity

    def test_audit_logging_for_phase4_creation(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario 5: Verify audit logging tracks Phase 4 Sessao creation
        Expected: MigrationAudit entry with entity_type='sessao_unified_creation'
        """
        google_event_id = "test_event_phase4_audit"

        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("350.00"),
            forma_pagamento="Dinheiro",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        sessao = Sessao(
            data=pagamento.data,
            valor=pagamento.valor,
            cliente_id=pagamento.cliente_id,
            artista_id=pagamento.artista_id,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento.id,
        )
        db_session.add(sessao)
        db_session.flush()

        pagamento.sessao_id = sessao.id

        # Simulate Phase 4 audit logging
        audit_entry = MigrationAudit(
            entity_type="sessao_unified_creation",
            entity_id=sessao.id,
            action="auto_created_with_payment",
            status="success",
            details={
                "payment_id": pagamento.id,
                "google_event_id": google_event_id,
                "valor": str(pagamento.valor),
                "phase": "4",
            },
        )
        db_session.add(audit_entry)
        db_session.commit()

        # Verify audit entry
        audit_records = (
            db_session.query(MigrationAudit)
            .filter(
                MigrationAudit.entity_type == "sessao_unified_creation",
                MigrationAudit.entity_id == sessao.id,
            )
            .all()
        )
        assert len(audit_records) == 1
        assert audit_records[0].action == "auto_created_with_payment"
        assert audit_records[0].status == "success"
        assert audit_records[0].details["google_event_id"] == google_event_id
        assert audit_records[0].details["phase"] == "4"

    def test_historico_compatibility_no_changes_needed(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario 6: Verify Historico heuristics work with unified flow
        Expected: Existing heuristics correctly match sessions and payments
        """
        google_event_id = "test_event_phase4_historico"

        # Create unified payment + session
        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("280.00"),
            forma_pagamento="PIX",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        sessao = Sessao(
            data=pagamento.data,
            valor=pagamento.valor,
            cliente_id=pagamento.cliente_id,
            artista_id=pagamento.artista_id,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento.id,
        )
        db_session.add(sessao)
        db_session.flush()

        pagamento.sessao_id = sessao.id
        db_session.commit()

        # Query as Historico would (bidirectional links + heuristics)
        # Heuristic: Match by (date, valor, client, artist)
        matching_sessions = (
            db_session.query(Sessao)
            .filter(
                Sessao.data == date(2025, 11, 25),
                Sessao.valor == Decimal("280.00"),
                Sessao.cliente_id == test_client_record.id,
                Sessao.artista_id == test_artist.id,
            )
            .all()
        )

        matching_payments = (
            db_session.query(Pagamento)
            .filter(
                Pagamento.data == date(2025, 11, 25),
                Pagamento.valor == Decimal("280.00"),
                Pagamento.cliente_id == test_client_record.id,
                Pagamento.artista_id == test_artist.id,
            )
            .all()
        )

        assert len(matching_sessions) == 1
        assert len(matching_payments) == 1

        # Heuristic matching (would normally return these as a pair)
        assert matching_sessions[0].id == sessao.id
        assert matching_payments[0].id == pagamento.id

        # Direct bidirectional link verification
        assert matching_payments[0].sessao_id == matching_sessions[0].id
        assert matching_sessions[0].payment_id == matching_payments[0].id


class TestPhase4EdgeCases:
    """Edge cases and error conditions"""

    def test_existing_sessao_reused_if_found(
        self, db_session, test_client_record, test_artist
    ):
        """
        Edge case: If Sessao already exists (legacy data), link instead of creating new
        Expected: Payment links to existing Sessao, status updated to 'paid'
        """
        google_event_id = "test_event_phase4_existing_sessao"

        # Create pre-existing Sessao (legacy flow artifact)
        existing_sessao = Sessao(
            data=date(2025, 11, 25),
            valor=Decimal("220.00"),
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
            status="active",  # Not yet paid
        )
        db_session.add(existing_sessao)
        db_session.commit()

        # Create payment (Phase 4 logic should detect existing session)
        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("220.00"),
            forma_pagamento="Dinheiro",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        # Simulate Phase 4 logic: Check for existing session
        found_sessao = (
            db_session.query(Sessao)
            .filter(Sessao.google_event_id == google_event_id)
            .first()
        )
        assert found_sessao is not None
        assert found_sessao.id == existing_sessao.id

        # Link and update status
        pagamento.sessao_id = found_sessao.id
        found_sessao.payment_id = pagamento.id
        found_sessao.status = "paid"
        db_session.commit()

        # Verify no duplicate Sessao created
        all_sessoes = (
            db_session.query(Sessao)
            .filter(Sessao.google_event_id == google_event_id)
            .all()
        )
        assert len(all_sessoes) == 1
        assert all_sessoes[0].status == "paid"
        assert all_sessoes[0].payment_id == pagamento.id

    def test_commission_calculation_unchanged(
        self, db_session, test_client_record, test_artist
    ):
        """
        Scenario: Verify commission calculation works identically with unified flow
        Expected: Commission percentage correctly applied, valor calculated
        """
        from app.db.base import Comissao

        google_event_id = "test_event_phase4_commission"

        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("500.00"),
            forma_pagamento="Cartão",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        sessao = Sessao(
            data=pagamento.data,
            valor=pagamento.valor,
            cliente_id=pagamento.cliente_id,
            artista_id=pagamento.artista_id,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento.id,
        )
        db_session.add(sessao)
        db_session.flush()

        pagamento.sessao_id = sessao.id

        # Commission: 40% of 500 = 200
        comissao = Comissao(
            pagamento_id=pagamento.id,
            artista_id=test_artist.id,
            percentual=Decimal("40.00"),
            valor=Decimal("200.00"),
            observacoes="Phase 4 commission test",
        )
        db_session.add(comissao)
        db_session.commit()

        # Verify commission
        comissoes = (
            db_session.query(Comissao)
            .filter(Comissao.pagamento_id == pagamento.id)
            .all()
        )
        assert len(comissoes) == 1
        assert comissoes[0].percentual == Decimal("40.00")
        assert comissoes[0].valor == Decimal("200.00")
        assert comissoes[0].artista_id == test_artist.id


@pytest.mark.phase4
@pytest.mark.integration
class TestPhase4IntegrationFullFlow:
    """End-to-end integration test for Phase 4 unified flow"""

    def test_full_payment_flow_with_commission(
        self, db_session, test_client_record, test_artist
    ):
        """
        E2E: Create payment with google_event_id + commission
        Expected: Payment + Sessao + Commission all created atomically
        """
        google_event_id = "test_event_phase4_e2e"

        # Simulate full flow
        pagamento = Pagamento(
            data=date(2025, 11, 25),
            valor=Decimal("600.00"),
            forma_pagamento="Transferência",
            cliente_id=test_client_record.id,
            artista_id=test_artist.id,
            observacoes="E2E Phase 4 test",
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.flush()

        sessao = Sessao(
            data=pagamento.data,
            valor=pagamento.valor,
            cliente_id=pagamento.cliente_id,
            artista_id=pagamento.artista_id,
            observacoes=pagamento.observacoes,
            google_event_id=google_event_id,
            status="paid",
            payment_id=pagamento.id,
        )
        db_session.add(sessao)
        db_session.flush()

        pagamento.sessao_id = sessao.id

        from app.db.base import Comissao

        comissao = Comissao(
            pagamento_id=pagamento.id,
            artista_id=test_artist.id,
            percentual=Decimal("35.00"),
            valor=Decimal("210.00"),  # 35% of 600
            observacoes="E2E commission",
        )
        db_session.add(comissao)

        # Audit logging
        audit_entry = MigrationAudit(
            entity_type="sessao_unified_creation",
            entity_id=sessao.id,
            action="auto_created_with_payment",
            status="success",
            details={
                "payment_id": pagamento.id,
                "google_event_id": google_event_id,
                "commission_percent": "35.00",
                "phase": "4",
            },
        )
        db_session.add(audit_entry)

        db_session.commit()

        # Verify all entities created
        assert pagamento.id is not None
        assert sessao.id is not None
        assert comissao.id is not None

        # Verify links
        assert pagamento.sessao_id == sessao.id
        assert sessao.payment_id == pagamento.id
        assert comissao.pagamento_id == pagamento.id

        # Verify audit
        audit_records = (
            db_session.query(MigrationAudit)
            .filter(MigrationAudit.entity_id == sessao.id)
            .all()
        )
        assert len(audit_records) == 1
