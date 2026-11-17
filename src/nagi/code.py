"""Code mode: responses and learners are small programs calling Nagi's modules.

A program is Python syntax restricted to calls of ``module.function(...)`` and
number or string literals, one call per line::

    speech.say(greeting.hello())

``module.function`` names a function listed in ``__all__`` of a registered
module (see ``nagi.plugins``); each takes the current context first.
Responses run on a ``Turn`` and call ``nagi.modules``. Learners run on a
``Lesson``, call ``nagi.learning`` (such as ``learn.prompt``), and may read
the lesson's ``record`` and its fields (``record.prompt``). Responses may
read the words heard in a slot of their prompt (``slot.thing``).

A program is checked and compiled once into closures with every function
already resolved, so running it costs only the calls: no parsing, lookup, or
``exec`` per run. Modules are imported only when a program first uses them.
"""

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from random import Random

from nagi import plugins
from nagi.knowledge import Knowledge


@dataclass
class Turn:
    """One exchange: what Nagi heard, and what it thought and said.

    ``residue`` holds the words Nagi read as not part of the intent, as said:
    in "add oat milk to my list" taught as "add to my list", ``["oat",
    "milk"]``. ``slots`` holds the words heard in each slot of the prompt
    taught: "is a whale a fish" taught as "is a {thing} a {kind}" gives
    ``{"thing": "whale", "kind": "fish"}``. ``knowledge`` is what Nagi
    knows and reasons with (see ``nagi.knowledge``). ``state`` is kept in memory between turns; each module keeps
    its data under its own name, as in ``turn.state.setdefault("todo", [])``.
    """

    heard: str
    now: datetime = field(default_factory=datetime.now)
    random: Random = field(default_factory=Random)
    residue: list[str] = field(default_factory=list)
    slots: dict[str, str] = field(default_factory=dict)
    state: dict = field(default_factory=dict)
    knowledge: Knowledge = field(default_factory=lambda: Knowledge([], []))
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
            case ast.Attribute(value=ast.Name(id="slot"), attr=name) if not self.learning:
                return lambda context: context.slots.get(name, "")
            case ast.Call(func=func, args=args, keywords=[]):
                function, args = self.resolve(func), [self.expression(arg) for arg in args]
                return lambda context: function(context, *[arg(context) for arg in args])
        raise ValueError(f"not allowed in code mode: {ast.unparse(node)}")

    def resolve(self, node: ast.expr) -> Callable:
        match node:
            case ast.Attribute(value=ast.Name(id=module), attr=name):
                found = plugins.module(module, learner=self.learning)
                if name in getattr(found, "__all__", ()):
                    return getattr(found, name)
        who, group = ("a learner", "learning") if self.learning else ("a response", "module")
        raise ValueError(
            f"not a function {who} may call: {ast.unparse(node)} "
            f"(is it in the {group} list of `nagi plugins`, and in its module's __all__?)"
        )
