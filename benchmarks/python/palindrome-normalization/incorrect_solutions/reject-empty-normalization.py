def is_normalized_palindrome(value: str) -> bool:
    """Incorrectly require at least one normalized character."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    normalized = [character.casefold() for character in value if character.isalnum()]
    return bool(normalized) and normalized == normalized[::-1]
