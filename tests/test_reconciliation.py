
from src.reconciliation import (
    reconcile_row_counts,
    reconcile_order_counts,
    reconcile_amounts
)


def test_row_counts_match():
    result = reconcile_row_counts(
        total_input_rows=100,
        valid_rows=90,
        rejected_rows=10
    )

    assert result["passed"] is True
    assert result["expected"] == 100
    assert result["actual"] == 100


def test_row_counts_do_not_match():
    result = reconcile_row_counts(
        total_input_rows=100,
        valid_rows=85,
        rejected_rows=10
    )

    assert result["passed"] is False


def test_order_counts_match():
    result = reconcile_order_counts(
        valid_order_count=500,
        transformed_order_count=500,
        published_order_count=500
    )

    assert result["passed"] is True


def test_order_counts_do_not_match():
    result = reconcile_order_counts(
        valid_order_count=500,
        transformed_order_count=490,
        published_order_count=490
    )

    assert result["passed"] is False


def test_amounts_match():
    result = reconcile_amounts(
        source_total_cents=100000,
        published_total_cents=100000
    )

    assert result["passed"] is True
    assert result["difference_cents"] == 0


def test_amounts_do_not_match():
    result = reconcile_amounts(
        source_total_cents=100000,
        published_total_cents=95000
    )

    assert result["passed"] is False
    assert result["difference_cents"] == 5000
