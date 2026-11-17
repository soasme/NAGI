"""Code mode: a response is a small program calling Nagi's modules.

A program is Python syntax restricted to calls of ``module.function(...)`` and
string or number literals, one call per line::

    speech.say(greeting.hello())

``module.function`` names a function listed in ``__all__`` of
``nagi.modules.<module>``; each takes the current ``Turn`` first. A program is
checked and compiled once into closures with every function already resolved,
so running it costs only the calls: no parsing, lookup, or ``exec`` per turn.
Modules are imported only when a program first uses them.
"""

import ast
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Turn:
    """One exchange: what Nagi heard, and what it thought and said."""

    heard: str
    now: datetime = field(default_factory=datetime.now)
    thoughts: list[str] = field(default_factory=list)
    said: list[str] = field(default_factory=list)


Step = Callable[[Turn], object]


def resolve(node: ast.expr) -> Callable:
    match node:
        case ast.Attribute(value=ast.Name(id=module), attr=name):
            try:
                found = importlib.import_module(f"nagi.modules.{module}")
            except ModuleNotFoundError:
                found = None
            if name in getattr(found, "__all__", ()):
                return getattr(found, name)
    raise ValueError(f"not a Nagi module function: {ast.unparse(node)}")


def expression(node: ast.expr) -> Step:
    match node:
        case ast.Constant(value=str() | int() | float() as value):
            return lambda turn: value
        case ast.Call(func=func, args=args, keywords=[]):
            function, args = resolve(func), [expression(arg) for arg in args]
            return lambda turn: function(turn, *[arg(turn) for arg in args])
    raise ValueError(f"not allowed in code mode: {ast.unparse(node)}")


class Program:
    def __init__(self, code: str):
        self.code = code
        self.steps = []
        for node in ast.parse(code).body:
            if not isinstance(node, ast.Expr):
                raise ValueError(f"not allowed in code mode: {ast.unparse(node)}")
            self.steps.append(expression(node.value))

    def __call__(self, turn: Turn) -> None:
        for step in self.steps:
            step(turn)
