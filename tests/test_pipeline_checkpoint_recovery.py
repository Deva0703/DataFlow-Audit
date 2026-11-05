
import uuid

import pytest

from src import pipeline
from src import database


def test_pipeline_resumes_same_run_from_checkpoints(
    monkeypatch,
    tmp_path
):
    # Use an isolated database for this test.
    test_db = tmp_path / "checkpoint_recovery.db"
    database.set_database_path(test_db)

    run_id = f"checkpoint-recovery-{uuid.uuid4()}"

    # Track how many times the checkpointed stages execute.
    calls = {
        "ingestion": 0,
        "validation": 0,
        "transformation": 0,
    }

    original_ingest = pipeline.ingest_source_files
    original_validate = pipeline.validate_source_datasets
    original_transform = pipeline.transform_orders
    original_publish = pipeline.publish_order_facts

    def tracked_ingestion(*args, **kwargs):
        calls["ingestion"] += 1
        return original_ingest(*args, **kwargs)

    def tracked_validation(*args, **kwargs):
        calls["validation"] += 1
        return original_validate(*args, **kwargs)

    def tracked_transformation(*args, **kwargs):
        calls["transformation"] += 1
        return original_transform(*args, **kwargs)

    publish_attempts = {"count": 0}

    def fail_first_publish(*args, **kwargs):
        publish_attempts["count"] += 1

        if publish_attempts["count"] == 1:
            raise RuntimeError("Simulated publishing failure")

        return original_publish(*args, **kwargs)

    monkeypatch.setattr(
        pipeline, "ingest_source_files", tracked_ingestion
    )
    monkeypatch.setattr(
        pipeline, "validate_source_datasets", tracked_validation
    )
    monkeypatch.setattr(
        pipeline, "transform_orders", tracked_transformation
    )
    monkeypatch.setattr(
        pipeline, "publish_order_facts", fail_first_publish
    )

    # First execution: fail during publishing.
    with pytest.raises(
        RuntimeError,
        match="Simulated publishing failure"
    ):
        pipeline.run_pipeline(run_id=run_id)

    # Confirm the run failed and all three checkpoints were saved.
    with database.get_connection() as connection:
        run = connection.execute(
            """
            SELECT status
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (run_id,)
        ).fetchone()

        assert run is not None
        assert run["status"] == "FAILED"

        checkpoints = connection.execute(
            """
            SELECT stage_name
            FROM pipeline_checkpoints
            WHERE run_id = ?
            """,
            (run_id,)
        ).fetchall()

        saved_stages = {row["stage_name"] for row in checkpoints}

        assert saved_stages == {
            "ingestion",
            "validation",
            "transformation",
        }

    # Each checkpointed stage should have executed once.
    assert calls == {
        "ingestion": 1,
        "validation": 1,
        "transformation": 1,
    }

    # Second execution: resume the SAME run ID.
    pipeline.run_pipeline(run_id=run_id)

    # The saved checkpoints should be restored, not recomputed.
    assert calls == {
        "ingestion": 1,
        "validation": 1,
        "transformation": 1,
    }

    assert publish_attempts["count"] == 2

    # Confirm the original run eventually succeeded.
    with database.get_connection() as connection:
        run = connection.execute(
            """
            SELECT status, published_rows
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (run_id,)
        ).fetchone()

        assert run is not None
        assert run["status"] == "SUCCESS"
        assert run["published_rows"] > 0
