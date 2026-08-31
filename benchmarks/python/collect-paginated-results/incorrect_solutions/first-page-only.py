def collect_paginated_results(fetch_page, *, start_cursor=None, max_pages=100) -> list:
    """Incorrectly stop after the first page."""
    page = fetch_page(start_cursor)
    return list(page["items"])
