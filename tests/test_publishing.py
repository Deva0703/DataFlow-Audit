
import sqlite3

import pandas as pd
import pytest

from src.database import initialize_database
from src.publishing import publish_order_facts



@pytest.fixture
def test_database(tmp_path):
    db_path = tmp_path / "test_audit.db"
    initialize_database(db_path)

    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO customers (
                customer_id,
                customer_name,
                email,
                registration_date
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                ("CUST001", "Arun", "arun@example.com", "2025-01-01"),
                ("CUST002", "Kumar", "kumar@example.com", "2025-01-02")
            ]
        )

        connection.executemany(
            """
            INSERT INTO orders (
                order_id,
                customer_id,
                order_date,
                order_status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("ORD001", "CUST001", "2026-01-10", "placed", "2026-01-10"),
                ("ORD002", "CUST002", "2026-01-11", "shipped", "2026-01-11")
            ]
        )

    return db_path



@pytest.fixture
def sample_facts():
    return pd.DataFrame([
        {
            "order_id": "ORD001",
            "customer_id": "CUST001",
            "customer_name": "Arun",
            "total_items": 3,
            "total_amount_cents": 5100000,
            "order_status": "placed",
            "order_date": "2026-01-10"
        },
        {
            "order_id": "ORD002",
            "customer_id": "CUST002",
            "customer_name": "Kumar",
            "total_items": 2,
            "total_amount_cents": 250000,
            "order_status": "shipped",
            "order_date": "2026-01-11"
        }
    ])


def test_insert_new_order_facts(test_database, sample_facts):
    result = publish_order_facts(sample_facts, test_database)

    assert result["total_rows"] == 2
    assert result["inserted_rows"] == 2
    assert result["updated_rows"] == 0
    assert result["published_rows"] == 2

    with sqlite3.connect(test_database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM order_facts"
        ).fetchone()[0]

    assert count == 2


def test_update_existing_order(test_database, sample_facts):
    publish_order_facts(sample_facts, test_database)

    updated_facts = sample_facts.iloc[[0]].copy()
    updated_facts.loc[:, "total_items"] = 5
    updated_facts.loc[:, "total_amount_cents"] = 7500000

    result = publish_order_facts(updated_facts, test_database)

    assert result["inserted_rows"] == 0
    assert result["updated_rows"] == 1

    with sqlite3.connect(test_database) as connection:
        row = connection.execute(
            """
            SELECT total_items, total_amount_cents
            FROM order_facts
            WHERE order_id = ?
            """,
            ("ORD001",)
        ).fetchone()

    assert row == (5, 7500000)


def test_safe_rerun_does_not_create_duplicates(test_database, sample_facts):
    first_result = publish_order_facts(sample_facts, test_database)
    second_result = publish_order_facts(sample_facts, test_database)

    assert first_result["inserted_rows"] == 2
    assert second_result["inserted_rows"] == 0
    assert second_result["updated_rows"] == 2

    with sqlite3.connect(test_database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM order_facts"
        ).fetchone()[0]

    assert count == 2


def test_duplicate_order_ids_are_rejected(test_database, sample_facts):
    duplicate_facts = pd.concat(
        [sample_facts, sample_facts.iloc[[0]]],
        ignore_index=True
    )

    with pytest.raises(ValueError, match="Duplicate order IDs"):
        publish_order_facts(duplicate_facts, test_database)


def test_negative_total_amount_is_rejected(test_database, sample_facts):
    invalid_facts = sample_facts.copy()
    invalid_facts.loc[0, "total_amount_cents"] = -100

    with pytest.raises(ValueError, match="Total amount cannot be negative"):
        publish_order_facts(invalid_facts, test_database)


def test_missing_order_id_is_rejected(test_database, sample_facts):
    invalid_facts = sample_facts.copy()
    invalid_facts.loc[0, "order_id"] = None

    with pytest.raises(ValueError, match="Order IDs cannot be missing"):
        publish_order_facts(invalid_facts, test_database)



def test_database_rolls_back_failed_publish(test_database, sample_facts):
    # First record is valid, but the second order does not exist.
    invalid_facts = sample_facts.copy()
    invalid_facts.loc[1, "order_id"] = "ORD_UNKNOWN"

    with pytest.raises(sqlite3.IntegrityError):
        publish_order_facts(invalid_facts, test_database)

    # The first insert must also be rolled back.
    with sqlite3.connect(test_database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM order_facts"
        ).fetchone()[0]

    assert count == 0



def test_missing_database_raises_error(tmp_path, sample_facts):
    missing_db = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError):
        publish_order_facts(sample_facts, missing_db)
