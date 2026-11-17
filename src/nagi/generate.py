"""Generate: choose the most preferred response among the intents captured, and run it."""

from dataclasses import dataclass

from nagi.code import Program, Turn
from nagi.intent import Fit

CONFUSED = "...?"


@dataclass
class Response:
    think: str
    program: Program
    value: float  # preference learned from DPO and RLHF; below zero is never chosen


def choose(responses: dict[str, Response], fits: dict[str, Fit]) -> str | None:
    """The best fit; among equal fits, such as responses taught the same prompts, the most valued."""
    candidates = [(fit.score, responses[name].value, name) for name, fit in fits.items() if responses[name].value >= 0]
    return max(candidates)[2] if candidates else None


def generate(response: Response | None, turn: Turn) -> Turn:
    if response is None:
        turn.said.append(CONFUSED)
        return turn
    if response.think:
        turn.thoughts.append(response.think)
    response.program(turn)
    return turn
