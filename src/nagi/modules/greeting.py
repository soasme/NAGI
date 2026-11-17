__all__ = ["hello", "time_of_day", "doing_well", "echo"]


def hello(turn) -> str:
    """Any friendly greeting, the time of day's among them."""
    return turn.random.choice(["Hello!", "Hi there!", "Hey! Nice to see you.", "Hi!", time_of_day(turn)])


def time_of_day(turn) -> str:
    hour = turn.now.hour
    if 5 <= hour < 12:
        return "Good morning!"
    if 12 <= hour < 18:
        return "Good afternoon!"
    if 18 <= hour < 22:
        return "Good evening!"
    return "Hello!"


def doing_well(turn) -> str:
    return turn.random.choice(["I'm doing well, thanks!", "All good here!", "Pretty good, thanks for asking!"])


def echo(turn) -> str:
    """Greet back in their own words, like "hola" -> "Hola!"."""
    words = turn.heard.strip().rstrip("!.?,")
    return words[:1].upper() + words[1:] + "!"
