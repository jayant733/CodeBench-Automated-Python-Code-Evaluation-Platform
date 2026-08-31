import time


def retry(
    operation,
    *,
    max_attempts=3,
    base_delay=0.1,
    max_delay=2.0,
    sleep=time.sleep,
):
    """Incorrectly interpret max_attempts as the number of retries."""
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be an integer of at least 1")
    if (
        isinstance(base_delay, bool)
        or not isinstance(base_delay, (int, float))
        or base_delay < 0
        or isinstance(max_delay, bool)
        or not isinstance(max_delay, (int, float))
        or max_delay < 0
    ):
        raise ValueError("delays must be non-negative numbers")

    for attempt in range(max_attempts + 1):
        try:
            return operation()
        except Exception:
            if attempt == max_attempts:
                raise
            sleep(min(base_delay * 2**attempt, max_delay))
    raise AssertionError("unreachable")
