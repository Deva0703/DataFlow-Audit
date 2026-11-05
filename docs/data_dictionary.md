
# DataFlow Audit – Data Dictionary

## 1. Project Overview

DataFlow Audit is a Python-based data engineering pipeline
that ingests CSV files, validates records, transforms data,
publishes clean records into SQLite, and maintains an
auditable record of every pipeline execution.

## 2. Source Data

The pipeline processes three source CSV files.

### 2.1 customers.csv

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| customer_id | STRING | No | PK | Unique customer identifier |
| customer_name | STRING | No | - | Customer full name |
| email | STRING | No | - | Customer email address |
| registration_date | DATE | No | - | Customer registration date |

### 2.2 orders.csv

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| order_id | STRING | No | PK | Unique order identifier |
| customer_id | STRING | No | FK | Reference to customers |
| order_date | DATETIME | No | - | Date and time of order |
| order_status | STRING | No | - | Current order status |
| updated_at | DATETIME | No | - | Last order update timestamp |

### 2.3 order_items.csv

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| item_id | STRING | No | PK | Unique order item identifier |
| order_id | STRING | No | FK | Reference to orders |
| product_id | STRING | No | - | Product identifier |
| product_name | STRING | No | - | Product name |
| quantity | INTEGER | No | - | Number of units ordered |
| unit_price | DECIMAL | No | - | Price per unit |

## 3. Target Tables

### 3.1 customers

Stores validated customer records.

### 3.2 orders

Stores validated order records.

### 3.3 order_items

Stores validated order item records.

### 3.4 order_facts

Stores transformed analytical order data.

| Column | Data Type | Description |
|---|---|---|
| order_id | STRING | Unique order identifier |
| customer_id | STRING | Customer identifier |
| customer_name | STRING | Customer name |
| total_items | INTEGER | Total quantity of items |
| total_amount | DECIMAL | Calculated order amount |
| order_status | STRING | Current order status |
| order_date | DATETIME | Order date |

## 4. Relationships

- One customer can have multiple orders.
- One order belongs to one customer.
- One order can contain multiple order items.
- Each order item belongs to one order.

## 5. Primary and Foreign Keys

| Table | Key | Type |
|---|---|---|
| customers | customer_id | Primary Key |
| orders | order_id | Primary Key |
| orders | customer_id | Foreign Key |
| order_items | item_id | Primary Key |
| order_items | order_id | Foreign Key |

## 6. Business Rules

1. Primary keys must be unique and non-null.
2. Customer IDs must exist before an order is accepted.
3. Order IDs must exist before an order item is accepted.
4. Customer names and email addresses are required.
5. Quantity must be greater than zero.
6. Unit price cannot be negative.
7. Order status must belong to an approved list of statuses.
8. Duplicate records must be detected.
9. Invalid records must be quarantined with rejection reasons.
10. Published records must be traceable to their source files.

## 7. Transformation Rules

- Calculate total_items by summing item quantities per order.
- Calculate total_amount using quantity multiplied by unit_price.
- Join orders with customers to obtain customer information.
- Generate order_facts from validated source records.
- Apply deterministic transformations.

## 8. Naming and Timestamp Conventions

- Table and column names use snake_case.
- Business identifiers use stable IDs.
- Timestamps use ISO-8601 format in UTC.
- Database timestamps are stored consistently.
- Monetary calculations must avoid floating-point precision errors.

## 9. Data Quality and Rejection Rules

The pipeline must identify:

- Missing required fields.
- Duplicate primary keys.
- Invalid data types.
- Invalid foreign keys.
- Unexpected columns or missing schema fields.
- Invalid quantities and prices.
- Malformed input files.

Rejected records must retain source file information,
source record identification, run ID and rejection reason.

## 10. Assumptions

- The source data is synthetic.
- CSV files are the initial data source.
- SQLite is the target relational database.
- Each business entity has a stable identifier.
- Order status changes must be preserved in history.
- The pipeline must support safe reruns and retries.
