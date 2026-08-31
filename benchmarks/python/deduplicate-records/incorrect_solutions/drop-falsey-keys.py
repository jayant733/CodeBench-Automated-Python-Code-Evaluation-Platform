def deduplicate_records(records: list[dict], key: str = "id") -> list[dict]:
    """Incorrectly discard records whose key value is falsey."""
    if not isinstance(records, list):
        raise TypeError("records must be a list")

    seen: set[object] = set()
    result: list[dict] = []
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("every record must be a dictionary")
        value = record.get(key)
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            result.append(record.copy())
    return result
