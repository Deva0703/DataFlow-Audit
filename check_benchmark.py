import sqlite3
import json

connection = sqlite3.connect("data/benchmarks/benchmark.db")
connection.row_factory = sqlite3.Row

query = """
SELECT run_id, details
FROM transformation_logs
WHERE step_name = 'reconciliation'
ORDER BY started_at DESC
LIMIT 3
"""

results = connection.execute(query).fetchall()

for result in results:
    print("\nRUN:", result["run_id"])
    print("RECONCILIATION DETAILS:")

    try:
        details = json.loads(result["details"])
        print(json.dumps(details, indent=4))
    except (TypeError, json.JSONDecodeError):
        print(result["details"])

connection.close()