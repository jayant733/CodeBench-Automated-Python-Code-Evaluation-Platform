def deduplicate_records(
    records: list[dict], key: str = "id"
) -> list[dict]:
    """Return first-seen records for each distinct key value."""
    if not isinstance(records, list):
        raise TypeError("records must be a list")

    seen: set[object] = set()
    result: list[dict] = []
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("every record must be a dictionary")
        if key not in record:
            raise ValueError(f"record is missing key: {key}")
        value = record[key]
        try:
            already_seen = value in seen
        except TypeError as exc:
            raise TypeError("record key values must be hashable") from exc
        if not already_seen:
            seen.add(value)
            result.append(record.copy())
    return result

