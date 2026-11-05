
import hashlib
import json
import logging
import os
import pickle

from datetime import datetime, timezone
from pathlib import Path

from src.database import initialize_database, get_connection


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = BASE_DIR / "data" / "checkpoints"


def calculate_source_manifest(source_files):
    """Create a deterministic manifest of the current source files."""

    manifest = {}

    for entity, file_path in sorted(source_files.items()):
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Source file not found: {path}"
            )

        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        manifest[entity] = digest.hexdigest()

    return json.dumps(manifest, sort_keys=True)


def calculate_file_hash(file_path):
    """Calculate SHA-256 for a checkpoint artifact."""

    digest = hashlib.sha256()

    with Path(file_path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def save_checkpoint(run_id, stage_name, data, source_manifest):
    """Save a checkpoint atomically and record its metadata."""

    initialize_database()

    run_directory = CHECKPOINT_DIR / run_id
    run_directory.mkdir(parents=True, exist_ok=True)

    artifact_path = run_directory / f"{stage_name}.pkl"
    temporary_path = artifact_path.with_suffix(".tmp")

    try:
        with temporary_path.open("wb") as file:
            pickle.dump(data, file, protocol=pickle.HIGHEST_PROTOCOL)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, artifact_path)

        artifact_hash = calculate_file_hash(artifact_path)

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO pipeline_checkpoints (
                    run_id,
                    stage_name,
                    artifact_path,
                    artifact_hash,
                    source_manifest,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, stage_name) DO UPDATE SET
                    artifact_path = excluded.artifact_path,
                    artifact_hash = excluded.artifact_hash,
                    source_manifest = excluded.source_manifest,
                    created_at = excluded.created_at
                """,
                (
                    run_id,
                    stage_name,
                    str(artifact_path.relative_to(BASE_DIR)),
                    artifact_hash,
                    source_manifest,
                    datetime.now(timezone.utc).isoformat()
                )
            )

        logger.info(
            "Checkpoint saved: run=%s stage=%s",
            run_id,
            stage_name
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_checkpoint(run_id, stage_name, source_manifest):
    """Load a verified checkpoint, or return None if it doesn't exist."""

    initialize_database()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT artifact_path, artifact_hash, source_manifest
            FROM pipeline_checkpoints
            WHERE run_id = ? AND stage_name = ?
            """,
            (run_id, stage_name)
        ).fetchone()

    if row is None:
        return None

    stored_manifest = row["source_manifest"]

    if stored_manifest != source_manifest:
        raise ValueError(
            f"Source files changed since checkpoint: {stage_name}"
        )

    artifact_path = (BASE_DIR / row["artifact_path"]).resolve()

    if not artifact_path.is_relative_to(CHECKPOINT_DIR.resolve()):
        raise ValueError("Invalid checkpoint artifact path")

    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Checkpoint artifact is missing: {artifact_path}"
        )

    actual_hash = calculate_file_hash(artifact_path)

    if actual_hash != row["artifact_hash"]:
        raise ValueError(
            f"Checkpoint integrity verification failed: {stage_name}"
        )

    # Only load checkpoint files created by this local pipeline.
    with artifact_path.open("rb") as file:
        data = pickle.load(file)

    logger.info(
        "Checkpoint restored: run=%s stage=%s",
        run_id,
        stage_name
    )

    return data
