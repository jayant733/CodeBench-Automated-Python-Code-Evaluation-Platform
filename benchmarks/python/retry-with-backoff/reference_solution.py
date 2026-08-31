import time
from collections.abc import Callable
from typing import Any


def retry(
    operation: Callable[[], Any],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Run operation with bounded exponential-backoff retries."""
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

    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            sleep(min(base_delay * 2**attempt, max_delay))
    raise AssertionError("unreachable")

