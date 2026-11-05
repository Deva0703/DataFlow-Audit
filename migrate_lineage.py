
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "benchmarks" / "benchmark.db"


def migrate_output_lineage():
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute("BEGIN")

        # Check whether the old constraint exists.
        table_info = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'output_lineage'
            """
        ).fetchone()

        if table_info is None:
            raise RuntimeError("output_lineage table does not exist")

        old_table_sql = table_info[0]

        if "output_record_id" in old_table_sql.split("UNIQUE")[1]:
            print("The lineage constraint is already updated.")
            connection.rollback()
            return

        # Create replacement table with corrected uniqueness.
        connection.execute(
            """
            CREATE TABLE output_lineage_new (
                lineage_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                source_record_id TEXT NOT NULL,
                output_table TEXT NOT NULL,
                output_record_id TEXT NOT NULL,
                published_at TEXT NOT NULL,

                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id),

                FOREIGN KEY (file_id)
                    REFERENCES input_files(file_id),

                UNIQUE (
                    run_id,
                    file_id,
                    source_record_id,
                    output_table,
                    output_record_id
                )
            )
            """
        )

        # Preserve all existing lineage records.
        connection.execute(
            """
            INSERT INTO output_lineage_new (
                lineage_id,
                run_id,
                file_id,
                source_record_id,
                output_table,
                output_record_id,
                published_at
            )
            SELECT
                lineage_id,
                run_id,
                file_id,
                source_record_id,
                output_table,
                output_record_id,
                published_at
            FROM output_lineage
            """
        )

        old_count = connection.execute(
            "SELECT COUNT(*) FROM output_lineage"
        ).fetchone()[0]

        new_count = connection.execute(
            "SELECT COUNT(*) FROM output_lineage_new"
        ).fetchone()[0]

        if old_count != new_count:
            raise RuntimeError(
                f"Migration count mismatch: {old_count} vs {new_count}"
            )

        # Replace the old table.
        connection.execute("DROP TABLE output_lineage")

        connection.execute(
            "ALTER TABLE output_lineage_new RENAME TO output_lineage"
        )

        connection.commit()

        print("Lineage migration completed successfully!")
        print(f"Existing records preserved: {new_count}")
        print("Updated unique constraint includes output_record_id.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate_output_lineage()
