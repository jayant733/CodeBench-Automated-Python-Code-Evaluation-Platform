def collect_paginated_results(fetch_page, *, start_cursor=None, max_pages=100) -> list:
    """Incorrectly traverse without enforcing max_pages."""
    results = []
    cursor = start_cursor
    seen = set()

    while True:
        if cursor is not None:
            if cursor in seen:
                raise RuntimeError("cursor cycle detected")
            seen.add(cursor)
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
        cursor = next_cursor
