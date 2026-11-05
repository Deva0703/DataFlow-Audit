import uuid

from src import pipeline
from src.database import get_connection


def test_pipeline_rerun_does_not_create_duplicate_records(monkeypatch):

    first_run_id = f"test-idempotency-1-{uuid.uuid4()}"
    second_run_id = f"test-idempotency-2-{uuid.uuid4()}"

    run_ids = iter([first_run_id, second_run_id])

    monkeypatch.setattr(
        pipeline,
        "generate_run_id",
        lambda: next(run_ids)
    )

    # First pipeline execution
    pipeline.run_pipeline()

    # Capture record counts after the first execution
    with get_connection() as connection:

        first_counts = {}

        for table in [
            "customers",
            "orders",
            "order_items",
            "order_facts"
        ]:
            first_counts[table] = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

    # Second pipeline execution with identical input files
    pipeline.run_pipeline()

    # Capture record counts after the second execution
    with get_connection() as connection:

        second_counts = {}

        for table in [
            "customers",
            "orders",
            "order_items",
            "order_facts"
        ]:
            second_counts[table] = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

        # Check both runs were recorded
        run_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM pipeline_runs
            WHERE run_id IN (?, ?)
            """,
            (first_run_id, second_run_id)
        ).fetchone()[0]

        # Check lineage records for each run
        first_lineage = connection.execute(
            """
            SELECT COUNT(*)
            FROM output_lineage
            WHERE run_id = ?
            """,
            (first_run_id,)
        ).fetchone()[0]

        second_lineage = connection.execute(
            """
            SELECT COUNT(*)
            FROM output_lineage
            WHERE run_id = ?
            """,
            (second_run_id,)
        ).fetchone()[0]

    # Published table counts must remain unchanged
    assert first_counts == second_counts

    # Both pipeline executions must be audited
    assert run_count == 2

    # Both runs must have their own lineage records
    assert first_lineage == 2207
    assert second_lineage == 2207