"""Generate: run the most preferred response among the intents captured."""

from dataclasses import dataclass

from nagi.code import Program, Turn

CONFUSED = "...?"


@dataclass
class Response:
    think: str
    program: Program
    value: float  # preference learned from DPO and RLHF; below zero is never chosen


def generate(responses: dict[str, Response], fits: dict[str, float], turn: Turn) -> Turn:
    """Prefer higher value, then a better fit."""
    candidates = [(responses[name].value, score, name) for name, score in fits.items() if responses[name].value >= 0]
    if not candidates:
        turn.said.append(CONFUSED)
        return turn
    response = responses[max(candidates)[2]]
    if response.think:
        turn.thoughts.append(response.think)
    response.program(turn)
    return turn
