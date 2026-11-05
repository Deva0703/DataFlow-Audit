import pytest
import uuid
from src import pipeline
from src.database import get_connection


def test_pipeline_marks_run_failed_when_input_file_is_missing(
    monkeypatch,
    tmp_path
):
    # Use a predictable ID so we can find this test run.
    test_run_id = f"test-missing-input-{uuid.uuid4()}"

    monkeypatch.setattr(
        pipeline,
        "generate_run_id",
        lambda: test_run_id
    )

    # Point the customers input to a file that does not exist.
    missing_file = tmp_path / "missing_customers.csv"

    monkeypatch.setattr(
        pipeline,
        "SOURCE_FILES",
        {
            "customers": missing_file,
            "orders": pipeline.SOURCE_FILES["orders"],
            "order_items": pipeline.SOURCE_FILES["order_items"]
        }
    )

    # The pipeline should raise an error instead of reporting success.
    with pytest.raises(FileNotFoundError):
        pipeline.run_pipeline()

    # Verify that the failed run was recorded in SQLite.
    with get_connection() as connection:
        run = connection.execute(
            """
            SELECT status, ended_at, error_message
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (test_run_id,)
        ).fetchone()

    assert run is not None
    assert run["status"] == "FAILED"
    assert run["ended_at"] is not None
    assert run["error_message"] is not None
    assert "missing_customers.csv" in run["error_message"]