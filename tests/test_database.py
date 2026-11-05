
import sqlite3
from src.database import DB_PATH


def test_database_tables_exist():

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]

    connection.close()

    expected_tables = [
        "customers",
        "orders",
        "order_items",
        "order_facts",
        "pipeline_runs",
        "input_files",
        "transformation_logs",
        "rejected_records",
        "output_lineage",
        "order_status_history"
    ]

    assert sorted(tables) == sorted(expected_tables)


def test_database_file_exists():

    assert DB_PATH.exists()
