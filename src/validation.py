
import pandas as pd


# -----------------------------------------
# SCHEMA DEFINITIONS
# -----------------------------------------

SCHEMAS = {
    "customers": {
        "required_columns": [
            "customer_id",
            "customer_name",
            "email",
            "registration_date"
        ],
        "primary_key": "customer_id",
        "required_fields": [
            "customer_id",
            "customer_name",
            "email",
            "registration_date"
        ]
    },

    "orders": {
        "required_columns": [
            "order_id",
            "customer_id",
            "order_date",
            "order_status",
            "updated_at"
        ],
        "primary_key": "order_id",
        "required_fields": [
            "order_id",
            "customer_id",
            "order_date",
            "order_status",
            "updated_at"
        ]
    },

    "order_items": {
        "required_columns": [
            "item_id",
            "order_id",
            "product_id",
            "product_name",
            "quantity",
            "unit_price"
        ],
        "primary_key": "item_id",
        "required_fields": [
            "item_id",
            "order_id",
            "product_id",
            "product_name",
            "quantity",
            "unit_price"
        ]
    }
}


# -----------------------------------------
# SCHEMA VALIDATION
# -----------------------------------------

def validate_schema(df, entity):

    schema = SCHEMAS[entity]

    expected = set(schema["required_columns"])
    actual = set(df.columns)

    missing = expected - actual
    unexpected = actual - expected

    if missing or unexpected:

        errors = []

        if missing:
            errors.append(
                f"Missing columns: {sorted(missing)}"
            )

        if unexpected:
            errors.append(
                f"Unexpected columns: {sorted(unexpected)}"
            )

        raise ValueError("; ".join(errors))


# -----------------------------------------
# RECORD VALIDATION
# -----------------------------------------

def validate_records(df, entity, valid_reference_ids=None):

    validate_schema(df, entity)

    schema = SCHEMAS[entity]

    working = df.copy().reset_index(drop=True)

    # Preserve original source row numbers.
    working.insert(
        0,
        "source_row_number",
        range(2, len(working) + 2)
    )

    errors = {
        index: []
        for index in working.index
    }

    # Check required fields
    for field in schema["required_fields"]:

        missing = (
            working[field].isna()
            | working[field].astype("string").str.strip().eq("")
        )

        for index in working.index[missing]:
            errors[index].append(
                f"Missing required field: {field}"
            )

    # Check duplicate primary keys
    primary_key = schema["primary_key"]

    duplicate_mask = (
        working[primary_key].notna()
        & working[primary_key].duplicated(keep="first")
    )

    for index in working.index[duplicate_mask]:
        errors[index].append(
            f"Duplicate primary key: {primary_key}"
        )

    # Check entity-specific rules
    if entity == "customers":

        email_mask = (
            working["email"].notna()
            & ~working["email"].astype("string").str.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                na=False
            )
        )

        for index in working.index[email_mask]:
            errors[index].append("Invalid email format")

    elif entity == "orders":

        allowed_statuses = {
            "placed",
            "processing",
            "shipped",
            "delivered",
            "cancelled"
        }

        invalid_status = (
            working["order_status"].notna()
            & ~working["order_status"].isin(allowed_statuses)
        )

        for index in working.index[invalid_status]:
            errors[index].append("Invalid order status")

        if valid_reference_ids is not None:

            invalid_customer = (
                working["customer_id"].notna()
                & ~working["customer_id"].isin(valid_reference_ids)
            )

            for index in working.index[invalid_customer]:
                errors[index].append(
                    "Invalid customer foreign key"
                )

    elif entity == "order_items":

        quantity = pd.to_numeric(
            working["quantity"],
            errors="coerce"
        )

        invalid_quantity = (
            quantity.isna()
            | (quantity <= 0)
            | (quantity % 1 != 0)
        )

        for index in working.index[invalid_quantity]:
            errors[index].append(
                "Quantity must be a positive integer"
            )

        price = pd.to_numeric(
            working["unit_price"],
            errors="coerce"
        )

        invalid_price = (
            price.isna()
            | (price < 0)
        )

        for index in working.index[invalid_price]:
            errors[index].append(
                "Unit price must be a valid non-negative number"
            )

        if valid_reference_ids is not None:

            invalid_order = (
                working["order_id"].notna()
                & ~working["order_id"].isin(valid_reference_ids)
            )

            for index in working.index[invalid_order]:
                errors[index].append(
                    "Invalid order foreign key"
                )

    # Separate valid and rejected records
    working["rejection_reason"] = [
        "; ".join(errors[index])
        for index in working.index
    ]

    rejected_mask = working["rejection_reason"] != ""

    valid_records = working.loc[
        ~rejected_mask
    ].copy()

    rejected_records = working.loc[
        rejected_mask
    ].copy()

    return valid_records, rejected_records


# -----------------------------------------
# VALIDATION SUMMARY
# -----------------------------------------

def print_validation_summary(entity, valid, rejected):

    print(f"\nValidation results: {entity}")

    print(f"Valid records: {len(valid)}")

    print(f"Rejected records: {len(rejected)}")

    print(
        f"Total processed: {len(valid) + len(rejected)}"
    )


if __name__ == "__main__":

    print("Data validation module loaded successfully.")
