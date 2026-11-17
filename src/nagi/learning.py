"""Learning: a small kernel, and learners taught as data.

The kernel knows only one kind of record by itself, a learner::

    {"learner": "sft",
     "shape": {"prompt": "text", "completion": "completion"},
     "code": "learn.prompt(record.prompt, record.completion, 1)"}

Every other record is learned by the most recently taught learner whose
shape it fits: exactly the shape's keys, each value of the shape's type. The
learner's program changes memory only through ``learn.*`` (see
``nagi.modules.learn``). Teaching a learner under an existing name replaces
it, so Nagi can be taught to learn differently.
"""

from collections.abc import Callable
from dataclasses import dataclass

from nagi.code import Program

TYPES: dict[str, Callable[[object], bool]] = {
    "text": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool),
    "completion": lambda v: isinstance(v, dict)
    and isinstance(v.get("code"), str)
    and isinstance(v.get("think", ""), str),
}


@dataclass
class Lesson:
    """What a learner runs on: the record, and the brain it teaches."""

    brain: object
    record: dict


class Learner:
    def __init__(self, shape: dict[str, str], code: str):
        if not isinstance(shape, dict) or not shape or not set(shape.values()) <= TYPES.keys():
            raise ValueError(f"a shape maps keys to {', '.join(TYPES)}: {shape!r}")
        self.shape = shape
        self.program = Program(code, learning=True)

    def fits(self, record: dict) -> bool:
        return record.keys() == self.shape.keys() and all(TYPES[t](record[k]) for k, t in self.shape.items())
