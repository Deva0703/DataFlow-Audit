
from src.database import get_connection


def inspect_pipeline_run(run_id):

    with get_connection() as connection:

        run = connection.execute(
            """
            SELECT *
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (run_id,)
        ).fetchone()

        if run is None:
            print(f"No pipeline run found: {run_id}")
            return

        print("\nPIPELINE RUN SUMMARY")
        print("=" * 80)
        print(f"Run ID: {run['run_id']}")
        print(f"Started: {run['started_at']}")
        print(f"Ended: {run['ended_at']}")
        print(f"Status: {run['status']}")
        print(f"Input rows: {run['total_input_rows']}")
        print(f"Valid rows: {run['valid_rows']}")
        print(f"Rejected rows: {run['rejected_rows']}")
        print(f"Published rows: {run['published_rows']}")

        steps = connection.execute(
            """
            SELECT *
            FROM transformation_logs
            WHERE run_id = ?
            ORDER BY started_at
            """,
            (run_id,)
        ).fetchall()

        print("\nPIPELINE STAGE AUDIT")
        print("=" * 80)

        for step in steps:
            print(
                f"{step['step_name']} | "
                f"{step['status']} | "
                f"{step['input_rows']} -> "
                f"{step['output_rows']} rows"
            )


if __name__ == "__main__":

    run_id = input("Enter Pipeline Run ID: ").strip()

    inspect_pipeline_run(run_id)
