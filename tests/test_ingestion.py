
import pandas as pd
import pytest

from src.ingestion import calculate_file_hash, ingest_csv


def test_ingest_valid_csv(tmp_path):
    file_path = tmp_path / "customers.csv"

    df = pd.DataFrame({
        "customer_id": ["CUST001", "CUST002"],
        "customer_name": ["Arun", "Kumar"]
    })
    df.to_csv(file_path, index=False)

    result, metadata = ingest_csv(file_path)

    assert len(result) == 2
    assert metadata["file_name"] == "customers.csv"
    assert metadata["row_count"] == 2
    assert metadata["column_count"] == 2
    assert len(metadata["file_hash"]) == 64
    assert metadata["file_size_bytes"] > 0
    assert metadata["received_at"]


def test_file_hash_is_deterministic(tmp_path):
    file_path = tmp_path / "sample.csv"
    file_path.write_text("id,name\n1,Arun\n", encoding="utf-8")

    first_hash = calculate_file_hash(file_path)
    second_hash = calculate_file_hash(file_path)

    assert first_hash == second_hash


def test_missing_file_raises_error(tmp_path):
    file_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        ingest_csv(file_path)


def test_empty_file_raises_error(tmp_path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Input file is empty"):
        ingest_csv(file_path)


def test_malformed_csv_raises_error(tmp_path):
    file_path = tmp_path / "malformed.csv"

    file_path.write_text(
        'customer_id,customer_name\n'
        'CUST001,"Arun\n'
        'CUST002,"Kumar\n'
        'CUST003,"Ravi\n',
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Malformed CSV file"):
        ingest_csv(file_path)


def test_same_content_has_same_hash(tmp_path):
    first_file = tmp_path / "first.csv"
    second_file = tmp_path / "second.csv"

    content = "id,name\n1,Arun\n"

    first_file.write_text(content, encoding="utf-8")
    second_file.write_text(content, encoding="utf-8")

    assert calculate_file_hash(first_file) == calculate_file_hash(second_file)
