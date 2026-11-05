
import pytest

from src.retry import retry_operation


def test_retry_succeeds_after_transient_failures():
    attempts = {"count": 0}
    delays = []

    def operation():
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise ConnectionError("Temporary connection failure")

        return "success"

    result = retry_operation(
        operation,
        max_attempts=3,
        initial_delay=1,
        sleep=delays.append
    )

    assert result == "success"
    assert attempts["count"] == 3
    assert delays == [1, 2]


def test_retry_raises_after_maximum_attempts():
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise ConnectionError("Service unavailable")

    with pytest.raises(ConnectionError):
        retry_operation(
            operation,
            max_attempts=3,
            initial_delay=0,
            sleep=lambda _: None
        )

    assert attempts["count"] == 3


def test_retry_does_not_retry_unlisted_exception():
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise ValueError("Invalid input")

    with pytest.raises(ValueError):
        retry_operation(
            operation,
            max_attempts=3,
            retry_exceptions=(ConnectionError,),
            sleep=lambda _: None
        )

    assert attempts["count"] == 1


def test_retry_rejects_invalid_attempt_count():
    with pytest.raises(ValueError):
        retry_operation(
            lambda: "success",
            max_attempts=0
        )
