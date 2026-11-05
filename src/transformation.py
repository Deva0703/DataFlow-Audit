
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd


def convert_price_to_cents(value):
    """Convert a decimal price into integer cents safely."""
    try:
        price = Decimal(str(value))

        if not price.is_finite() or price < 0:
            raise ValueError(f"Invalid unit price: {value}")

        cents = (price * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )

        return int(cents)

    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid unit price: {value}")


def transform_orders(customers, orders, order_items):
    """
    Combine customer, order and item data into order-level facts.

    Returns:
        DataFrame containing one row per order.
    """

    # Work on copies so source data is not modified.
    customers = customers.copy()
    orders = orders.copy()
    order_items = order_items.copy()

    # Check primary key uniqueness.
    if customers["customer_id"].duplicated().any():
        raise ValueError("Duplicate customer IDs found")

    if orders["order_id"].duplicated().any():
        raise ValueError("Duplicate order IDs found")

    if order_items["item_id"].duplicated().any():
        raise ValueError("Duplicate item IDs found")

    # Check foreign key relationships.
    if not orders["customer_id"].isin(customers["customer_id"]).all():
        raise ValueError("Orders contain invalid customer references")

    if not order_items["order_id"].isin(orders["order_id"]).all():
        raise ValueError("Order items contain invalid order references")

    # Validate quantities.
    quantity = pd.to_numeric(order_items["quantity"], errors="coerce")

    if (
        quantity.isna().any()
        or (quantity <= 0).any()
        or (quantity % 1 != 0).any()
    ):
        raise ValueError("Order quantities must be positive integers")

    order_items["quantity"] = quantity.astype("int64")

    # Convert prices to integer cents.
    order_items["unit_price_cents"] = (
        order_items["unit_price"].apply(convert_price_to_cents)
    )

    # Calculate each item's total value.
    order_items["line_total_cents"] = (
        order_items["quantity"] * order_items["unit_price_cents"]
    )

    # Aggregate item data at order level.
    item_summary = (
        order_items.groupby("order_id", as_index=False)
        .agg(
            total_items=("quantity", "sum"),
            total_amount_cents=("line_total_cents", "sum")
        )
    )

    # Join customer details to orders.
    order_facts = orders.merge(
        customers[["customer_id", "customer_name"]],
        on="customer_id",
        how="left",
        validate="many_to_one"
    )

    # Attach aggregated item metrics.
    order_facts = order_facts.merge(
        item_summary,
        on="order_id",
        how="left",
        validate="one_to_one"
    )

    # Preserve orders that have no items.
    order_facts["total_items"] = (
        order_facts["total_items"].fillna(0).astype("int64")
    )

    order_facts["total_amount_cents"] = (
        order_facts["total_amount_cents"].fillna(0).astype("int64")
    )

    # Select and order the target columns.
    order_facts = order_facts[
        [
            "order_id",
            "customer_id",
            "customer_name",
            "total_items",
            "total_amount_cents",
            "order_status",
            "order_date"
        ]
    ]

    return order_facts


if __name__ == "__main__":
    print("Data transformation module loaded successfully.")
