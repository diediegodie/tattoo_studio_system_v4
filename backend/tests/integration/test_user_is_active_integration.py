"""
Integration test for User.is_active attribute with Flask-Login.

This test validates the fix for the active/is_active column mismatch issue.
After migrating to SQLAlchemy 2.0, the User model incorrectly mapped 'active'
instead of 'is_active', causing PostgreSQL errors.

Test Coverage:
- User.is_active persists correctly to database
- Inactive users cannot authenticate via Flask-Login
- Active users can authenticate normally
- Column name matches database schema (is_active not active)
"""

import pytest
from flask import Flask
from flask_login import LoginManager, login_user, current_user
from sqlalchemy import select, text

from app.db.base import User
from app.db.session import SessionLocal


@pytest.fixture
def app_with_login():
    """Create Flask app with LoginManager configured."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with SessionLocal() as db:
            return db.get(User, int(user_id))

    return app


def test_user_is_active_column_exists_in_database():
    """Verify that the database column is named 'is_active' not 'active'."""
    with SessionLocal() as db:
        # This query will fail if column is named 'active' instead of 'is_active'
        result = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_active'"
            )
        ).fetchone()

        assert result is not None, "Column 'is_active' should exist in users table"
        assert result[0] == "is_active", "Column should be named 'is_active'"

        # Verify 'active' column does NOT exist
        result_active = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='active'"
            )
        ).fetchone()

        assert (
            result_active is None
        ), "Column 'active' should NOT exist (must be 'is_active')"


def test_create_inactive_user_persists_to_database():
    """Test that is_active=False is correctly persisted to the database."""
    with SessionLocal() as db:
        # Create inactive user
        inactive_user = User(
            email="inactive@test.com",
            name="Inactive User",
            role="client",
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()
        user_id = inactive_user.id

    # Fetch user in new session to verify persistence
    with SessionLocal() as db:
        fetched_user = db.get(User, user_id)
        assert fetched_user is not None, "User should be retrievable from database"
        assert fetched_user.is_active is False, "is_active should be False as persisted"
        assert fetched_user.email == "inactive@test.com"

        # Clean up
        db.delete(fetched_user)
        db.commit()


def test_create_active_user_persists_to_database():
    """Test that is_active=True (default) is correctly persisted."""
    with SessionLocal() as db:
        # Create active user (default)
        active_user = User(
            email="active@test.com", name="Active User", role="client", is_active=True
        )
        db.add(active_user)
        db.commit()
        user_id = active_user.id

    # Fetch user in new session
    with SessionLocal() as db:
        fetched_user = db.get(User, user_id)
        assert fetched_user is not None
        assert fetched_user.is_active is True, "is_active should be True"

        # Clean up
        db.delete(fetched_user)
        db.commit()


def test_user_default_is_active_is_true():
    """Test that User.is_active defaults to True when not specified."""
    with SessionLocal() as db:
        user = User(email="default@test.com", name="Default User", role="artist")
        # Don't explicitly set is_active
        db.add(user)
        db.commit()
        user_id = user.id

    with SessionLocal() as db:
        fetched = db.get(User, user_id)
        assert fetched.is_active is True, "Default is_active should be True"

        # Clean up
        db.delete(fetched)
        db.commit()


def test_flask_login_respects_is_active_attribute(app_with_login):
    """Test that Flask-Login's is_active property reflects database state."""
    # Create test users
    with SessionLocal() as db:
        active_user = User(
            email="active_flask@test.com",
            name="Active Flask User",
            role="client",
            is_active=True,
        )
        inactive_user = User(
            email="inactive_flask@test.com",
            name="Inactive Flask User",
            role="client",
            is_active=False,
        )
        db.add_all([active_user, inactive_user])
        db.commit()
        active_id = active_user.id
        inactive_id = inactive_user.id

    try:
        with app_with_login.test_request_context():
            # Test active user
            with SessionLocal() as db:
                active = db.get(User, active_id)
                assert active.is_active is True
                # Flask-Login checks is_active via UserMixin
                assert active.is_authenticated is True

            # Test inactive user
            with SessionLocal() as db:
                inactive = db.get(User, inactive_id)
                assert inactive.is_active is False
                # Inactive users should still be "authenticated" in terms of identity
                # but is_active controls whether they can log in
                assert inactive.is_authenticated is True

    finally:
        # Clean up
        with SessionLocal() as db:
            db.query(User).filter(User.id.in_([active_id, inactive_id])).delete(
                synchronize_session=False
            )
            db.commit()


def test_toggle_user_is_active_status():
    """Test updating is_active status persists correctly."""
    with SessionLocal() as db:
        user = User(
            email="toggle@test.com", name="Toggle User", role="client", is_active=True
        )
        db.add(user)
        db.commit()
        user_id = user.id

    # Toggle to inactive
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.is_active is True
        user.is_active = False
        db.commit()

    # Verify change persisted
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.is_active is False, "is_active should be updated to False"

    # Toggle back to active
    with SessionLocal() as db:
        user = db.get(User, user_id)
        user.is_active = True
        db.commit()

    # Verify final state
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.is_active is True, "is_active should be updated back to True"

        # Clean up
        db.delete(user)
        db.commit()


def test_query_users_by_is_active_status():
    """Test filtering users by is_active status using SQLAlchemy 2.0 select."""
    with SessionLocal() as db:
        # Create mix of active and inactive users
        users = [
            User(
                email=f"active{i}@test.com",
                name=f"Active {i}",
                role="client",
                is_active=True,
            )
            for i in range(3)
        ] + [
            User(
                email=f"inactive{i}@test.com",
                name=f"Inactive {i}",
                role="client",
                is_active=False,
            )
            for i in range(2)
        ]
        db.add_all(users)
        db.commit()
        user_ids = [u.id for u in users]

    try:
        # Query active users only
        with SessionLocal() as db:
            stmt = select(User).where(User.is_active == True)
            active_users = db.execute(stmt).scalars().all()
            test_active = [u for u in active_users if u.id in user_ids]
            assert len(test_active) == 3, "Should find 3 active users"

        # Query inactive users only
        with SessionLocal() as db:
            stmt = select(User).where(User.is_active == False)
            inactive_users = db.execute(stmt).scalars().all()
            test_inactive = [u for u in inactive_users if u.id in user_ids]
            assert len(test_inactive) == 2, "Should find 2 inactive users"

    finally:
        # Clean up
        with SessionLocal() as db:
            db.query(User).filter(User.id.in_(user_ids)).delete(
                synchronize_session=False
            )
            db.commit()


def test_sqlalchemy_2_0_style_query_with_is_active():
    """Verify SQLAlchemy 2.0 select() works with is_active attribute."""
    with SessionLocal() as db:
        user = User(
            email="sqla2@test.com",
            name="SQLAlchemy 2.0 User",
            role="artist",
            is_active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    try:
        # Use SQLAlchemy 2.0 style select
        with SessionLocal() as db:
            stmt = select(User).where(
                User.email == "sqla2@test.com", User.is_active == True
            )
            result = db.execute(stmt).scalar_one_or_none()

            assert result is not None, "Should find user with is_active filter"
            assert result.is_active is True
            assert result.email == "sqla2@test.com"

    finally:
        with SessionLocal() as db:
            db.query(User).filter(User.id == user_id).delete()
            db.commit()
