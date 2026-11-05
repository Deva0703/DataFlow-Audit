from src.database import get_connection
from src.transformation import convert_price_to_cents


def reconcile_row_counts(
    total_input_rows,
    valid_rows,
    rejected_rows
):
    """
    Verify that every input row is either valid or rejected.
    """

    expected_rows = valid_rows + rejected_rows

    return {
        "check_name": "input_row_reconciliation",
        "expected": total_input_rows,
        "actual": expected_rows,
        "passed": total_input_rows == expected_rows
    }


def reconcile_order_counts(
    valid_order_count,
    transformed_order_count,
    published_order_count
):
    """
    Verify order counts across transformation and publishing.
    """

    return {
        "check_name": "order_count_reconciliation",
        "valid_orders": valid_order_count,
        "transformed_orders": transformed_order_count,
        "published_orders": published_order_count,
        "passed": (
            valid_order_count == transformed_order_count
            == published_order_count
        )
    }


def reconcile_amounts(
    source_total_cents,
    published_total_cents
):
    """
    Verify that source item amounts match published order amounts.
    """

    return {
        "check_name": "amount_reconciliation",
        "source_total_cents": source_total_cents,
        "published_total_cents": published_total_cents,
        "difference_cents": (
            source_total_cents - published_total_cents
        ),
        "passed": source_total_cents == published_total_cents
    }


def run_reconciliation(run_id, validated, order_facts):
    """
    Reconcile actual pipeline data against published SQLite records.
    """

    # 1. Reconcile input, valid and rejected row counts
    total_input_rows = sum(
        len(result["valid"]) + len(result["rejected"])
        for result in validated.values()
    )

    valid_rows = sum(
        len(result["valid"])
        for result in validated.values()
    )

    rejected_rows = sum(
        len(result["rejected"])
        for result in validated.values()
    )

    row_check = reconcile_row_counts(
        total_input_rows,
        valid_rows,
        rejected_rows
    )

    # 2. Calculate source item amount in cents
    order_items = validated["order_items"]["valid"]

    source_total_cents = sum(
        int(row.quantity) * convert_price_to_cents(row.unit_price)
        for row in order_items.itertuples(index=False)
    )

    # 3. Read actual published records from SQLite
    order_ids = order_facts["order_id"].tolist()

    published_records = []

    if order_ids:
        batch_size = 900

        with get_connection() as connection:
            for start in range(0, len(order_ids), batch_size):
                batch_ids = order_ids[start:start + batch_size]

                placeholders = ",".join("?" for _ in batch_ids)

                records = connection.execute(
                    f"""
                    SELECT order_id, total_amount_cents
                    FROM order_facts
                    WHERE order_id IN ({placeholders})
                    """,
                    batch_ids
                ).fetchall()

                published_records.extend(records)

        published_count = len(published_records)

        published_total_cents = sum(
            row["total_amount_cents"]
            for row in published_records
        )

    # 4. Reconcile order counts
    order_check = reconcile_order_counts(
        len(validated["orders"]["valid"]),
        len(order_facts),
        published_count
    )

    # 5. Reconcile financial amounts
    amount_check = reconcile_amounts(
        source_total_cents,
        published_total_cents
    )

    # 6. Check lineage relationships for this run
    expected_lineage_count = (
        len(order_facts)
        + len(order_facts)
        + len(order_items)
    )

    with get_connection() as connection:
        actual_lineage_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM output_lineage
            WHERE run_id = ?
            """,
            (run_id,)
        ).fetchone()[0]

    lineage_check = {
        "check_name": "lineage_reconciliation",
        "expected": expected_lineage_count,
        "actual": actual_lineage_count,
        "passed": expected_lineage_count == actual_lineage_count
    }

    checks = [
    row_check,
    order_check,
    amount_check,
    lineage_check
    ]

    print("\nRECONCILIATION CHECK DETAILS")
    print("============================")

    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"{check['check_name']}: {status}")
        print(check)

    overall_passed = all(
        check["passed"] for check in checks
)

    return {
        "checks": checks,
        "overall_passed": overall_passed
    }
