"""Reasoning with what Nagi knows (see ``nagi.knowledge``).

Questions think out loud: the facts a proof used and what it concluded go
to the turn's thoughts. Conversation can add to what Nagi knows::

    reason.update(slot.person, "is in", slot.place)     # "Mary went to the kitchen."
    speech.say(reason.what(slot.person, "is in"))       # "Where is Mary?"
    speech.say(reason.check(slot.thing, "is", slot.kind))  # "Is a whale a fish?"
"""

from nagi.code import Turn
from nagi.knowledge import said, term

__all__ = ["check", "tell", "update", "what"]

UNKNOWN = "I don't know"


def check(turn: Turn, subject: str, relation: str, object: str) -> str:
    """"yes" if Nagi can show the fact, otherwise "no"."""
    goal = term(subject), term(relation), term(object)
    for _, steps in turn.knowledge.prove(goal):
        turn.thoughts.extend(steps)
        return "yes"
    turn.thoughts.append(f"I can't show {said(goal)}")
    return "no"


def what(turn: Turn, subject: str, relation: str) -> str:
    """The object Nagi can show the subject has this relation to, newest first."""
    goal = term(subject), term(relation), "{what}"
    for bound, steps in turn.knowledge.prove(goal):
        turn.thoughts.extend(steps)
        return bound["{what}"] if "{what}" in bound else UNKNOWN
    turn.thoughts.append(f"I don't know what {said(goal[:2])}")
    return UNKNOWN


def tell(turn: Turn, subject: str, relation: str, object: str) -> None:
    turn.thoughts.append("now I know " + said(turn.knowledge.tell(subject, relation, object)))


def update(turn: Turn, subject: str, relation: str, object: str) -> None:
    """Tell a fact that replaces what was known of the subject's relation."""
    turn.thoughts.append("now I know " + said(turn.knowledge.update(subject, relation, object)))
