"""A todo list. Code mode calls these as todo.add(), todo.show(), and so on.

The item is a slot of the prompts taught: taught "add {item} to my list",
Nagi reads "add oat milk to my list" as ``todo.add(slot.item)`` with the
item "oat milk". The list lives in ``turn.state``, so it is kept between
turns.
"""

from nagi.api import Turn

__all__ = ["add", "show", "done", "clear"]


def items(turn: Turn) -> list[str]:
    return turn.state.setdefault("todo", [])


def add(turn: Turn, item: str) -> str:
    items(turn).append(item)
    return f"Added {item}."


def show(turn: Turn) -> str:
    listed = items(turn)
    if not listed:
        return "Your list is empty."
    if len(listed) == 1:
        return f"On your list: {listed[0]}."
    return f"On your list: {', '.join(listed[:-1])} and {listed[-1]}."


def done(turn: Turn, item: str) -> str:
    for listed in items(turn):
        if listed.lower() == item.lower():
            items(turn).remove(listed)
            return f"Crossed off {listed}."
    return f"{item} isn't on your list."


def clear(turn: Turn) -> str:
    count = len(items(turn))
    items(turn).clear()
    return f"Cleared {count} item{'' if count == 1 else 's'}."
