
import pandas as pd
import pytest

from src.transformation import (
    convert_price_to_cents,
    transform_orders
)


@pytest.fixture
def sample_data():
    customers = pd.DataFrame([
        {
            "customer_id": "CUST001",
            "customer_name": "Arun"
        },
        {
            "customer_id": "CUST002",
            "customer_name": "Kumar"
        }
    ])

    orders = pd.DataFrame([
        {
            "order_id": "ORD001",
            "customer_id": "CUST001",
            "order_status": "placed",
            "order_date": "2026-01-10"
        },
        {
            "order_id": "ORD002",
            "customer_id": "CUST002",
            "order_status": "shipped",
            "order_date": "2026-01-11"
        }
    ])

    order_items = pd.DataFrame([
        {
            "item_id": "ITEM001",
            "order_id": "ORD001",
            "quantity": 2,
            "unit_price": "25000.00"
        },
        {
            "item_id": "ITEM002",
            "order_id": "ORD001",
            "quantity": 1,
            "unit_price": "1000.00"
        },
        {
            "item_id": "ITEM003",
            "order_id": "ORD002",
            "quantity": 3,
            "unit_price": "500.00"
        }
    ])

    return customers, orders, order_items


def test_price_conversion():
    assert convert_price_to_cents("25000.00") == 2500000
    assert convert_price_to_cents("10.50") == 1050
    assert convert_price_to_cents("0.99") == 99


def test_invalid_price():
    with pytest.raises(ValueError):
        convert_price_to_cents("-100.00")

    with pytest.raises(ValueError):
        convert_price_to_cents("invalid")


def test_order_transformation(sample_data):
    customers, orders, order_items = sample_data

    result = transform_orders(customers, orders, order_items)

    assert len(result) == 2
    assert result["order_id"].is_unique


def test_total_items_calculation(sample_data):
    customers, orders, order_items = sample_data

    result = transform_orders(customers, orders, order_items)

    ord001 = result[result["order_id"] == "ORD001"].iloc[0]

    assert ord001["total_items"] == 3


def test_total_amount_calculation(sample_data):
    customers, orders, order_items = sample_data

    result = transform_orders(customers, orders, order_items)

    ord001 = result[result["order_id"] == "ORD001"].iloc[0]

    # (2 * 25000) + (1 * 1000) = 51000
    # Stored in cents = 5,100,000
    assert ord001["total_amount_cents"] == 5100000


def test_invalid_customer_reference(sample_data):
    customers, orders, order_items = sample_data

    orders.loc[0, "customer_id"] = "CUST_UNKNOWN"

    with pytest.raises(ValueError, match="invalid customer references"):
        transform_orders(customers, orders, order_items)


def test_invalid_order_reference(sample_data):
    customers, orders, order_items = sample_data

    order_items.loc[0, "order_id"] = "ORD_UNKNOWN"

    with pytest.raises(ValueError, match="invalid order references"):
        transform_orders(customers, orders, order_items)


def test_duplicate_order_id(sample_data):
    customers, orders, order_items = sample_data

    orders = pd.concat([orders, orders.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate order IDs"):
        transform_orders(customers, orders, order_items)



def test_order_without_items(sample_data):
    customers, orders, order_items = sample_data

    # Add a new order without adding any corresponding order items.
    new_order = pd.DataFrame([{
        "order_id": "ORD003",
        "customer_id": "CUST001",
        "order_status": "placed",
        "order_date": "2026-01-12"
    }])

    orders = pd.concat([orders, new_order], ignore_index=True)

    result = transform_orders(customers, orders, order_items)

    ord003 = result[result["order_id"] == "ORD003"].iloc[0]

    assert ord003["total_items"] == 0
    assert ord003["total_amount_cents"] == 0
