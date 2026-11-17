"""Code mode: responses and learners are small programs calling Nagi's modules.

A program is Python syntax restricted to calls of ``module.function(...)`` and
number or string literals, one call per line::

    speech.say(greeting.hello())

``module.function`` names a function listed in ``__all__`` of
``nagi.modules.<module>``; each takes the current context first. Responses
run on a ``Turn`` and may call any module but ``learn``. Learners run on a
lesson, may call only ``learn``, and may read the lesson's ``record`` and its
fields (``record.prompt``).

A program is checked and compiled once into closures with every function
already resolved, so running it costs only the calls: no parsing, lookup, or
``exec`` per run. Modules are imported only when a program first uses them.
"""

import ast
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from random import Random


@dataclass
class Turn:
    """One exchange: what Nagi heard, and what it thought and said."""

    heard: str
    now: datetime = field(default_factory=datetime.now)
    random: Random = field(default_factory=Random)
    thoughts: list[str] = field(default_factory=list)
    said: list[str] = field(default_factory=list)


Step = Callable[[object], object]


class Program:
    def __init__(self, code: str, learning: bool = False):
        self.code = code
        self.learning = learning
        self.steps = []
        for node in ast.parse(code).body:
            if not isinstance(node, ast.Expr):
                raise ValueError(f"not allowed in code mode: {ast.unparse(node)}")
            self.steps.append(self.expression(node.value))

    def __call__(self, context) -> None:
        for step in self.steps:
            step(context)

    def expression(self, node: ast.expr) -> Step:
        match node:
            case ast.Constant(value=str() | int() | float() as value):
                return lambda context: value
            case ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=int() | float() as value)):
                return lambda context: -value
            case ast.Name(id="record") if self.learning:
                return lambda context: context.record
            case ast.Attribute(value=ast.Name(id="record"), attr=name) if self.learning:
                return lambda context: context.record[name]
            case ast.Call(func=func, args=args, keywords=[]):
                function, args = self.resolve(func), [self.expression(arg) for arg in args]
                return lambda context: function(context, *[arg(context) for arg in args])
        raise ValueError(f"not allowed in code mode: {ast.unparse(node)}")

    def resolve(self, node: ast.expr) -> Callable:
        match node:
            case ast.Attribute(value=ast.Name(id=module), attr=name) if (module == "learn") == self.learning:
                try:
                    found = importlib.import_module(f"nagi.modules.{module}")
                except ModuleNotFoundError:
                    found = None
                if name in getattr(found, "__all__", ()):
                    return getattr(found, name)
        who = "a learner" if self.learning else "a response"
        raise ValueError(f"not a Nagi module function {who} may call: {ast.unparse(node)}")
