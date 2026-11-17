"""Memory operations: the only way learners change what Nagi knows.

Everything is a sum, so lessons add up in any order: a prompt's weight
toward a completion, and a completion's value.
"""

__all__ = ["prompt", "value"]


def prompt(lesson, text: str, completion: dict, weight: float) -> None:
    """Hearing text should lead to completion while the weight is positive."""
    prompts = lesson.brain.remember(completion)["prompts"]
    prompts[text] = prompts.get(text, 0) + weight


def value(lesson, completion: dict, delta: float) -> None:
    """How much completion is preferred; below zero it is never chosen."""
    lesson.brain.remember(completion)["value"] += delta

