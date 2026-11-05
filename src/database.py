
import sqlite3
from pathlib import Path


# Project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database location
DB_PATH = BASE_DIR / "data" / "dataflow_audit.db"
ACTIVE_DB_PATH = DB_PATH


def set_database_path(db_path):
    global ACTIVE_DB_PATH
    ACTIVE_DB_PATH = Path(db_path)
    initialize_database(ACTIVE_DB_PATH)


def get_connection(db_path=None):
    """
    Create a SQLite connection.
    Supports custom database paths for benchmarking and testing.
    """

    database_path = Path(db_path) if db_path else ACTIVE_DB_PATH

    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)

    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database(db_path=None):
    """
    Create all business and audit tables.
    """

    connection = get_connection(db_path)

    try:
        cursor = connection.cursor()

        # --------------------------------
        # 1. CUSTOMERS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                registration_date TEXT NOT NULL
            )
        """)

        # --------------------------------
        # 2. ORDERS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                order_date TEXT NOT NULL,
                order_status TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY (customer_id)
                    REFERENCES customers(customer_id)
            )
        """)

        # --------------------------------
        # 3. ORDER ITEMS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                item_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price_cents INTEGER NOT NULL
                    CHECK (unit_price_cents >= 0),

                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
            )
        """)

        # --------------------------------
        # 4. ORDER FACTS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_facts (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                total_items INTEGER NOT NULL,
                total_amount_cents INTEGER NOT NULL,
                order_status TEXT NOT NULL,
                order_date TEXT NOT NULL,

                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
            )
        """)

        # --------------------------------
        # 5. PIPELINE RUNS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                total_input_rows INTEGER DEFAULT 0,
                valid_rows INTEGER DEFAULT 0,
                rejected_rows INTEGER DEFAULT 0,
                published_rows INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)

        # --------------------------------
        # 6. INPUT FILES TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS input_files (
                file_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                received_at TEXT NOT NULL,
                row_count INTEGER DEFAULT 0,

                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id),

                UNIQUE (run_id, file_hash)
            )
        """)

        # --------------------------------
        # 7. TRANSFORMATION LOGS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transformation_logs (
                step_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                input_rows INTEGER DEFAULT 0,
                output_rows INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                details TEXT,

                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id)
            )
        """)

        # --------------------------------
        # 8. REJECTED RECORDS TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rejected_records (
                reject_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                source_record_id TEXT,
                source_row_number INTEGER NOT NULL,
                raw_record_json TEXT NOT NULL,
                rejection_reason TEXT NOT NULL,
                rejected_at TEXT NOT NULL,

                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id),

                FOREIGN KEY (file_id)
                    REFERENCES input_files(file_id)
            )
        """)

        # --------------------------------
        # 9. OUTPUT LINEAGE TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS output_lineage (
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
        """)

        # --------------------------------
        # 10. ORDER STATUS HISTORY TABLE
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_status_history (
                history_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                run_id TEXT NOT NULL,

                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id),

                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id)
            )
        """)


        # --------------------------------
        # 11. PIPELINE CHECKPOINTS
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
                run_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                source_manifest TEXT NOT NULL,
                created_at TEXT NOT NULL,

                PRIMARY KEY (run_id, stage_name),

                FOREIGN KEY (run_id)
                    REFERENCES pipeline_runs(run_id)
            )
        """)


        # Create useful indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_customer
            ON orders(customer_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_input_files_hash
            ON input_files(file_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lineage_output
            ON output_lineage(output_table, output_record_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rejected_run
            ON rejected_records(run_id)
        """)

        connection.commit()

        print("Database initialized successfully!")
        print(
            f"Database location: "
            f"{Path(db_path) if db_path else ACTIVE_DB_PATH}"
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
