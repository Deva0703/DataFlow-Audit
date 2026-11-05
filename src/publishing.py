
from contextlib import closing
from pathlib import Path

import pandas as pd

from src.database import get_connection


BASE_DIR = Path(__file__).resolve().parent.parent

REQUIRED_COLUMNS = [
        "order_id",
        "customer_id",
        "customer_name",
        "total_items",
        "total_amount_cents",
        "order_status",
        "order_date"
    ]


def publish_order_facts(order_facts, db_path=None):
        """
        Publish transformed order facts into SQLite.

        Uses an UPSERT strategy:
        - New order IDs are inserted.
        - Existing order IDs are updated.
        - Duplicate order IDs in the incoming batch are rejected.

        Returns publishing statistics.
        """

        if not isinstance(order_facts, pd.DataFrame):
            raise TypeError("order_facts must be a pandas DataFrame")

        missing_columns = set(REQUIRED_COLUMNS) - set(order_facts.columns)

        if missing_columns:
            raise ValueError(
                f"Missing publishing columns: {sorted(missing_columns)}"
            )

        if order_facts["order_id"].isna().any():
            raise ValueError("Order IDs cannot be missing")

        if order_facts["order_id"].duplicated().any():
            raise ValueError("Duplicate order IDs in publishing batch")

        if (order_facts["total_items"] < 0).any():
            raise ValueError("Total items cannot be negative")

        if (order_facts["total_amount_cents"] < 0).any():
            raise ValueError("Total amount cannot be negative")

        if db_path is not None:
            db_path = Path(db_path)

            if not db_path.exists():
                raise FileNotFoundError(f"Database not found: {db_path}")

        records = order_facts[REQUIRED_COLUMNS].to_dict(orient="records")

        insert_sql = """
            INSERT INTO order_facts (
                order_id,
                customer_id,
                customer_name,
                total_items,
                total_amount_cents,
                order_status,
                order_date
            )
            VALUES (
                :order_id,
                :customer_id,
                :customer_name,
                :total_items,
                :total_amount_cents,
                :order_status,
                :order_date
            )
            ON CONFLICT(order_id) DO UPDATE SET
                customer_id = excluded.customer_id,
                customer_name = excluded.customer_name,
                total_items = excluded.total_items,
                total_amount_cents = excluded.total_amount_cents,
                order_status = excluded.order_status,
                order_date = excluded.order_date
        """

        with closing(get_connection(db_path)) as connection:
            with connection:
                incoming_ids = [record["order_id"] for record in records]

                existing_ids = set()

                # Query in batches to stay within SQLite's variable limit.
                batch_size = 900

                for start in range(0, len(incoming_ids), batch_size):
                    batch_ids = incoming_ids[start:start + batch_size]

                    placeholders = ",".join("?" for _ in batch_ids)

                    query = f"""
                        SELECT order_id
                        FROM order_facts
                        WHERE order_id IN ({placeholders})
                    """

                    batch_existing_ids = {
                        row[0]
                        for row in connection.execute(query, batch_ids).fetchall()
                    }

                    existing_ids.update(batch_existing_ids)

                connection.executemany(insert_sql, records)

        inserted_rows = len(records) - len(existing_ids)
        updated_rows = len(existing_ids)

        return {
            "total_rows": len(records),
            "inserted_rows": inserted_rows,
            "updated_rows": updated_rows,
            "published_rows": len(records)
        }


if __name__ == "__main__":
    print("Data publishing module loaded successfully.")
