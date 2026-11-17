"""Birthdays, answered. Code mode calls these as birthdays.when().

Nagi learns the birthdays from your data (see ``nagi_birthdays.learning``).
Whose birthday is asked about is a slot of the prompts taught: taught "when
is {person} birthday", it reads "when is Mei's birthday?" as
``birthdays.when(slot.person)`` with the person "Mei's".
"""

import re

from nagi.api import Turn

__all__ = ["when"]


def when(turn: Turn, person: str) -> str:
    person = re.sub(r"['’]s$", "", person)
    known = turn.state.get("birthdays", {})
    for name, day in known.items():
        if name.lower() == person.lower():
            return f"{name}'s birthday is {day}."
    return f"I don't know when {person}'s birthday is yet."
