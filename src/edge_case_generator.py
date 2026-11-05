
from pathlib import Path

import pandas as pd


# -----------------------------------------
# PROJECT PATHS
# -----------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

SAMPLE_DIR = BASE_DIR / "data" / "sample"
OUTPUT_DIR = BASE_DIR / "data" / "input" / "edge_cases"


def generate_edge_cases():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating data-quality test scenarios...")

    # Load clean datasets
    customers = pd.read_csv(SAMPLE_DIR / "customers.csv")
    orders = pd.read_csv(SAMPLE_DIR / "orders.csv")
    items = pd.read_csv(SAMPLE_DIR / "order_items.csv")

    # -------------------------------------
    # 1. CUSTOMER EDGE CASES
    # -------------------------------------

    customer_bad = customers.head(5).copy()

    # Missing required customer name
    missing_name = customer_bad.iloc[[0]].copy()
    missing_name.loc[:, "customer_name"] = pd.NA

    # Duplicate primary key
    duplicate_customer = customer_bad.iloc[[1]].copy()

    customer_edge = pd.concat(
        [customer_bad, missing_name, duplicate_customer],
        ignore_index=True
    )

    customer_edge.to_csv(
        OUTPUT_DIR / "customers_edge_cases.csv",
        index=False
    )

    # -------------------------------------
    # 2. ORDER EDGE CASES
    # -------------------------------------

    order_bad = orders.head(5).copy()

    # Invalid customer foreign key
    invalid_customer = order_bad.iloc[[0]].copy()
    invalid_customer.loc[:, "order_id"] = "ORD_INVALID_FK"
    invalid_customer.loc[:, "customer_id"] = "CUST_UNKNOWN"

    # Missing required customer ID
    missing_customer = order_bad.iloc[[1]].copy()
    missing_customer.loc[:, "order_id"] = "ORD_MISSING_FK"
    missing_customer.loc[:, "customer_id"] = pd.NA

    # Duplicate order ID
    duplicate_order = order_bad.iloc[[2]].copy()

    # Late-arriving order: old event date, new arrival
    late_order = order_bad.iloc[[3]].copy()
    late_order.loc[:, "order_id"] = "ORD_LATE_001"
    late_order.loc[:, "order_date"] = "2025-01-05T10:00:00+00:00"
    late_order.loc[:, "updated_at"] = "2026-11-04T00:00:00+00:00"

    order_edge = pd.concat(
        [
            order_bad,
            invalid_customer,
            missing_customer,
            duplicate_order,
            late_order
        ],
        ignore_index=True
    )

    order_edge.to_csv(
        OUTPUT_DIR / "orders_edge_cases.csv",
        index=False
    )

    # -------------------------------------
    # 3. ORDER ITEM EDGE CASES
    # -------------------------------------

    item_bad = items.head(5).copy()

    # Invalid quantity
    invalid_quantity = item_bad.iloc[[0]].copy()
    invalid_quantity.loc[:, "item_id"] = "ITEM_BAD_QTY"
    invalid_quantity.loc[:, "quantity"] = -5

    # Invalid price
    invalid_price = item_bad.iloc[[1]].copy()
    invalid_price.loc[:, "item_id"] = "ITEM_BAD_PRICE"
    invalid_price.loc[:, "unit_price"] = -100.00

    # Invalid order reference
    invalid_order = item_bad.iloc[[2]].copy()
    invalid_order.loc[:, "item_id"] = "ITEM_BAD_FK"
    invalid_order.loc[:, "order_id"] = "ORD_UNKNOWN"

    # Duplicate item primary key
    duplicate_item = item_bad.iloc[[3]].copy()

    item_edge = pd.concat(
        [
            item_bad,
            invalid_quantity,
            invalid_price,
            invalid_order,
            duplicate_item
        ],
        ignore_index=True
    )

    item_edge.to_csv(
        OUTPUT_DIR / "order_items_edge_cases.csv",
        index=False
    )

    # -------------------------------------
    # 4. UNEXPECTED SCHEMA
    # -------------------------------------

    schema_change = orders.head(5).copy()

    schema_change["unexpected_column"] = "NEW_FIELD"

    schema_change.to_csv(
        OUTPUT_DIR / "unexpected_schema.csv",
        index=False
    )

    # -------------------------------------
    # 5. MALFORMED CSV
    # -------------------------------------

    malformed_content = (
        'order_id,customer_id,order_date\n'
        'ORD_BAD,CUST001,"2025-01-01\n'
        'ORD002,CUST002,2025-02-01\n'
    )

    with open(
        OUTPUT_DIR / "malformed_input.csv",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(malformed_content)

    # -------------------------------------
    # SUMMARY
    # -------------------------------------

    print("\nEdge-case generation completed!")

    for file_path in OUTPUT_DIR.iterdir():
        if file_path.is_file():
            print(f"Created: {file_path.name}")

    print(f"\nOutput directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_edge_cases()
