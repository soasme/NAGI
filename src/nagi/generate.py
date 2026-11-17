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
    """The best fit; among equal fits, such as responses taught the same prompts, the most valued.

    A response is a candidate only if it is not disliked (value ≥ 0) and
    every slot its program reads was heard.
    """
    candidates = [
        (fit.score, responses[name].value, name)
        for name, fit in fits.items()
        if responses[name].value >= 0 and responses[name].program.slots <= fit.slots.keys()
    ]
    return max(candidates)[2] if candidates else None


def generate(response: Response | None, turn: Turn) -> Turn:
    if response is None:
        turn.said.append(CONFUSED)
        return turn
    if response.think:
        turn.thoughts.append(response.think)
    response.program(turn)
    return turn
