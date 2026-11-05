
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


def calculate_file_hash(file_path):
    """Calculate SHA-256 hash to identify a file's contents."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def ingest_csv(file_path):
    """
    Read a CSV file and capture its metadata.

    Returns:
        dataframe, metadata
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Input path is not a file: {file_path}")

    file_hash = calculate_file_hash(file_path)
    file_size = file_path.stat().st_size

    if file_size == 0:
        raise ValueError(f"Input file is empty: {file_path.name}")

    try:
        dataframe = pd.read_csv(file_path, engine="python", on_bad_lines="error")
    except pd.errors.EmptyDataError as error:
        raise ValueError(
            f"CSV contains no readable data: {file_path.name}"
        ) from error
    except pd.errors.ParserError as error:
        raise ValueError(
            f"Malformed CSV file: {file_path.name} - {error}"
        ) from error

    metadata = {
        "file_name": file_path.name,
        "file_path": str(file_path.resolve()),
        "file_hash": file_hash,
        "file_size_bytes": file_size,
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "received_at": datetime.now(timezone.utc).isoformat()
    }

    logger.info(
        "Ingested %s: %s rows, %s columns",
        file_path.name,
        len(dataframe),
        len(dataframe.columns)
    )

    return dataframe, metadata


if __name__ == "__main__":
    print("Data ingestion module loaded successfully.")
