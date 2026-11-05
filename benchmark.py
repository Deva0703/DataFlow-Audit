
import time
import uuid
from pathlib import Path

from src import pipeline
from src.database import initialize_database
from src.database import set_database_path
from src.database import set_database_path, get_connection


BASE_DIR = Path(__file__).resolve().parent

BENCHMARK_DIR = BASE_DIR / "data" / "benchmarks"
BENCHMARK_DB = BENCHMARK_DIR / "benchmark.db"


def run_pipeline_benchmark():

    benchmark_sizes = [
        "small",
        "medium",
        "large"
    ]

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize a separate benchmark database.
    set_database_path(BENCHMARK_DB)

    results = []

    print("\nDATAFLOW AUDIT - PIPELINE PERFORMANCE")
    print("=" * 70)

    for dataset in benchmark_sizes:

        print(f"\nRunning {dataset.upper()} benchmark...")

        # Select the dataset.
        pipeline.SOURCE_FILES = pipeline.get_source_files(
            f"benchmarks/{dataset}"
        )

        # Use a unique run ID.
        run_id = f"benchmark-{dataset}-{uuid.uuid4()}"

        # Measure complete pipeline execution time.
        start_time = time.perf_counter()

        pipeline.run_pipeline(run_id = run_id)

        elapsed_time = time.perf_counter() - start_time

        # Read actual input and output counts.
        with get_connection() as connection:

            run = connection.execute(
                """
                SELECT
                    total_input_rows,
                    valid_rows,
                    rejected_rows,
                    published_rows,
                    status
                FROM pipeline_runs
                WHERE run_id = ?
                """,
                (run_id,)
            ).fetchone()

        if run is None:
            raise RuntimeError(
                f"Benchmark run not found: {run_id}"
            )

        total_records = run[0]

        throughput = (
            total_records / elapsed_time
            if elapsed_time > 0 else 0
        )

        results.append({
            "dataset": dataset,
            "input_rows": run[0],
            "valid_rows": run[1],
            "rejected_rows": run[2],
            "published_rows": run[3],
            "execution_seconds": round(elapsed_time, 3),
            "records_per_second": round(throughput, 2),
            "status": run[4]
        })

        print(f"\nExecution time: {elapsed_time:.3f} seconds")
        print(f"Input rows: {run[0]:,}")
        print(f"Published rows: {run[3]:,}")
        print(f"Throughput: {throughput:,.2f} records/second")
        print(f"Status: {run[4]}")

    print("\nFINAL BENCHMARK SUMMARY")
    print("=" * 100)

    for result in results:
        print(result)

    return results


if __name__ == "__main__":
    run_pipeline_benchmark()
