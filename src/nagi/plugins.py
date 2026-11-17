"""Plugins: how anyone's modules and curricula hook into Nagi.

A plugin is an ordinary Python package that declares entry points::

    [project.entry-points."nagi.modules"]       # responses call these
    birthdays = "nagi_birthdays"

    [project.entry-points."nagi.learning"]      # learners call these
    birthdays = "nagi_birthdays.learning"

    [project.entry-points."nagi.curricula"]
    birthdays = "nagi_birthdays.curriculum"

A module is any Python module whose ``__all__`` functions take the context
first (see ``nagi.api``): a ``Turn`` for modules responses call, a
``Lesson`` for modules learners call. Code mode calls either as
``birthdays.when()``. A curriculum
is a package directory of tiers ``t0/``, ``t1/``, … holding teaching assets
and eval sets (``*.eval.jsonl``). Nagi registers its own modules and its
curriculum the same way, so core is just the first plugin. Names share one
namespace per group, and two packages registering the same name in a group
is an error.
"""

import re
from functools import cache
from importlib import import_module
from importlib.metadata import entry_points
from importlib.resources import files
from importlib.resources.abc import Traversable
from types import ModuleType


def registry(group: str) -> dict[str, str]:
    found: dict[str, tuple[str, str]] = {}
    for point in entry_points(group=group):
        package = point.dist.name if point.dist else "?"
        if point.name in found and found[point.name][0] != point.value:
            raise ValueError(f"{group} {point.name!r} is registered by both {found[point.name][1]} and {package}")
        found[point.name] = (point.value, package)
    return {name: value for name, (value, _) in found.items()}


@cache
def modules() -> dict[str, str]:
    return registry("nagi.modules")


@cache
def learning() -> dict[str, str]:
    return registry("nagi.learning")


@cache
def curricula() -> dict[str, str]:
    return registry("nagi.curricula")


def module(name: str, learner: bool = False) -> ModuleType | None:
    """A module responses may call, or with ``learner``, one learners may call."""
    path = (learning() if learner else modules()).get(name)
    return import_module(path) if path else None


def files_of(name: str) -> list[Traversable]:
    """Every file of a curriculum, tier by tier, in name order within a tier."""
    if name not in curricula():
        raise ValueError(f"no curriculum named {name!r}; installed: {', '.join(sorted(curricula()))}")
    root = files(curricula()[name])
    tiers = sorted((t for t in root.iterdir() if re.fullmatch(r"t\d+", t.name)), key=lambda t: int(t.name[1:]))
    return [f for tier in tiers for f in sorted(tier.iterdir(), key=lambda f: f.name) if f.name.endswith(".jsonl")]


def curriculum(name: str = "nagi") -> list[Traversable]:
    """A curriculum's teaching assets, in the order they are taught."""
    return [f for f in files_of(name) if not f.name.endswith(".eval.jsonl")]


def evals(name: str = "nagi") -> list[Traversable]:
    """A curriculum's eval sets, never taught."""
    return [f for f in files_of(name) if f.name.endswith(".eval.jsonl")]
