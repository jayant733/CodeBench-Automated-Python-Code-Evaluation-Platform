"""Execute one submission inside the disposable container.

This module intentionally depends only on the Python standard library because it
is copied into the small runner image for every evaluation.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

OUTPUT_LIMIT = 16_000


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("submission", path)
    if spec is None or spec.loader is None:
        raise ImportError("The submission module could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _same(actual: Any, expected: Any) -> bool:
    if isinstance(actual, float) and isinstance(expected, (int, float)):
        return math.isclose(actual, float(expected), rel_tol=1e-9, abs_tol=1e-9)
    return actual == expected


def _direct(function: Callable[..., Any], case: dict[str, Any]) -> tuple[bool, str | None]:
    details = case["input"]
    expected_exception = case.get("expected_exception")
    try:
        actual = function(*details.get("args", []), **details.get("kwargs", {}))
    except Exception as exc:
        if expected_exception == type(exc).__name__:
            return True, None
        return False, f"Raised {type(exc).__name__}: {str(exc)[:240]}"

    if expected_exception:
        return False, f"Expected {expected_exception}, but no exception was raised."
    if _same(actual, case.get("expected")):
        return True, None
    return False, f"Expected {case.get('expected')!r}, received {actual!r}."


def _retry(function: Callable[..., Any], case: dict[str, Any]) -> tuple[bool, str | None]:
    details = case["input"]
    calls = 0
    delays: list[float] = []

    def operation() -> Any:
        nonlocal calls
        calls += 1
        if calls <= details["failures_before_success"]:
            raise ValueError("temporary failure")
        return details.get("result")

    def sleeper(delay: float) -> None:
        delays.append(delay)

    expected_exception = case.get("expected_exception")
    try:
        actual = function(
            operation,
            max_attempts=details["max_attempts"],
            base_delay=details["base_delay"],
            max_delay=details["max_delay"],
            sleep=sleeper,
        )
    except Exception as exc:
        if expected_exception != type(exc).__name__:
            return False, f"Raised {type(exc).__name__}: {str(exc)[:240]}"
        actual = None
    else:
        if expected_exception:
            return False, f"Expected {expected_exception}, but no exception was raised."

    if calls != details["expected_calls"]:
        return False, f"Expected {details['expected_calls']} calls, observed {calls}."
    if delays != details["expected_delays"]:
        return False, f"Expected delays {details['expected_delays']!r}, received {delays!r}."
    if not expected_exception and not _same(actual, case.get("expected")):
        return False, f"Expected {case.get('expected')!r}, received {actual!r}."
    return True, None


def _pagination(function: Callable[..., Any], case: dict[str, Any]) -> tuple[bool, str | None]:
    details = case["input"]
    requested: list[str | None] = []
    pages = details["pages"]

    def fetch_page(cursor: str | None) -> dict[str, Any]:
        requested.append(cursor)
        key = "__start__" if cursor is None else cursor
        if key not in pages:
            raise LookupError(f"Unexpected cursor: {cursor}")
        return pages[key]

    expected_exception = case.get("expected_exception")
    try:
        actual = function(
            fetch_page,
            start_cursor=details.get("start_cursor"),
            max_pages=details.get("max_pages", 100),
        )
    except Exception as exc:
        if expected_exception != type(exc).__name__:
            return False, f"Raised {type(exc).__name__}: {str(exc)[:240]}"
        actual = None
    else:
        if expected_exception:
            return False, f"Expected {expected_exception}, but no exception was raised."

    if requested != details["expected_cursors"]:
        return (
            False,
            f"Expected cursor requests {details['expected_cursors']!r}, got {requested!r}.",
        )
    if not expected_exception and not _same(actual, case.get("expected")):
        return False, f"Expected {case.get('expected')!r}, received {actual!r}."
    return True, None


CASE_RUNNERS: dict[str, Callable[[Callable[..., Any], dict[str, Any]], tuple[bool, str | None]]] = {
    "direct": _direct,
    "retry": _retry,
    "pagination": _pagination,
}


def evaluate(job: dict[str, Any], submission_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    response: dict[str, Any] = {
        "imported": False,
        "function_exists": False,
        "runtime_ms": 0,
        "stdout": "",
        "stderr": "",
        "tests": [],
    }

    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        try:
            module = _load_module(submission_path)
        except Exception as exc:
            response["fatal_code"] = "import_error"
            response["fatal_message"] = f"Import failed with {type(exc).__name__}: {str(exc)[:240]}"
        else:
            response["imported"] = True
            function = getattr(module, job["function_name"], None)
            if not callable(function):
                response["fatal_code"] = "missing_function"
                response["fatal_message"] = (
                    f"Required function '{job['function_name']}' was not callable after import."
                )
            else:
                response["function_exists"] = True
                for case in job["tests"]:
                    test_started = time.perf_counter()
                    try:
                        passed, message = CASE_RUNNERS[case["mode"]](function, case)
                    except Exception as exc:
                        passed = False
                        message = f"Test harness observed {type(exc).__name__}: {str(exc)[:240]}"
                        status = "error"
                    else:
                        status = "passed" if passed else "failed"
                    response["tests"].append(
                        {
                            "id": case["id"],
                            "status": status,
                            "runtime_ms": round((time.perf_counter() - test_started) * 1000),
                            "message": message,
                        }
                    )

    response["runtime_ms"] = round((time.perf_counter() - started) * 1000)
    response["stdout"] = stdout_buffer.getvalue()[-OUTPUT_LIMIT:]
    response["stderr"] = stderr_buffer.getvalue()[-OUTPUT_LIMIT:]
    return response


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    job_path = Path(sys.argv[1])
    submission_path = Path(sys.argv[2])
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        result = evaluate(job, submission_path)
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "protocol_error": type(exc).__name__,
                    "message": str(exc)[:240],
                },
                separators=(",", ":"),
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
