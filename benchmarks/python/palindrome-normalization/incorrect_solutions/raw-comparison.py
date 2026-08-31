def is_normalized_palindrome(value: str) -> bool:
    """Incorrectly compare the unnormalized value."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    return value == value[::-1]
