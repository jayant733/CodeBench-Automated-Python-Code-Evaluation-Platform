from collections.abc import Callable
from typing import Any


def collect_paginated_results(
    fetch_page: Callable[[str | None], dict[str, Any]],
    *,
    start_cursor: str | None = None,
    max_pages: int = 100,
) -> list[Any]:
    """Collect items from a cursor-paginated API."""
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages must be an integer of at least 1")
    if start_cursor is not None and not isinstance(start_cursor, str):
        raise ValueError("start_cursor must be a string or None")

    results: list[Any] = []
    cursor = start_cursor
    seen_cursors: set[str] = set()

    for page_number in range(max_pages):
        if cursor is not None:
            if cursor in seen_cursors:
                raise RuntimeError("cursor cycle detected")
            seen_cursors.add(cursor)

        page = fetch_page(cursor)
        if not isinstance(page, dict):
            raise ValueError("page must be a dictionary")
        items = page.get("items")
        next_cursor = page.get("next_cursor")
        if not isinstance(items, list):
            raise ValueError("page items must be a list")
        if next_cursor is not None and not isinstance(next_cursor, str):
            raise ValueError("next_cursor must be a string or None")

        results.extend(items)
        if next_cursor is None:
            return results
        if page_number == max_pages - 1:
            raise RuntimeError("page limit exceeded")
        cursor = next_cursor

    raise RuntimeError("page limit exceeded")
