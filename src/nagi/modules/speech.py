__all__ = ["say"]


def say(turn, text: str) -> None:
    turn.said.append(text)
