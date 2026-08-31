def is_normalized_palindrome(value: str) -> bool:
    """Return whether value is a palindrome after normalization."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    normalized = [character.casefold() for character in value if character.isalnum()]
    return normalized == normalized[::-1]

