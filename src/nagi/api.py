"""What plugins build on. Stable within a major ``VERSION``.

A plugin module's functions take a ``Turn`` first. A turn carries what was
heard, the words Nagi read as not part of the intent (``turn.residue``), the
words heard in the slots of the prompt taught (``turn.slots``), the time, a
random source, and ``turn.state``, which persists between turns::

    from nagi.api import Turn

    __all__ = ["hello"]

    def hello(turn: Turn) -> str:
        return "Hello!"


A module that learners call takes a ``Lesson`` first instead: the record
being learned and ``lesson.state``, the same state ``turn.state`` reads.
"""

from nagi.code import Turn
from nagi.learning import Lesson

VERSION = 1

__all__ = ["Lesson", "Turn", "VERSION"]
