__all__ = ["hello"]


def hello(turn) -> str:
    """A greeting that fits the time of day."""
    hour = turn.now.hour
    if 5 <= hour < 12:
        return "Good morning!"
    if 12 <= hour < 18:
        return "Good afternoon!"
    if 18 <= hour < 22:
        return "Good evening!"
    return "Hello!"
