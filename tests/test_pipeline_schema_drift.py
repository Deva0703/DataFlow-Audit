import uuid

import pandas as pd
import pytest

from src import pipeline
from src.database import get_connection


def test_pipeline_marks_run_failed_on_schema_drift(
    monkeypatch,
    tmp_path
):
    test_run_id = f"test-schema-drift-{uuid.uuid4()}"

    monkeypatch.setattr(
        pipeline,
        "generate_run_id",
        lambda: test_run_id
    )

    # Create a copy of the orders data with an unexpected column.
    orders = pd.read_csv(
        pipeline.SOURCE_FILES["orders"]
    )

    orders["unexpected_column"] = "extra_value"

    drift_file = tmp_path / "orders_schema_drift.csv"
    orders.to_csv(drift_file, index=False)

    # Use the modified file only for this test.
    test_source_files = pipeline.SOURCE_FILES.copy()
    test_source_files["orders"] = drift_file

    monkeypatch.setattr(
        pipeline,
        "SOURCE_FILES",
        test_source_files
    )

    # The pipeline should reject the unexpected schema.
    with pytest.raises(ValueError):
        pipeline.run_pipeline()

    # Confirm that the failed run was recorded.
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
    assert "unexpected_column" in run["error_message"]