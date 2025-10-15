"""
Simple test to verify postgres_db fixture works correctly.
"""

from datetime import date, time
from decimal import Decimal

import pytest


@pytest.mark.postgres
def test_postgres_fixture_works(postgres_db):
    """Test that the postgres_db fixture creates a working database connection."""
    # Import models
    from app.db.base import Client, Sessao, User

    # Create test data
    client = Client(
        name="Fixture Test Client", jotform_submission_id="fixture_test_123"
    )
    postgres_db.add(client)
    postgres_db.flush()

    artist = User(
        name="Fixture Test Artist",
        email="fixture_artist@example.com",
        role="artist",
        active_flag=True,
    )
    postgres_db.add(artist)
    postgres_db.flush()

    # Create session with google_event_id
    session = Sessao(
        data=date(2025, 8, 30),
        valor=Decimal("100.00"),
        observacoes="Fixture test session",
        cliente_id=client.id,
        artista_id=artist.id,
        google_event_id="FIXTURE_TEST_123",
    )
    postgres_db.add(session)
    postgres_db.commit()

    # Query back to verify
    found_session = (
        postgres_db.query(Sessao).filter_by(google_event_id="FIXTURE_TEST_123").first()
    )
    assert found_session is not None
    assert found_session.google_event_id == "FIXTURE_TEST_123"
    assert found_session.observacoes == "Fixture test session"
    assert found_session.cliente_id == client.id
    assert found_session.artista_id == artist.id


@pytest.mark.postgres
def test_postgres_unique_constraint_on_google_event_id(postgres_db):
    """Test that the unique constraint on google_event_id works in PostgreSQL."""
    from app.db.base import Client, Sessao, User
    from sqlalchemy.exc import IntegrityError

    # Create test data
    client = Client(
        name="Constraint Test Client", jotform_submission_id="constraint_test_456"
    )
    postgres_db.add(client)
    postgres_db.flush()

    artist = User(
        name="Constraint Test Artist",
        email="constraint_artist@example.com",
        role="artist",
        active_flag=True,
    )
    postgres_db.add(artist)
    postgres_db.flush()

    # Create first session with google_event_id
    session1 = Sessao(
        data=date(2025, 8, 30),
        valor=Decimal("100.00"),
        observacoes="First session",
        cliente_id=client.id,
        artista_id=artist.id,
        google_event_id="CONSTRAINT_TEST_123",
    )
    postgres_db.add(session1)
    postgres_db.commit()

    # Try to create second session with same google_event_id - should fail
    session2 = Sessao(
        data=date(2025, 8, 31),
        valor=Decimal("150.00"),
        observacoes="Second session (should fail)",
        cliente_id=client.id,
        artista_id=artist.id,
        google_event_id="CONSTRAINT_TEST_123",  # Same ID as session1
    )
    postgres_db.add(session2)

    # This should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        postgres_db.commit()
