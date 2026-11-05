
import json
import logging
import uuid

from src.reconciliation import run_reconciliation

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.database import initialize_database, get_connection
from src.ingestion import ingest_csv
from src.validation import validate_records
from src.transformation import (
    transform_orders,
    convert_price_to_cents
)
from src.publishing import publish_order_facts


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

def get_source_files(dataset="sample"):

    dataset_dir = BASE_DIR / "data" / dataset

    return {
        "customers": dataset_dir / "customers.csv",
        "orders": dataset_dir / "orders.csv",
        "order_items": dataset_dir / "order_items.csv"
    }


SOURCE_FILES = get_source_files()


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            BASE_DIR / "dataflow_audit.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------

def generate_run_id():
    """Generate a unique ID for every pipeline execution."""
    return str(uuid.uuid4())


def get_current_timestamp():
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------
# PIPELINE RUN MANAGEMENT
# --------------------------------------------------

def create_pipeline_run(run_id):
    """Create an audit record for a new pipeline execution."""

    initialize_database()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO pipeline_runs (
                run_id,
                started_at,
                status
            )
            VALUES (?, ?, ?)
            """,
            (
                run_id,
                get_current_timestamp(),
                "RUNNING"
            )
        )

    logger.info("Pipeline run created: %s", run_id)


# --------------------------------------------------
# INGESTION
# --------------------------------------------------

def ingest_source_files(run_id):
    """Ingest source CSV files and record their metadata."""

    datasets = {}

    with get_connection() as connection:

        for entity, file_path in SOURCE_FILES.items():

            logger.info("Ingesting %s file", entity)

            dataframe, metadata = ingest_csv(file_path)

            file_id = str(uuid.uuid4())

            connection.execute(
                """
                INSERT INTO input_files (
                    file_id,
                    run_id,
                    file_name,
                    file_path,
                    file_hash,
                    file_size_bytes,
                    received_at,
                    row_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    run_id,
                    metadata["file_name"],
                    metadata["file_path"],
                    metadata["file_hash"],
                    metadata["file_size_bytes"],
                    metadata["received_at"],
                    metadata["row_count"]
                )
            )

            datasets[entity] = {
                "data": dataframe,
                "file_id": file_id,
                "metadata": metadata
            }

            logger.info(
                "%s: %s rows ingested",
                entity,
                metadata["row_count"]
            )

    return datasets


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

