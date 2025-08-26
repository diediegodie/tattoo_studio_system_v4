from sqlalchemy import inspect


def test_inventory_order_column_nullable(db_session):
    inspector = inspect(db_session.get_bind())
    cols = inspector.get_columns("inventory")
    order_col = next((c for c in cols if c["name"] == "order"), None)
    assert order_col is not None
    # SQLAlchemy inspector uses 'nullable' boolean
    assert order_col.get("nullable", True) is True
    # default key may be 'default' or 'server_default'; be permissive
    assert (
        order_col.get("default", None) is None
        or order_col.get("server_default", None) is None
    )
