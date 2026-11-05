import uuid

import pandas as pd

from src import pipeline
from src.database import get_connection


def test_pipeline_rejects_invalid_records_and_continues(
    monkeypatch,
    tmp_path
):
    test_run_id = f"test-rejected-records-{uuid.uuid4()}"

    monkeypatch.setattr(
        pipeline,
        "generate_run_id",
        lambda: test_run_id
    )

    # Load the original customers data.
    customers = pd.read_csv(
        pipeline.SOURCE_FILES["customers"]
    )

    # Make one customer record invalid.
    customers.loc[0, "customer_name"] = None

    invalid_customers_file = tmp_path / "customers_with_invalid.csv"

    customers.to_csv(
        invalid_customers_file,
        index=False
    )

    # Replace only the customers input.
    test_source_files = pipeline.SOURCE_FILES.copy()

    test_source_files["customers"] = invalid_customers_file

    monkeypatch.setattr(
        pipeline,
        "SOURCE_FILES",
        test_source_files
    )

    # The pipeline should continue despite one rejected record.
    pipeline.run_pipeline()

    # Verify the run completed successfully.
    with get_connection() as connection:

        run = connection.execute(
            """
            SELECT status, total_input_rows, valid_rows, rejected_rows
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (test_run_id,)
        ).fetchone()

        rejected = connection.execute(
            """
            SELECT rejection_reason, raw_record_json
            FROM rejected_records
            WHERE run_id = ?
            """,
            (test_run_id,)
        ).fetchall()

    assert run is not None
    assert run["status"] == "SUCCESS"

    assert run["total_input_rows"] == 1807

    # Valid and rejected records must account for every input row.
    assert run["valid_rows"] == 1787
    assert run["rejected_rows"] == 20
    assert run["valid_rows"] + run["rejected_rows"] == run["total_input_rows"]

    # The original invalid customer must be recorded.
    assert len(rejected) == 20
    assert any(
        "customer_name" in record["rejection_reason"]
        for record in rejected
    )
    assert "customer_name" in rejected[0]["rejection_reason"]