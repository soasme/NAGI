"""Birthdays, answered. Code mode calls these as birthdays.when().

Nagi learns the birthdays from your data (see ``nagi_birthdays.learning``).
Whose birthday is asked about is what Nagi wasn't taught: taught "when is
birthday", it reads "when is Mei's birthday?" as asking about Mei.
"""

import re

from nagi.api import Turn

__all__ = ["when"]


def when(turn: Turn) -> str:
    person = re.sub(r"['’]s$", "", " ".join(turn.residue))
    if not person:
        return "Whose birthday?"
    known = turn.state.get("birthdays", {})
    for name, day in known.items():
        if name.lower() == person.lower():
            return f"{name}'s birthday is {day}."
    return f"I don't know when {person}'s birthday is yet."
