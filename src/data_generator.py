
import random
from pathlib import Path
from datetime import datetime, timezone, date

import numpy as np
import pandas as pd
from faker import Faker


# -----------------------------------------
# PROJECT CONFIGURATION
# -----------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "sample"

SEED = 42

fake = Faker("en_IN")
fake.seed_instance(SEED)

rng = np.random.default_rng(SEED)
random.seed(SEED)


# -----------------------------------------
# PRODUCT MASTER DATA
# -----------------------------------------

PRODUCTS = [
    ("PROD001", "Laptop"),
    ("PROD002", "Smartphone"),
    ("PROD003", "Headphones"),
    ("PROD004", "Keyboard"),
    ("PROD005", "Mouse"),
    ("PROD006", "Monitor"),
    ("PROD007", "Smartwatch"),
    ("PROD008", "Tablet")
]

ORDER_STATUSES = [
    "placed",
    "processing",
    "shipped",
    "delivered",
    "cancelled"
]


# -----------------------------------------
# CUSTOMER DATA GENERATION
# -----------------------------------------

def generate_customers(num_customers):

    customers = []

    for i in range(1, num_customers + 1):

        customer = {
            "customer_id": f"CUST{i:05d}",
            "customer_name": fake.name(),
            "email": fake.unique.email(),
            "registration_date": fake.date_between(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            ).isoformat()
        }

        customers.append(customer)

    return pd.DataFrame(customers)


# -----------------------------------------
# ORDER DATA GENERATION
# -----------------------------------------

def generate_orders(num_orders, customers):

    orders = []

    customer_ids = customers["customer_id"].tolist()

    for i in range(1, num_orders + 1):

        order_datetime = fake.date_time_between(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2026, 10, 31),
            tzinfo=timezone.utc
        )

        updated_datetime = order_datetime

        order = {
            "order_id": f"ORD{i:06d}",
            "customer_id": random.choice(customer_ids),
            "order_date": order_datetime.isoformat(),
            "order_status": random.choice(ORDER_STATUSES),
            "updated_at": updated_datetime.isoformat()
        }

        orders.append(order)

    return pd.DataFrame(orders)


# -----------------------------------------
# ORDER ITEM DATA GENERATION
# -----------------------------------------

def generate_order_items(orders):

    order_items = []

    item_counter = 1

    for order_id in orders["order_id"]:

        # Each order contains 1 to 4 items
        number_of_items = int(rng.integers(1, 5))

        selected_products = random.choices(
            PRODUCTS,
            k=number_of_items
        )

        for product_id, product_name in selected_products:

            quantity = int(rng.integers(1, 6))

            # Generate price in paise to avoid
            # floating-point calculation errors
            unit_price_cents = int(
                rng.integers(10000, 10000001)
            )

            item = {
                "item_id": f"ITEM{item_counter:07d}",
                "order_id": order_id,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": f"{unit_price_cents / 100:.2f}"
            }

            order_items.append(item)

            item_counter += 1

    return pd.DataFrame(order_items)


# -----------------------------------------
# MAIN DATASET GENERATOR
# -----------------------------------------


def generate_dataset(
    num_customers=100,
    num_orders=500,
    output_dir=None
):
    if num_customers < 1 or num_orders < 1:
        raise ValueError("Customers and orders must be greater than zero.")

    target_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Starting synthetic dataset generation...")

    customers = generate_customers(num_customers)

    orders = generate_orders(
        num_orders,
        customers
    )

    order_items = generate_order_items(orders)

    customers.to_csv(
        target_dir / "customers.csv",
        index=False
    )

    orders.to_csv(
        target_dir / "orders.csv",
        index=False
    )

    order_items.to_csv(
        target_dir / "order_items.csv",
        index=False
    )

    print("\nDataset generation completed!")
    print(f"Customers generated: {len(customers)}")
    print(f"Orders generated: {len(orders)}")
    print(f"Order items generated: {len(order_items)}")
    print(f"\nOutput directory: {target_dir}")

    return {
        "customers": len(customers),
        "orders": len(orders),
        "order_items": len(order_items)
    }



# -----------------------------------------
# EXECUTION ENTRY POINT
# -----------------------------------------

if __name__ == "__main__":

    generate_dataset(
        num_customers=100,
        num_orders=500
    )
