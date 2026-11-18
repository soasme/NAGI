__all__ = ["answer", "say"]


def say(turn, text: str) -> None:
    turn.said.append(text)


def answer(turn, text: str, *more: str) -> None:
    """Say a short answer as a sentence: "moo" is said "Moo.", and "s", "w" is said "S, w."."""
    text = ", ".join([text, *more])
    text = text[:1].upper() + text[1:]
    turn.said.append(text if text[-1:] in (".", "!", "?") else text + ".")
