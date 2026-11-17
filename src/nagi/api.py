"""What plugins build on. Stable within a major ``VERSION``.

A plugin module's functions take a ``Turn`` first::

    from nagi.api import Turn

    __all__ = ["hello"]

    def hello(turn: Turn) -> str:
        return "Hello!"
"""

from nagi.code import Turn

VERSION = 1

__all__ = ["Turn", "VERSION"]
