def deduplicate_records(records: list[dict], key: str = "id") -> list[dict]:
    """Incorrectly replace first-seen records with later duplicates."""
    by_value: dict[object, dict] = {}
    for record in records:
        by_value[record[key]] = record.copy()
    return list(by_value.values())