def validate_source_datasets(run_id, datasets):
    """Validate source datasets and save rejected records."""

    validated = {}

    total_input_rows = 0
    total_valid_rows = 0
    total_rejected_rows = 0

    validation_order = [
        "customers",
        "orders",
        "order_items"
    ]

    with get_connection() as connection:

        for entity in validation_order:

            logger.info("Validating %s", entity)

            source_data = datasets[entity]["data"]
            file_id = datasets[entity]["file_id"]

            valid_reference_ids = None

            if entity == "orders":
                valid_reference_ids = set(
                    validated["customers"]["valid"]["customer_id"]
                )

            elif entity == "order_items":
                valid_reference_ids = set(
                    validated["orders"]["valid"]["order_id"]
                )

            valid, rejected = validate_records(
                source_data,
                entity,
                valid_reference_ids
            )

            total_input_rows += len(source_data)
            total_valid_rows += len(valid)
            total_rejected_rows += len(rejected)

            primary_key = {
                "customers": "customer_id",
                "orders": "order_id",
                "order_items": "item_id"
            }[entity]

            for _, row in rejected.iterrows():

                raw_record = row.drop(
                    labels=[
                        "source_row_number",
                        "rejection_reason"
                    ]
                ).to_dict()

                connection.execute(
                    """
                    INSERT INTO rejected_records (
                        reject_id,
                        run_id,
                        file_id,
                        source_record_id,
                        source_row_number,
                        raw_record_json,
                        rejection_reason,
                        rejected_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        run_id,
                        file_id,
                        str(row[primary_key])
                        if pd.notna(row[primary_key]) else None,
                        int(row["source_row_number"]),
                        json.dumps(raw_record, default=str),
                        row["rejection_reason"],
                        get_current_timestamp()
                    )
                )

            validated[entity] = {
                "valid": valid,
                "rejected": rejected,
                "file_id": file_id
            }

            logger.info(
                "%s validation: %s valid, %s rejected",
                entity,
                len(valid),
                len(rejected)
            )

        connection.execute(
            """
            UPDATE pipeline_runs
            SET total_input_rows = ?,
                valid_rows = ?,
                rejected_rows = ?
            WHERE run_id = ?
            """,
            (
                total_input_rows,
                total_valid_rows,
                total_rejected_rows,
                run_id
            )
        )

    return validated


# --------------------------------------------------
# SOURCE TABLE LOADING
# --------------------------------------------------

def load_source_tables(validated):
    """Load validated records into normalized SQLite tables."""

    with get_connection() as connection:

        customers = validated["customers"]["valid"]
        orders = validated["orders"]["valid"]
        order_items = validated["order_items"]["valid"]

        # 1. Load customers
        connection.executemany(
            """
            INSERT INTO customers (
                customer_id,
                customer_name,
                email,
                registration_date
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                customer_name = excluded.customer_name,
                email = excluded.email,
                registration_date = excluded.registration_date
            """,
            [
                (
                    row.customer_id,
                    row.customer_name,
                    row.email,
                    row.registration_date
                )
                for row in customers.itertuples(index=False)
            ]
        )

        # 2. Load orders
        connection.executemany(
            """
            INSERT INTO orders (
                order_id,
                customer_id,
                order_date,
                order_status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                customer_id = excluded.customer_id,
                order_date = excluded.order_date,
                order_status = excluded.order_status,
                updated_at = excluded.updated_at
            WHERE julianday(excluded.updated_at) > julianday(orders.updated_at)
            """,
            [
                (
                    row.order_id,
                    row.customer_id,
                    row.order_date,
                    row.order_status,
                    row.updated_at
                )
                for row in orders.itertuples(index=False)
            ]
        )

        # 3. Load order items
        connection.executemany(
            """
            INSERT INTO order_items (
                item_id,
                order_id,
                product_id,
                product_name,
                quantity,
                unit_price_cents
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                order_id = excluded.order_id,
                product_id = excluded.product_id,
                product_name = excluded.product_name,
                quantity = excluded.quantity,
                unit_price_cents = excluded.unit_price_cents
            """,
            [
                (
                    row.item_id,
                    row.order_id,
                    row.product_id,
                    row.product_name,
                    int(row.quantity),
                    convert_price_to_cents(row.unit_price)
                )
                for row in order_items.itertuples(index=False)
            ]
        )

    logger.info(
        "Source tables loaded: %s customers, %s orders, %s items",
        len(customers),
        len(orders),
        len(order_items)
    )

    return {
        "customers": len(customers),
        "orders": len(orders),
        "order_items": len(order_items)
    }


# --------------------------------------------------
# OUTPUT LINEAGE
# --------------------------------------------------


def record_output_lineage(run_id, validated, order_facts):
    """Record source-to-output relationships efficiently."""

    lineage_records = []

    order_items = validated["order_items"]["valid"]

    # Group items by order only once instead of scanning the
    # entire DataFrame for every individual order.
    items_by_order = (
        order_items.groupby("order_id")["item_id"]
        .agg(list)
        .to_dict()
    )

    orders_file_id = validated["orders"]["file_id"]
    customers_file_id = validated["customers"]["file_id"]
    items_file_id = validated["order_items"]["file_id"]

    published_at = get_current_timestamp()

    for order in order_facts.itertuples(index=False):

        order_id = order.order_id
        customer_id = order.customer_id

        # Link the original order and customer records.
        source_links = [
            (orders_file_id, order_id),
            (customers_file_id, customer_id)
        ]

        # Retrieve already-grouped items for this order.
        for item_id in items_by_order.get(order_id, []):
            source_links.append((items_file_id, item_id))

        # Build lineage relationships.
        for file_id, source_record_id in source_links:
            lineage_records.append(
                (
                    str(uuid.uuid4()),
                    run_id,
                    file_id,
                    source_record_id,
                    "order_facts",
                    order_id,
                    published_at
                )
            )

    # Insert all lineage relationships in one batch.
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO output_lineage (
                lineage_id,
                run_id,
                file_id,
                source_record_id,
                output_table,
                output_record_id,
                published_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            lineage_records
        )

    logger.info(
        "Output lineage recorded: %s relationships",
        len(lineage_records)
    )

    return len(lineage_records)



def log_pipeline_step(
    run_id,
    step_name,
    started_at,
    input_rows,
    output_rows,
    status="SUCCESS",
    details=None
):
    """Save pipeline step execution details in SQLite."""

    ended_at = get_current_timestamp()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO transformation_logs (
                step_id,
                run_id,
                step_name,
                started_at,
                ended_at,
                input_rows,
                output_rows,
                status,
                details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                run_id,
                step_name,
                started_at,
                ended_at,
                input_rows,
                output_rows,
                status,
                details
            )
        )

    logger.info(
        "Audit step recorded: %s | %s | %s -> %s rows",
        step_name,
        status,
        input_rows,
        output_rows
    )



# --------------------------------------------------
# PIPELINE RUN STATUS
# --------------------------------------------------

def update_pipeline_run(
    run_id,
    status,
    published_rows=0,
    error_message=None
):
    """Update the final status and metrics of a pipeline run."""

    with get_connection() as connection:

        connection.execute(
            """
            UPDATE pipeline_runs
            SET ended_at = ?,
                status = ?,
                published_rows = ?,
                error_message = ?
            WHERE run_id = ?
            """,
            (
                get_current_timestamp(),
                status,
                published_rows,
                error_message,
                run_id
            )
        )

    logger.info(
        "Pipeline run %s finished with status: %s",
        run_id,
        status
    )


# --------------------------------------------------
# PIPELINE EXECUTION
# --------------------------------------------------

def run_pipeline(run_id=None):

    if run_id is None:
        run_id = generate_run_id()

    published_rows = 0

    print("\nDataFlow Audit - Pipeline")
    print("-------------------------")
    print(f"Run ID: {run_id}")

    try:

        # 1. Create run
        create_pipeline_run(run_id)

        # 2. Ingestion
        ingestion_started_at = get_current_timestamp()

        datasets = ingest_source_files(run_id)

        ingestion_input_rows = sum(
            result["metadata"]["row_count"]
            for result in datasets.values()
        )

        log_pipeline_step(
            run_id=run_id,
            step_name="ingestion",
            started_at=ingestion_started_at,
            input_rows=ingestion_input_rows,
            output_rows=ingestion_input_rows,
            status="SUCCESS",
            details="Successfully ingested all source CSV files."
        )

        # 3. Validation
        validation_started_at = get_current_timestamp()

        validated = validate_source_datasets(
            run_id,
            datasets
        )

        validation_input_rows = sum(
            len(result["valid"]) + len(result["rejected"])
            for result in validated.values()
        )

        validation_output_rows = sum(
            len(result["valid"])
            for result in validated.values()
        )

        validation_rejected_rows = sum(
            len(result["rejected"])
            for result in validated.values()
        )

        log_pipeline_step(
            run_id=run_id,
            step_name="validation",
            started_at=validation_started_at,
            input_rows=validation_input_rows,
            output_rows=validation_output_rows,
            status="SUCCESS",
            details=(
                f"Validation completed. "
                f"Accepted: {validation_output_rows}, "
                f"Rejected: {validation_rejected_rows}"
            )
        )

        print("\nValidation completed!")

        for entity, result in validated.items():
            print(
                f"{entity}: "
                f"{len(result['valid'])} valid, "
                f"{len(result['rejected'])} rejected"
            )

        # 4. Load source tables
        loading_started_at = get_current_timestamp()

        loaded_counts = load_source_tables(validated)

        loading_input_rows = sum(
            len(result["valid"])
            for result in validated.values()
        )

        loading_output_rows = sum(
            loaded_counts.values()
        )

        log_pipeline_step(
            run_id=run_id,
            step_name="source_table_loading",
            started_at=loading_started_at,
            input_rows=loading_input_rows,
            output_rows=loading_output_rows,
            status="SUCCESS",
            details=(
                f"Customers: {loaded_counts['customers']}, "
                f"Orders: {loaded_counts['orders']}, "
                f"Order items: {loaded_counts['order_items']}"
            )
        )

        
        # 5. Transformation
        transformation_started_at = get_current_timestamp()

        order_facts = transform_orders(
            validated["customers"]["valid"],
            validated["orders"]["valid"],
            validated["order_items"]["valid"]
        )

        log_pipeline_step(
            run_id=run_id,
            step_name="order_transformation",
            started_at=transformation_started_at,
            input_rows=len(validated["orders"]["valid"]),
            output_rows=len(order_facts),
            status="SUCCESS",
            details="Generated order-level facts from customers, orders and order items."
        )

        print("\nTransformation completed!")
        print(f"Order facts generated: {len(order_facts)}")
        print(order_facts.head())


        # 6. Publishing
        publishing_started_at = get_current_timestamp()

        publish_summary = publish_order_facts(order_facts)

        published_rows = publish_summary["published_rows"]

        log_pipeline_step(
            run_id=run_id,
            step_name="publishing",
            started_at=publishing_started_at,
            input_rows=len(order_facts),
            output_rows=published_rows,
            status="SUCCESS",
            details=(
                f"Inserted: {publish_summary['inserted_rows']}, "
                f"Updated: {publish_summary['updated_rows']}"
            )
        )

        # 7. Output lineage
        lineage_count = record_output_lineage(
            run_id,
            validated,
            order_facts
        )

        print("\nAudit lineage completed!")
        print(
            f"Lineage relationships recorded: "
            f"{lineage_count}"
        )

        # 8. Reconcile pipeline data
        reconciliation_started_at = get_current_timestamp()

        reconciliation = run_reconciliation(
            run_id,
            validated,
            order_facts
        )

        passed_checks = sum(
            1 for check in reconciliation["checks"]
            if check["passed"]
        )

        total_checks = len(reconciliation["checks"])

        log_pipeline_step(
            run_id=run_id,
            step_name="reconciliation",
            started_at=reconciliation_started_at,
            input_rows=total_checks,
            output_rows=passed_checks,
            status="SUCCESS" if reconciliation["overall_passed"] else "FAILED",
            details=(
                f"Passed checks: {passed_checks}/{total_checks}"
            )
        )

        # 8. Mark successful run only if reconciliation passes
        if not reconciliation["overall_passed"]:
            raise RuntimeError(
                f"Reconciliation failed: "
                f"{passed_checks}/{total_checks} checks passed"
            )

        update_pipeline_run(
            run_id,
            status="SUCCESS",
            published_rows=published_rows
)

        print("\nPipeline completed successfully!")

    except Exception as error:

        logger.exception("Pipeline execution failed")

        try:
            update_pipeline_run(
                run_id,
                status="FAILED",
                published_rows=published_rows,
                error_message=str(error)
            )
        except Exception:
            logger.exception("Could not update failed pipeline status")

        print(f"\nPipeline failed: {error}")

        raise


if __name__ == "__main__":
    run_pipeline()
