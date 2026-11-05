import uuid

import pytest

from src import pipeline
from src.database import get_connection


def test_pipeline_marks_run_failed_on_malformed_csv(
    monkeypatch,
    tmp_path
):
    test_run_id = f"test-malformed-csv-{uuid.uuid4()}"

    monkeypatch.setattr(
        pipeline,
        "generate_run_id",
        lambda: test_run_id
    )

    # Create an intentionally malformed CSV.
    malformed_file = tmp_path / "malformed_orders.csv"

    malformed_file.write_text(
        'order_id,customer_id,order_date,order_status,updated_at\n'
        'ORD001,CUST001,2026-11-04,placed,2026-11-04\n'
        '"ORD002,CUST002,2026-11-04,shipped,2026-11-04\n',
        encoding="utf-8"
    )

    # Replace only the orders input file.
    test_source_files = pipeline.SOURCE_FILES.copy()
    test_source_files["orders"] = malformed_file

    monkeypatch.setattr(
        pipeline,
        "SOURCE_FILES",
        test_source_files
    )

    # The pipeline should reject the malformed CSV.
    with pytest.raises(Exception):
        pipeline.run_pipeline()

    # Verify the failed run was recorded.
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