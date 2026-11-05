import pandas as pd
import pytest

from src.validation import validate_schema, validate_records


def test_valid_customer_record():
    df = pd.DataFrame([{
        "customer_id": "CUST001",
        "customer_name": "Arun Kumar",
        "email": "arun@example.com",
        "registration_date": "2025-01-10"
    }])

    valid, rejected = validate_records(df, "customers")

    assert len(valid) == 1
    assert len(rejected) == 0


def test_missing_required_customer_name():
    df = pd.DataFrame([{
        "customer_id": "CUST001",
        "customer_name": "",
        "email": "arun@example.com",
        "registration_date": "2025-01-10"
    }])

    valid, rejected = validate_records(df, "customers")

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "Missing required field: customer_name" in rejected.iloc[0]["rejection_reason"]


def test_duplicate_customer_id():
    df = pd.DataFrame([
        {
            "customer_id": "CUST001",
            "customer_name": "Arun",
            "email": "arun@example.com",
            "registration_date": "2025-01-10"
        },
        {
            "customer_id": "CUST001",
            "customer_name": "Kumar",
            "email": "kumar@example.com",
            "registration_date": "2025-01-11"
        }
    ])

    valid, rejected = validate_records(df, "customers")

    assert len(valid) == 1
    assert len(rejected) == 1
    assert "Duplicate primary key" in rejected.iloc[0]["rejection_reason"]


def test_invalid_email():
    df = pd.DataFrame([{
        "customer_id": "CUST001",
        "customer_name": "Arun",
        "email": "invalid-email",
        "registration_date": "2025-01-10"
    }])

    valid, rejected = validate_records(df, "customers")

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "Invalid email format" in rejected.iloc[0]["rejection_reason"]


def test_invalid_customer_foreign_key():
    df = pd.DataFrame([{
        "order_id": "ORD001",
        "customer_id": "CUST_UNKNOWN",
        "order_date": "2025-01-10",
        "order_status": "placed",
        "updated_at": "2025-01-10"
    }])

    valid, rejected = validate_records(
        df,
        "orders",
        valid_reference_ids={"CUST001", "CUST002"}
    )

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "Invalid customer foreign key" in rejected.iloc[0]["rejection_reason"]


def test_invalid_order_quantity():
    df = pd.DataFrame([{
        "item_id": "ITEM001",
        "order_id": "ORD001",
        "product_id": "PROD001",
        "product_name": "Laptop",
        "quantity": -2,
        "unit_price": "500.00"
    }])

    valid, rejected = validate_records(df, "order_items")

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "Quantity must be a positive integer" in rejected.iloc[0]["rejection_reason"]


def test_invalid_order_item_foreign_key():
    df = pd.DataFrame([{
        "item_id": "ITEM001",
        "order_id": "ORD_UNKNOWN",
        "product_id": "PROD001",
        "product_name": "Laptop",
        "quantity": 2,
        "unit_price": "500.00"
    }])

    valid, rejected = validate_records(
        df,
        "order_items",
        valid_reference_ids={"ORD001", "ORD002"}
    )

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "Invalid order foreign key" in rejected.iloc[0]["rejection_reason"]


def test_schema_drift_with_unexpected_column():
    df = pd.DataFrame([{
        "customer_id": "CUST001",
        "customer_name": "Arun",
        "email": "arun@example.com",
        "registration_date": "2025-01-10",
        "unexpected_column": "unexpected"
    }])

    with pytest.raises(ValueError, match="Unexpected columns"):
        validate_schema(df, "customers")


def test_empty_batch():
    df = pd.DataFrame(columns=[
        "customer_id",
        "customer_name",
        "email",
        "registration_date"
    ])

    valid, rejected = validate_records(df, "customers")

    assert len(valid) == 0
    assert len(rejected) == 0