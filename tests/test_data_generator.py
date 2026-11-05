
import pandas as pd

from src.data_generator import OUTPUT_DIR


def test_all_csv_files_exist():

    assert (OUTPUT_DIR / "customers.csv").exists()
    assert (OUTPUT_DIR / "orders.csv").exists()
    assert (OUTPUT_DIR / "order_items.csv").exists()


def test_expected_record_counts():

    customers = pd.read_csv(OUTPUT_DIR / "customers.csv")
    orders = pd.read_csv(OUTPUT_DIR / "orders.csv")
    items = pd.read_csv(OUTPUT_DIR / "order_items.csv")

    assert len(customers) == 100
    assert len(orders) == 500
    assert len(items) >= 500


def test_primary_keys_are_unique():

    customers = pd.read_csv(OUTPUT_DIR / "customers.csv")
    orders = pd.read_csv(OUTPUT_DIR / "orders.csv")
    items = pd.read_csv(OUTPUT_DIR / "order_items.csv")

    assert customers["customer_id"].is_unique
    assert orders["order_id"].is_unique
    assert items["item_id"].is_unique


def test_foreign_keys_are_valid():

    customers = pd.read_csv(OUTPUT_DIR / "customers.csv")
    orders = pd.read_csv(OUTPUT_DIR / "orders.csv")
    items = pd.read_csv(OUTPUT_DIR / "order_items.csv")

    valid_customer_ids = set(customers["customer_id"])
    valid_order_ids = set(orders["order_id"])

    assert set(orders["customer_id"]).issubset(
        valid_customer_ids
    )

    assert set(items["order_id"]).issubset(
        valid_order_ids
    )


def test_required_columns_exist():

    customers = pd.read_csv(OUTPUT_DIR / "customers.csv")
    orders = pd.read_csv(OUTPUT_DIR / "orders.csv")
    items = pd.read_csv(OUTPUT_DIR / "order_items.csv")

    assert set([
        "customer_id",
        "customer_name",
        "email",
        "registration_date"
    ]).issubset(customers.columns)

    assert set([
        "order_id",
        "customer_id",
        "order_date",
        "order_status",
        "updated_at"
    ]).issubset(orders.columns)

    assert set([
        "item_id",
        "order_id",
        "product_id",
        "product_name",
        "quantity",
        "unit_price"
    ]).issubset(items.columns)
