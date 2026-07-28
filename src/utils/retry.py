def calculate_retry_delay(
    base_seconds: int,
    attempt: int,
    max_seconds: int,
) -> int:
    if attempt < 1:
        raise ValueError("attempt must be at least 1")
    return min(base_seconds * (2 ** (attempt - 1)), max_seconds)
