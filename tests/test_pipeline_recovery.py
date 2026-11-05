import uuid

import pytest

from src import pipeline
from src.database import get_connection


def test_pipeline_recovers_after_transformation_failure(monkeypatch):

    failed_run_id = f"test-recovery-failed-{uuid.uuid4()}"
    successful_run_id = f"test-recovery-success-{uuid.uuid4()}"

    run_ids = iter([failed_run_id, successful_run_id])

    monkeypatch.setattr(
        pipeline,
        "generate_run_id",
        lambda: next(run_ids)
    )

    # Save the original transformation function.
    original_transform = pipeline.transform_orders

    # Simulate a transformation failure on the first execution.
    monkeypatch.setattr(
        pipeline,
        "transform_orders",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("Simulated transformation failure")
        )
    )

    # First execution should fail.
    with pytest.raises(
        RuntimeError,
        match="Simulated transformation failure"
    ):
        pipeline.run_pipeline()

    # Verify that the failed run was recorded.
    with get_connection() as connection:

        failed_run = connection.execute(
            """
            SELECT status, error_message
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (failed_run_id,)
        ).fetchone()

        assert failed_run is not None
        assert failed_run["status"] == "FAILED"
        assert "Simulated transformation failure" in failed_run["error_message"]

        # Source records should already have been loaded.
        source_counts_after_failure = {}

        for table in ["customers", "orders", "order_items"]:
            source_counts_after_failure[table] = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

    # Restore the original transformation function.
    monkeypatch.setattr(
        pipeline,
        "transform_orders",
        original_transform
    )

    # Second execution should succeed.
    pipeline.run_pipeline()

    # Verify recovery and ensure no duplicate source records.
    with get_connection() as connection:

        successful_run = connection.execute(
            """
            SELECT status
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (successful_run_id,)
        ).fetchone()

        assert successful_run is not None
        assert successful_run["status"] == "SUCCESS"

        for table in ["customers", "orders", "order_items"]:

            final_count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            assert final_count == source_counts_after_failure[table]