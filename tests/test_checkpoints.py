
import uuid

import pytest

from src import database, pipeline
from src.checkpoints import (
    calculate_source_manifest,
    load_checkpoint,
    save_checkpoint,
)



@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    db_path = tmp_path / "checkpoint_tests.db"
    database.set_database_path(db_path)

    # Use the temporary directory as the checkpoint module's base directory.
    monkeypatch.setattr(
        "src.checkpoints.BASE_DIR",
        tmp_path
    )

    checkpoint_dir = tmp_path / "checkpoints"

    monkeypatch.setattr(
        "src.checkpoints.CHECKPOINT_DIR",
        checkpoint_dir
    )

    return checkpoint_dir



def test_checkpoint_save_and_restore(isolated_database, tmp_path):
    run_id = str(uuid.uuid4())
    pipeline.create_pipeline_run(run_id)
    source_file = tmp_path / "customers.csv"
    source_file.write_text("customer_id,name\n1,Test\n", encoding="utf-8")

    manifest = calculate_source_manifest({
        "customers": source_file
    })

    original_data = {"customers": [{"id": "1", "name": "Test"}]}

    save_checkpoint(
        run_id,
        "ingestion",
        original_data,
        manifest
    )

    restored_data = load_checkpoint(
        run_id,
        "ingestion",
        manifest
    )

    assert restored_data == original_data


def test_checkpoint_rejects_changed_source(isolated_database, tmp_path):
    run_id = str(uuid.uuid4())
    pipeline.create_pipeline_run(run_id)
    source_file = tmp_path / "customers.csv"
    source_file.write_text("customer_id,name\n1,Test\n", encoding="utf-8")

    original_manifest = calculate_source_manifest({
        "customers": source_file
    })

    save_checkpoint(
        run_id,
        "ingestion",
        {"records": 1},
        original_manifest
    )

    # Modify the source after saving the checkpoint.
    source_file.write_text(
        "customer_id,name\n2,Changed\n",
        encoding="utf-8"
    )

    changed_manifest = calculate_source_manifest({
        "customers": source_file
    })

    with pytest.raises(
        ValueError,
        match="Source files changed"
    ):
        load_checkpoint(
            run_id,
            "ingestion",
            changed_manifest
        )


def test_checkpoint_rejects_corrupted_artifact(
    isolated_database,
    tmp_path
):
    run_id = str(uuid.uuid4())
    pipeline.create_pipeline_run(run_id)
    source_file = tmp_path / "customers.csv"
    source_file.write_text("customer_id,name\n1,Test\n", encoding="utf-8")

    manifest = calculate_source_manifest({
        "customers": source_file
    })

    save_checkpoint(
        run_id,
        "ingestion",
        {"records": 1},
        manifest
    )

    artifact = isolated_database / run_id / "ingestion.pkl"

    # Change the saved artifact without updating its database hash.
    artifact.write_bytes(b"corrupted checkpoint")

    with pytest.raises(
        ValueError,
        match="integrity verification failed"
    ):
        load_checkpoint(
            run_id,
            "ingestion",
            manifest
        )


def test_checkpoint_rejects_missing_artifact(
    isolated_database,
    tmp_path
):
    run_id = str(uuid.uuid4())
    pipeline.create_pipeline_run(run_id)
    source_file = tmp_path / "customers.csv"
    source_file.write_text("customer_id,name\n1,Test\n", encoding="utf-8")

    manifest = calculate_source_manifest({
        "customers": source_file
    })

    save_checkpoint(
        run_id,
        "ingestion",
        {"records": 1},
        manifest
    )

    artifact = isolated_database / run_id / "ingestion.pkl"
    artifact.unlink()

    with pytest.raises(
        FileNotFoundError,
        match="Checkpoint artifact is missing"
    ):
        load_checkpoint(
            run_id,
            "ingestion",
            manifest
        )
