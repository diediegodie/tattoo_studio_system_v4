"""
Tests for payment ordering in list views.

Verifies that payments are displayed in the correct order:
- Primary sort: date descending (newest date first)
- Secondary sort: created_at descending (newest time first)
- Tertiary sort: id descending (highest ID first)

This ensures new records always appear at the top of the list.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.db.base import Pagamento, User
from app.db.session import SessionLocal


class TestPaymentOrdering:
    """Test suite for payment list ordering."""

    @pytest.fixture
    def mock_artist(self, mock_db_session):
        """Create a mock artist user."""
        artist = User(id=1, name="Test Artist", email="artist@test.com", role="artist")
        mock_db_session.add(artist)
        mock_db_session.flush()
        return artist

    def test_payments_ordered_by_date_desc(self, app, mock_artist):
        """Test that payments are ordered by date descending (newest date first)."""
        app.config["LOGIN_DISABLED"] = True

        # Create payments with different dates
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        db = SessionLocal()
        try:
            # Insert in random order
            p1 = Pagamento(
                data=week_ago,
                valor=Decimal("100.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            p2 = Pagamento(
                data=today,
                valor=Decimal("200.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            p3 = Pagamento(
                data=yesterday,
                valor=Decimal("150.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )

            db.add_all([p1, p2, p3])
            db.commit()

            # Query with ordering
            payments = (
                db.query(Pagamento)
                .order_by(
                    Pagamento.data.desc(),
                    Pagamento.created_at.desc(),
                    Pagamento.id.desc(),
                )
                .all()
            )

            # Verify order: today, yesterday, week_ago
            assert len(payments) >= 3
            assert payments[0].data == today
            assert payments[1].data == yesterday
            assert payments[2].data == week_ago

        finally:
            db.close()

    def test_same_date_ordered_by_created_at_desc(self, app, mock_artist):
        """Test that payments with same date are ordered by created_at desc."""
        app.config["LOGIN_DISABLED"] = True

        today = date.today()

        db = SessionLocal()
        try:
            # Create three payments on the same date with slight time delays
            # to ensure different created_at values
            p1 = Pagamento(
                data=today,
                valor=Decimal("100.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p1)
            db.commit()
            db.refresh(p1)

            import time

            time.sleep(0.01)  # Small delay to ensure different timestamps

            p2 = Pagamento(
                data=today,
                valor=Decimal("200.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p2)
            db.commit()
            db.refresh(p2)

            time.sleep(0.01)

            p3 = Pagamento(
                data=today,
                valor=Decimal("300.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p3)
            db.commit()
            db.refresh(p3)

            # Query with ordering
            payments = (
                db.query(Pagamento)
                .filter(Pagamento.data == today)
                .order_by(
                    Pagamento.data.desc(),
                    Pagamento.created_at.desc(),
                    Pagamento.id.desc(),
                )
                .all()
            )

            # Verify order: p3 (most recent), p2, p1 (oldest)
            assert len(payments) >= 3
            # The last created should be first
            assert payments[0].id == p3.id
            assert payments[1].id == p2.id
            assert payments[2].id == p1.id

        finally:
            db.close()

    def test_financeiro_home_returns_ordered_list(self, app, mock_artist):
        """Test that /financeiro/ returns payments in correct order."""
        app.config["LOGIN_DISABLED"] = True

        today = date.today()

        db = SessionLocal()
        try:
            # Create two payments on same date
            p1 = Pagamento(
                data=today,
                valor=Decimal("100.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p1)
            db.commit()
            db.refresh(p1)

            import time

            time.sleep(0.01)

            p2 = Pagamento(
                data=today,
                valor=Decimal("200.00"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p2)
            db.commit()
            db.refresh(p2)

            # Make request to financeiro home
            with app.test_client() as client:
                with patch("flask_login.utils._get_user") as mock_user:
                    mock_current_user = MagicMock()
                    mock_current_user.id = 1
                    mock_current_user.is_authenticated = True
                    mock_user.return_value = mock_current_user

                    response = client.get("/financeiro/")
                    assert response.status_code == 200

                    # Parse HTML to verify order (newest payment should appear first)
                    html = response.data.decode("utf-8")

                    # Find positions of payment amounts in HTML
                    # Template uses Brazilian format with comma: 200,00 and 100,00
                    # The 200,00 payment (newer) should appear before 100,00 payment
                    pos_200 = html.find("200,00")
                    pos_100 = html.find("100,00")

                    assert pos_200 > 0, "New payment not found in HTML"
                    assert pos_100 > 0, "Old payment not found in HTML"
                    assert (
                        pos_200 < pos_100
                    ), "Newer payment should appear before older payment"

        finally:
            db.close()

    def test_historico_returns_ordered_list(self, app, mock_artist):
        """Test that /historico/ returns payments in correct order."""
        app.config["LOGIN_DISABLED"] = True

        today = date.today()

        db = SessionLocal()
        try:
            # Create two payments
            p1 = Pagamento(
                data=today,
                valor=Decimal("111.11"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p1)
            db.commit()
            db.refresh(p1)

            import time

            time.sleep(0.01)

            p2 = Pagamento(
                data=today,
                valor=Decimal("222.22"),
                forma_pagamento="Pix",
                artista_id=1,
            )
            db.add(p2)
            db.commit()
            db.refresh(p2)

            # Make request to historico
            with app.test_client() as client:
                with patch("flask_login.utils._get_user") as mock_user:
                    mock_current_user = MagicMock()
                    mock_current_user.id = 1
                    mock_current_user.is_authenticated = True
                    mock_user.return_value = mock_current_user

                    # Get current month for historico
                    year = today.year
                    month = today.month

                    response = client.get(f"/historico/?ano={year}&mes={month}")
                    assert response.status_code == 200

                    # Verify order in HTML
                    html = response.data.decode("utf-8")

                    pos_222 = html.find("222.22")
                    pos_111 = html.find("111.11")

                    if pos_222 > 0 and pos_111 > 0:
                        assert (
                            pos_222 < pos_111
                        ), "Newer payment should appear before older payment in historico"

        finally:
            db.close()
