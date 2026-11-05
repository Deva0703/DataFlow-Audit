# DataFlow Audit

### Trustworthy data pipelines. Traceable records. Verifiable outcomes.

**An end-to-end, auditable data engineering solution**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-61%20passing-2E8B57?logo=pytest&logoColor=white)
![Pipeline](https://img.shields.io/badge/Pipeline-Auditable-6C63FF)

------------------------------------------------------------------------

## At a glance

DataFlow Audit is a Python-based data engineering pipeline that ingests
structured CSV data, validates it, transforms it into order-level facts,
publishes the results and records how those outputs relate to their
source records.

> **A trustworthy data pipeline should explain what it processed, what
> it rejected, what it published, and where every published record came
> from.**

| Capability    | What it provides                                          |
|---------------|-----------------------------------------------------------|
| Data quality  | Schema, record and relationship validation                |
| Traceability  | Run IDs, file hashes and source-to-output lineage         |
| Reliability   | Idempotent publishing, retries and checkpoint recovery    |
| Verification  | Four reconciliation checks                                |
| Observability | Execution history, stage logs, counts and failure details |

## Project results

The following figures are from the project's locally recorded benchmark
and latest verified test run.

| Automated tests | Largest benchmark | Published order facts | Lineage relationships |
|----------------:|------------------:|----------------------:|----------------------:|
|   **61 passed** |  **180,257 rows** |            **50,000** |           **225,257** |

### Performance benchmark results

| Dataset | Input rows | Execution time |           Throughput |
|---------|-----------:|---------------:|---------------------:|
| Small   |      1,807 |      1.459 sec | 1,238.50 records/sec |
| Medium  |     35,801 |      5.003 sec | 7,155.87 records/sec |
| Large   |    180,257 |     21.296 sec | 8,464.53 records/sec |

Large dataset composition:

- 5,000 customers
- 50,000 orders
- 125,257 order items
- 50,000 published order facts
- 225,257 lineage relationships

Benchmarks were measured in a local Windows development environment.
Execution times vary by hardware and system configuration.

## How it works

``` mermaid
flowchart TD
    A["Customer, order and order-item CSVs"] --> B["Ingestion and SHA-256 hashing"]
    B --> C["Schema and record validation"]
    C --> D{"Validation"}
    D -->|"Valid"| E["Load source records"]
    D -->|"Invalid"| F["Rejected records with reasons"]
    E --> G["Transform and aggregate"]
    G --> H["Publish order facts"]
    H --> I[("SQLite")]
    I --> J["Source-to-output lineage"]
    I --> K["Four reconciliation checks"]
    I --> L["Checkpoint metadata"]
    J --> M["Auditable run results"]
    K --> M
    L --> N["Resume supported failed runs"]
```

### Pipeline stages

| Stage            | What happens                                                                 |
|------------------|------------------------------------------------------------------------------|
| **1. Ingest**    | Read CSV files, capture file metadata and calculate SHA-256 hashes           |
| **2. Validate**  | Check schemas, required fields, duplicate keys, data rules and foreign keys  |
| **3. Load**      | Load valid source records into relational tables and record rejected records |
| **4. Transform** | Integrate customers, orders and order items into order-level facts           |
| **5. Publish**   | Write results using UPSERT operations and database transactions              |
| **6. Trace**     | Link source records to published output records                              |
| **7. Reconcile** | Verify row counts, order counts, financial totals and lineage                |

## What makes it auditable?

### Run-level audit trail

Each execution receives a unique **Run ID**. The pipeline records
execution timestamps, input file details, processing stages, row counts,
rejected records, published counts, status and error information.

### Data lineage

Lineage connects the original source records to their published output
records.

| Lineage field    | Meaning                       |
|------------------|-------------------------------|
| Run ID           | Pipeline execution identifier |
| File ID          | Source file identifier        |
| Source Record ID | Original source record        |
| Output Table     | Destination table             |
| Output Record ID | Published record identifier   |
| Published At     | Publication timestamp         |

This supports tracing order facts back to their source customer, order
and order-item records.

### Reconciliation before success

The pipeline performs four checks:

1.  **Input row reconciliation** — valid and rejected records account
    for input rows.
2.  **Order count reconciliation** — compare valid, transformed and
    published order counts.
3.  **Amount reconciliation** — compare source and published financial
    totals.
4.  **Lineage reconciliation** — compare expected and recorded lineage
    relationships.

**All four checks must pass for the pipeline to be marked successful.**

## Reliability and recovery

### Safe reruns

Publishing uses UPSERT operations to avoid creating duplicate output
records when a pipeline is rerun. Database transactions provide rollback
support for failed publishing operations.

### Retry handling

- Configurable maximum retry attempts.
- Exponential backoff between attempts.
- Selective exception handling.
- Logging of retry attempts and final failures.

### Checkpoint-based recovery

- Persist intermediate stage outputs as local checkpoint artifacts.
- Store checkpoint metadata in SQLite.
- Record source manifests using SHA-256 hashes.
- Verify artifact integrity before restoring a checkpoint.
- Reject restoration if source files have changed.
- Resume supported pipeline runs that have been recorded as failed.

Checkpoint metadata is stored in `pipeline_checkpoints`; artifacts are
stored locally under `data/checkpoints/`.

**Recovery boundary:** The implemented flow supports recorded failed
runs. Automatic recovery of an abrupt process termination that leaves a
run marked `RUNNING` is not guaranteed.

**Checkpoint safety:** Checkpoint artifacts use Python pickle
serialization. Only load trusted, locally generated checkpoint files.
Never load checkpoint files from untrusted sources.

## Data quality checks

The validation layer covers:

- Missing required fields and columns.
- Unexpected columns and schema drift.
- Duplicate primary keys.
- Invalid email formats.
- Invalid foreign-key references.
- Invalid quantities and prices.
- Missing, empty and malformed CSV files.

Invalid records are captured with source information and rejection
reasons. The pipeline can continue processing valid records where
supported by the validation flow.

## Database overview

SQLite stores business data, published outputs and pipeline audit
information.

### Business tables

| Table                  | Purpose                        |
|------------------------|--------------------------------|
| `customers`            | Customer information           |
| `orders`               | Order information              |
| `order_items`          | Individual order items         |
| `order_facts`          | Consolidated order-level facts |
| `order_status_history` | Order status history           |

### Audit tables

| Table                  | Purpose                                      |
|------------------------|----------------------------------------------|
| `pipeline_runs`        | Pipeline execution history                   |
| `input_files`          | Source file metadata                         |
| `transformation_logs`  | Processing stage information                 |
| `rejected_records`     | Rejected records and reasons                 |
| `output_lineage`       | Source-to-output relationships               |
| `pipeline_checkpoints` | Checkpoint metadata and recovery information |

Primary keys, foreign keys, uniqueness constraints and indexes support
relational integrity and query efficiency.

## Technology

| Technology    | Role                                    |
|---------------|-----------------------------------------|
| Python        | Pipeline implementation                 |
| Pandas        | Data manipulation and transformation    |
| SQLite / SQL  | Relational storage and data operations  |
| Pytest        | Automated tests                         |
| Faker / NumPy | Synthetic data generation               |
| Hashlib       | SHA-256 file hashing                    |
| Pickle        | Local checkpoint artifact serialization |
| Logging       | Execution and failure logging           |
| Git / GitHub  | Version control                         |

## Quick start

### 1. Clone the repository

``` bash
git clone https://github.com/Devaraj0703/DataFlow-Audit.git
cd DataFlow-Audit
```

### 2. Create and activate a virtual environment

``` bash
python -m venv venv
```

Windows PowerShell:

``` powershell
.\venv\Scripts\Activate.ps1
```

Linux / macOS:

``` bash
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Run the pipeline

``` bash
python main.py
```

The default database location is:

``` text
data/dataflow_audit.db
```

The pipeline processes the sample customer, order and order-item CSV
files and produces transformed records, audit information, lineage and
reconciliation results.

## Run the tests

``` bash
python -m pytest -v
```

### Latest verified test result

| Metric         |       Result |
|----------------|-------------:|
| Total tests    |           61 |
| Passed         |           61 |
| Failed         |            0 |
| Execution time | 3.81 seconds |

Verified locally using Python 3.13.7 and pytest 9.2.0 on Windows.

Test areas include ingestion, validation, transformation, publishing,
database behavior, reconciliation, idempotency, failure handling,
late-arriving data, retry handling, checkpoint integrity and same-run
recovery.

## Run the benchmark

``` bash
python benchmark.py
```

Benchmark results are hardware-dependent.

## Repository layout

``` text
DataFlow-Audit/
├── data/
│   ├── input/
│   │   └── edge_cases/
│   ├── sample/
│   ├── output/
│   ├── quarantine/
│   ├── benchmarks/
│   └── checkpoints/              # Generated local artifacts
├── src/
│   ├── database.py
│   ├── data_generator.py
│   ├── edge_case_generator.py
│   ├── ingestion.py
│   ├── validation.py
│   ├── transformation.py
│   ├── publishing.py
│   ├── pipeline.py
│   ├── reconciliation.py
│   ├── retry.py
│   └── checkpoints.py
├── tests/
│   ├── test_database.py
│   ├── test_data_generator.py
│   ├── test_ingestion.py
│   ├── test_validation.py
│   ├── test_transformation.py
│   ├── test_publishing.py
│   ├── test_reconciliation.py
│   ├── test_retry.py
│   ├── test_checkpoints.py
│   ├── test_pipeline_failure.py
│   ├── test_pipeline_idempotency.py
│   ├── test_pipeline_recovery.py
│   ├── test_pipeline_checkpoint_recovery.py
│   ├── test_pipeline_schema_drift.py
│   ├── test_pipeline_malformed_csv.py
│   ├── test_pipeline_rejected_records.py
│   └── test_late_arriving_data.py
├── docs/
├── prompts/
├── reports/
├── main.py
├── benchmark.py
├── inspect_audit.py
├── check_benchmark.py
├── migrate_lineage.py
├── config.yaml
├── requirements.txt
└── README.md
```

Generated databases, logs, benchmark outputs and checkpoint artifacts
may be created locally and are not necessarily tracked by Git.

## Engineering decisions

| Concern               | Approach                                                 |
|-----------------------|----------------------------------------------------------|
| Idempotency           | UPSERT-based publishing                                  |
| Data integrity        | Primary and foreign keys                                 |
| Source identification | SHA-256 file hashes                                      |
| Transaction safety    | Database transactions and rollback                       |
| Data quality          | Validation and rejection handling                        |
| Observability         | Run metadata, stage logs and failure details             |
| Traceability          | Source-to-output lineage                                 |
| Consistency           | Automated reconciliation                                 |
| Retry                 | Configurable exponential backoff                         |
| Recovery              | Persistent checkpoints for supported failed-run recovery |
| Checkpoint integrity  | SHA-256 artifact verification                            |
| Source consistency    | Source manifest verification                             |

## AI development assistance

AI tools were used as development assistance for code suggestions,
debugging guidance, test-case ideas and documentation. Suggestions were
reviewed, integrated and validated through local execution and automated
tests. Supporting prompt documentation is maintained in the `prompts/`
directory.

## Future work

Potential extensions include:

- Cloud-based deployment.
- Incremental data processing.
- Monitoring dashboard.
- Additional data source integrations.
- Distributed processing for larger workloads.
- Stronger recovery for abrupt process termination and runs left in a
  `RUNNING` state.

------------------------------------------------------------------------

**DataFlow Audit**  
*AI Data Forward Deployed Engineer Challenge*

**Make every record traceable. Make every result verifiable.**
