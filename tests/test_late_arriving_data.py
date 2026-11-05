
import pandas as pd

from src import database, pipeline


def test_late_arriving_order_does_not_overwrite_newer_record(
    tmp_path,
    monkeypatch
):
    # Use an isolated test database.
    test_db = tmp_path / "late_arrival_test.db"

    monkeypatch.setattr(
        database,
        "ACTIVE_DB_PATH",
        test_db
    )

    database.initialize_database()

    # Minimal valid source records.
    customers = pd.DataFrame([
        {
            "customer_id": "CUST001",
            "customer_name": "Test Customer",
            "email": "test@example.com",
            "registration_date": "2026-01-01"
        }
    ])

    order_items = pd.DataFrame([
        {
            "item_id": "ITEM001",
            "order_id": "ORD001",
            "product_id": "PROD001",
            "product_name": "Test Product",
            "quantity": 2,
            "unit_price": 100.00
        }
    ])

    def make_validated_orders(status, updated_at):
        return {
            "customers": {"valid": customers},
            "orders": {
                "valid": pd.DataFrame([
                    {
                        "order_id": "ORD001",
                        "customer_id": "CUST001",
                        "order_date": "2026-11-01T10:00:00+00:00",
                        "order_status": status,
                        "updated_at": updated_at
                    }
                ])
            },
            "order_items": {"valid": order_items}
        }

    # First load: newer record already exists.
    pipeline.load_source_tables(
        make_validated_orders(
            "shipped",
            "2026-11-04T10:00:00+00:00"
        )
    )

    # Second load: an older update arrives late.
    pipeline.load_source_tables(
        make_validated_orders(
            "processing",
            "2026-11-02T10:00:00+00:00"
        )
    )

    with database.get_connection() as connection:
        order = connection.execute(
            """
            SELECT order_status, updated_at
            FROM orders
            WHERE order_id = ?
            """,
            ("ORD001",)
        ).fetchone()

    # Older data must not overwrite the newer record.
    assert order["order_status"] == "shipped"
    assert order["updated_at"] == "2026-11-04T10:00:00+00:00"

    # Third load: a genuinely newer update arrives.
    pipeline.load_source_tables(
        make_validated_orders(
            "delivered",
            "2026-11-05T10:00:00+00:00"
        )
    )

    with database.get_connection() as connection:
        order = connection.execute(
            """
            SELECT order_status, updated_at
            FROM orders
            WHERE order_id = ?
            """,
            ("ORD001",)
        ).fetchone()

    # Newer data should update the existing record.
    assert order["order_status"] == "delivered"
    assert order["updated_at"] == "2026-11-05T10:00:00+00:00"
