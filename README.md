# DataFlow Audit

### Building Trustworthy, Traceable & Reliable Data Pipelines

**An end-to-end auditable data engineering solution**

![Python
3.13](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Processing-150458?logo=pandas)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite)
![Pytest](https://img.shields.io/badge/Tests-61%20passing-success?logo=pytest)
![Project](https://img.shields.io/badge/Project-Completed-success)

------------------------------------------------------------------------

## Overview

**DataFlow Audit** is a Python-based data engineering pipeline that
ingests, validates, transforms, publishes and audits structured datasets
while maintaining source-to-output traceability.

The project focuses on a core data engineering requirement: published
data should not only be processed correctly, but should also be
explainable, verifiable and recoverable.

Each pipeline execution receives a unique **Run ID**. The system records
execution metadata, data quality results, rejected records,
transformation stages, data lineage and reconciliation outcomes.

### Key capabilities

-   CSV ingestion with SHA-256 source-file hashing.
-   Schema, record and relationship validation.
-   Rejected-record capture with reasons.
-   Transformation of customer, order and order-item data into order
    facts.
-   Transaction-safe, UPSERT-based publishing.
-   Source-to-output data lineage.
-   Automated reconciliation of row counts, order counts, financial
    totals and lineage.
-   Retry handling with configurable exponential backoff.
-   Persistent checkpoints and recovery of recorded failed runs.
-   Automated tests and performance benchmarks.

## Architecture

``` mermaid
flowchart TD
    A[Source CSV files] --> B[Ingestion and file hashing]
    B --> C[Schema and data validation]
    C --> D{Validation result}
    D -->|Valid records| E[Source table loading]
    D -->|Invalid records| F[Rejected records]
    E --> G[Transformation]
    G --> H[Order fact generation]
    H --> I[Transactional publishing]
    I --> J[(SQLite database)]
    J --> K[Data lineage]
    J --> L[Reconciliation]
    J --> M[Checkpoint metadata]
    K --> N[Audit results]
    L --> N
    M --> O[Recovery of recorded failed runs]
```

### Pipeline components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Ingestion                           Reads source CSV files and captures
                                      file metadata and hashes

  Validation                          Checks schemas, required fields,
                                      record rules and relationships

  Source loading                      Loads validated records into
                                      relational tables

  Transformation                      Combines customer, order and
                                      order-item data into order facts

  Publishing                          Publishes transformed data using
                                      safe UPSERT operations and
                                      transactions

  Lineage                             Links source records to published
                                      output records

  Reconciliation                      Checks row counts, order counts,
                                      financial totals and lineage

  Retry                               Retries configured operations with
                                      exponential backoff

  Checkpoints                         Saves completed stage outputs and
                                      verifies them before restoration

  Audit logging                       Captures run history, stage
                                      information, metrics and failures
  -----------------------------------------------------------------------

## Core functionality

### 1. Ingestion

-   Reads CSV source files.
-   Calculates SHA-256 file hashes.
-   Captures file metadata and row counts.
-   Detects missing, empty and malformed files.

### 2. Data quality and validation

The validation layer checks:

-   Missing required fields and columns.
-   Unexpected columns and schema drift.
-   Duplicate primary keys.
-   Invalid email formats.
-   Invalid foreign-key references.
-   Invalid quantities and prices.

Invalid records are recorded with source information and rejection
reasons, allowing valid records to continue through the pipeline where
supported.

### 3. Transformation

Customer, order and order-item datasets are integrated to produce
consolidated order-level facts.

Key operations include:

-   Customer and order integration.
-   Order-item aggregation.
-   Total quantity calculation.
-   Financial amount calculation.
-   Handling orders without associated items.
-   Financial precision using integer cents.

### 4. Publishing

-   SQLite relational storage.
-   UPSERT-based publishing to support safe reruns.
-   Duplicate order protection.
-   Transaction handling and rollback on failed publishing operations.

### 5. Audit and observability

Each pipeline run records information such as:

-   Run ID and execution timestamps.
-   Input file details.
-   Processing stages.
-   Input, valid, rejected and published row counts.
-   Execution status.
-   Error information.

### 6. Data lineage

Lineage records connect original source records to their corresponding
published outputs.

  Field              Description
  ------------------ -------------------------------
  Run ID             Pipeline execution identifier
  File ID            Source file identifier
  Source Record ID   Original source record
  Output Table       Destination table
  Output Record ID   Published record identifier
  Published At       Publication timestamp

This supports tracing published order facts back to source customer,
order and order-item records.

### 7. Retry and checkpoint-based recovery

The pipeline includes retry handling and persistent checkpoints to
improve recovery after recorded pipeline failures.

**Retry handling**

-   Configurable maximum retry attempts.
-   Exponential backoff between attempts.
-   Selective exception handling.
-   Logging of retry attempts and final failures.

**Checkpoint handling**

-   Persists intermediate pipeline stage outputs.
-   Stores checkpoint metadata in SQLite.
-   Records source manifests using SHA-256 hashes.
-   Verifies checkpoint artifact integrity before restoration.
-   Rejects restoration when source files have changed.
-   Supports resuming recorded failed runs from completed checkpoints.

Checkpoint metadata is stored in the `pipeline_checkpoints` table. Local
checkpoint artifacts are stored under `data/checkpoints/`.

**Recovery limitation:** The implemented recovery flow supports runs
recorded as failed. Automatic recovery of a process that terminates
abruptly while its run remains marked `RUNNING` is not guaranteed.

**Checkpoint security:** Checkpoint artifacts use Python pickle
serialization. Only load trusted, locally generated checkpoint files. Do
not load checkpoint files from untrusted sources.

## Reconciliation

Four reconciliation checks are used to verify processed data:

  -----------------------------------------------------------------------
  Check                               Purpose
  ----------------------------------- -----------------------------------
  Input row reconciliation            Checks that valid and rejected
                                      records account for the input rows

  Order count reconciliation          Compares valid, transformed and
                                      published order counts

  Amount reconciliation               Compares source and published
                                      financial totals

  Lineage reconciliation              Verifies expected and recorded
                                      lineage relationships
  -----------------------------------------------------------------------

**Success condition:** All four reconciliation checks must pass.
Otherwise, the pipeline is marked as failed.

## Database design

SQLite stores business data, published outputs and audit information.

### Business tables

  Table                    Description
  ------------------------ --------------------------------
  `customers`              Customer information
  `orders`                 Order information
  `order_items`            Individual order items
  `order_facts`            Consolidated order-level facts
  `order_status_history`   Order status history

### Audit tables

  -----------------------------------------------------------------------
  Table                               Description
  ----------------------------------- -----------------------------------
  `pipeline_runs`                     Pipeline execution history

  `input_files`                       Source file metadata

  `transformation_logs`               Processing stage information

  `rejected_records`                  Rejected records and reasons

  `output_lineage`                    Source-to-output relationships

  `pipeline_checkpoints`              Checkpoint metadata and recovery
                                      information
  -----------------------------------------------------------------------

Primary keys, foreign keys, uniqueness constraints and indexes support
relational integrity and efficient queries.

## Technology stack

  Technology       Usage
  ---------------- -----------------------------------------
  Python           Pipeline implementation
  Pandas           Data manipulation and transformation
  SQLite           Relational database
  SQL              Data operations and reconciliation
  Pytest           Automated testing
  Faker            Synthetic data generation
  NumPy            Data generation
  Hashlib          SHA-256 file hashing
  Pickle           Local checkpoint artifact serialization
  Logging          Pipeline monitoring
  Git and GitHub   Version control

## Repository structure

``` text
DataFlow-Audit/
├── data/
│   ├── input/
│   │   └── edge_cases/
│   ├── sample/
│   ├── output/
│   ├── quarantine/
│   ├── benchmarks/
│   └── checkpoints/              # Generated local checkpoint artifacts
├── src/
│   ├── __init__.py
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
├── README.md
└── .gitignore
```

Generated databases, logs, benchmark outputs and checkpoint artifacts
may be created locally during execution and are not necessarily tracked
by Git.

## Setup

### Prerequisites

-   Python 3.10 or higher.
-   Git.
-   Windows, Linux or macOS.

### Clone the repository

``` bash
git clone https://github.com/Deva0703/DataFlow-Audit.git
cd DataFlow-Audit
```

### Create and activate a virtual environment

``` bash
python -m venv venv
```

Windows PowerShell:

``` powershell
.\venv\Scripts\Activate.ps1
```

Linux/macOS:

``` bash
source venv/bin/activate
```

### Install dependencies

``` bash
pip install -r requirements.txt
```

## Run the pipeline

``` bash
python main.py
```

The pipeline processes the sample customer, order and order-item CSV
files.

The execution produces pipeline details, ingestion and validation
metrics, transformed order facts, published records, audit logs, lineage
and reconciliation results. Supported stages also create checkpoint
metadata and local checkpoint artifacts.

Default database location:

``` text
data/dataflow_audit.db
```

## Automated tests

Run the full test suite:

``` bash
python -m pytest -v
```

### Latest verified test results

  Metric                   Result
  ---------------- --------------
  Total tests                  61
  Passed                       61
  Failed                        0
  Execution time     3.81 seconds

These results were verified locally using Python 3.13.7 and pytest 9.2.0
on Windows.

Test coverage includes:

-   Database initialization and constraints.
-   Synthetic data generation.
-   CSV ingestion and file hashing.
-   Missing, empty and malformed files.
-   Schema drift and unexpected columns.
-   Duplicate records and invalid references.
-   Transformation and financial calculations.
-   Publishing, transactions and rollback.
-   Idempotent reruns.
-   Pipeline failure handling and recovery.
-   Retry success, exhaustion and exception filtering.
-   Checkpoint save and restore.
-   Changed-source detection.
-   Checkpoint corruption and missing-artifact detection.
-   Late-arriving data.
-   Reconciliation checks.

## Performance benchmarks

The pipeline was evaluated using three synthetic datasets.

### Dataset configuration

  Dataset     Customers   Orders   Order items   Total input rows
  --------- ----------- -------- ------------- ------------------
  Small             100      500         1,207              1,807
  Medium          1,000   10,000        24,801             35,801
  Large           5,000   50,000       125,257            180,257

### Benchmark results

  Dataset     Execution time             Throughput
  --------- ---------------- ----------------------
  Small            1.459 sec   1,238.50 records/sec
  Medium           5.003 sec   7,155.87 records/sec
  Large           21.296 sec   8,464.53 records/sec

### Large dataset highlights

-   180,257 total input records.
-   5,000 customers.
-   50,000 orders.
-   125,257 order items.
-   50,000 published order facts.
-   225,257 lineage relationships.
-   21.296 seconds execution time.
-   8,464.53 records per second.

Run the benchmark:

``` bash
python benchmark.py
```

Benchmark results were measured in a local Windows development
environment. Execution times may vary depending on hardware and system
configuration.

## Reliability and engineering design

  -----------------------------------------------------------------------
  Principle                           Implementation
  ----------------------------------- -----------------------------------
  Idempotency                         UPSERT-based publishing

  Data integrity                      Primary and foreign keys

  File identification                 SHA-256 hashing

  Transaction safety                  Database transactions and rollback

  Data quality                        Validation and rejection handling

  Observability                       Execution logging and audit records

  Traceability                        Source-to-output lineage

  Reconciliation                      Automated consistency checks

  Performance                         Grouped operations and batched
                                      database queries

  Retry handling                      Configurable retries with
                                      exponential backoff

  Recovery                            Persistent stage checkpoints for
                                      supported failed-run recovery

  Checkpoint integrity                SHA-256 artifact verification

  Source consistency                  Source manifest verification before
                                      checkpoint restoration
  -----------------------------------------------------------------------

## AI development assistance

AI tools were used as development assistance for code suggestions,
debugging guidance, test-case ideas and documentation.

Generated suggestions were reviewed, integrated and validated through
local execution and automated testing. Development decisions,
integration, debugging and final verification were part of the project
work.

Supporting AI prompt documentation is maintained in the `prompts/`
directory.

## Future enhancements

Potential future extensions include:

-   Cloud-based deployment.
-   Incremental data processing.
-   Monitoring dashboard.
-   Additional data source integrations.
-   Distributed processing for larger workloads.
-   Stronger recovery handling for abrupt process termination and runs
    left in a `RUNNING` state.

These are potential enhancements, not completed functionality.

## Conclusion

DataFlow Audit demonstrates how an end-to-end data engineering pipeline
can combine data processing with auditability, reliability and
traceability.

By integrating ingestion, validation, transformation, publishing, data
lineage, reconciliation, retry handling, checkpoint-based recovery and
automated testing, the solution provides a foundation for building
trustworthy data workflows.

> **The goal is not just to move data. It is to make every published
> record traceable, verifiable and trustworthy.**

------------------------------------------------------------------------

**DataFlow Audit**\
*AI Data Forward Deployed Engineer Challenge*
