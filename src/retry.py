
import logging
import time


logger = logging.getLogger(__name__)


def retry_operation(
    operation,
    *,
    max_attempts=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    retry_exceptions=(Exception,),
    sleep=time.sleep
):
    """
    Retry an operation with exponential backoff.

    Delays for the default configuration:
    Attempt 1 -> immediate
    Attempt 2 -> 1 second
    Attempt 3 -> 2 seconds

    Raises the final exception when all attempts fail.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if initial_delay < 0:
        raise ValueError("initial_delay cannot be negative")

    if backoff_factor < 1:
        raise ValueError("backoff_factor must be at least 1")

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except retry_exceptions as error:
            if attempt == max_attempts:
                logger.error(
                    "Operation failed after %s attempts: %s",
                    attempt,
                    error
                )
                raise

            delay = initial_delay * (
                backoff_factor ** (attempt - 1)
            )

            logger.warning(
                "Attempt %s/%s failed: %s. "
                "Retrying in %.2f seconds.",
                attempt,
                max_attempts,
                error,
                delay
            )

            sleep(delay)
