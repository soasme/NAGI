"""A todo list. Code mode calls these as todo.add(), todo.show(), and so on.

The item is whatever Nagi heard but wasn't taught (``turn.residue``): taught
"add to my list", it reads "add oat milk to my list" as adding "oat milk".
The list lives in ``turn.state``, so it is kept between turns.
"""

from nagi.api import Turn

__all__ = ["add", "show", "done", "clear"]


def items(turn: Turn) -> list[str]:
    return turn.state.setdefault("todo", [])


def add(turn: Turn) -> str:
    item = " ".join(turn.residue)
    if not item:
        return "What should I add?"
    items(turn).append(item)
    return f"Added {item}."


def show(turn: Turn) -> str:
    listed = items(turn)
    if not listed:
        return "Your list is empty."
    if len(listed) == 1:
        return f"On your list: {listed[0]}."
    return f"On your list: {', '.join(listed[:-1])} and {listed[-1]}."


def done(turn: Turn) -> str:
    item = " ".join(turn.residue)
    for listed in items(turn):
        if listed.lower() == item.lower():
            items(turn).remove(listed)
            return f"Crossed off {listed}."
    return f"{item or 'That'} isn't on your list."


def clear(turn: Turn) -> str:
    count = len(items(turn))
    items(turn).clear()
    return f"Cleared {count} item{'' if count == 1 else 's'}."
