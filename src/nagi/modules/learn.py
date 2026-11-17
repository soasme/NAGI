"""Memory operations: the only way learners change what Nagi knows.

Each adds up, so lessons can be taught in any order and repeating one does
no harm: a prompt's weight toward a completion, a completion's value, and
the facts and rules Nagi reasons with (see ``nagi.knowledge``).
"""

__all__ = ["fact", "prompt", "rule", "value"]


def prompt(lesson, text: str, completion: dict, weight: float) -> None:
    """Hearing text should lead to completion while the weight is positive."""
    prompts = lesson.brain.remember(completion)["prompts"]
    prompts[text] = prompts.get(text, 0) + weight


def value(lesson, completion: dict, delta: float) -> None:
    """How much completion is preferred; below zero it is never chosen."""
    lesson.brain.remember(completion)["value"] += delta



def fact(lesson, subject: str, relation: str, object: str) -> None:
    lesson.brain.knowledge.tell(subject, relation, object)


def rule(lesson, text: str) -> None:
    """A rule as a sentence: "{x} is {z} if {x} is {y} and {y} is {z}"."""
    lesson.brain.knowledge.rule(text)
