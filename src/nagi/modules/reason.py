"""Reasoning with what Nagi knows (see ``nagi.knowledge``).

Questions think out loud: the facts a proof used and what it concluded go
to the turn's thoughts. Conversation can add to what Nagi knows::

    reason.update(slot.person, "is in", slot.place)       # "Mary went to the kitchen."
    speech.say(reason.what(slot.person, "is in"))         # "Where is Mary?"
    speech.say(reason.which("south of", slot.place))      # "What is south of the garden?"
    speech.say(reason.check(slot.thing, "is", slot.kind))  # "Is a whale a fish?"
    speech.say(reason.ask(slot.thing, "is", slot.kind, "is not"))  # the same, where unknown isn't false
    speech.say(reason.each("is in", slot.person))         # "What is Mary carrying?"
    speech.say(reason.count("is in", slot.person))        # "How many objects is Mary carrying?"
    reason.rule("{x}", "is", slot.b, "{x}", "is", slot.a)  # "All {a} things are {b}."
"""

from nagi.code import Turn
from nagi.knowledge import said, term

__all__ = ["ask", "check", "count", "each", "forget", "rule", "tell", "update", "what", "which"]

UNKNOWN = "I don't know"
NOTHING = "nothing"


def check(turn: Turn, subject: str, relation: str, object: str) -> str:
    """"yes" if Nagi can show the fact, otherwise "no"."""
    goal = term(subject), term(relation), term(object)
    for _, steps in turn.knowledge.prove(goal):
        turn.thoughts.extend(steps)
        return "yes"
    turn.thoughts.append(f"I can't show {said(goal)}")
    return "no"


def ask(turn: Turn, subject: str, relation: str, object: str, opposite: str) -> str:
    """"yes" if Nagi can show the fact, "no" if it can show the opposite, otherwise that it doesn't know.

    For a world where not knowing isn't knowing not: ask("cat", "is", "big", "is not").
    """
    for answer, said_relation in (("yes", relation), ("no", opposite)):
        goal = term(subject), term(said_relation), term(object)
        for _, steps in turn.knowledge.prove(goal):
            turn.thoughts.extend(steps)
            return answer
    turn.thoughts.append(f"I can't show {said((term(subject), term(relation), term(object)))}, or that it's not so")
    return UNKNOWN


def what(turn: Turn, subject: str, relation: str) -> str:
    """The object Nagi can show the subject has this relation to, newest first."""
    goal = term(subject), term(relation), "{what}"
    for bound, steps in turn.knowledge.prove(goal):
        turn.thoughts.extend(steps)
        return bound["{what}"] if "{what}" in bound else UNKNOWN
    turn.thoughts.append(f"I don't know what {said(goal[:2])}")
    return UNKNOWN


def which(turn: Turn, relation: str, object: str) -> str:
    """The subject Nagi can show has this relation to the object, newest first."""
    for found, _ in subjects(turn, relation, object):
        return found
    return UNKNOWN


def each(turn: Turn, relation: str, object: str) -> str:
    """Every subject Nagi can show has this relation to the object, as "milk and apple"."""
    found = list(dict.fromkeys(found for found, _ in subjects(turn, relation, object)))
    if not found:
        return NOTHING
    return found[0] if len(found) == 1 else ", ".join(found[:-1]) + " and " + found[-1]


def count(turn: Turn, relation: str, object: str) -> str:
    """How many subjects Nagi can show have this relation to the object, as a number: "2"."""
    return str(len(set(found for found, _ in subjects(turn, relation, object))))


def subjects(turn: Turn, relation: str, object: str):
    goal = "{which}", term(relation), term(object)
    for bound, steps in turn.knowledge.prove(goal):
        if "{which}" in bound:
            turn.thoughts.extend(steps)
            yield bound["{which}"], steps


def forget(turn: Turn, subject: str, relation: str, object: str) -> None:
    turn.thoughts.append("no longer " + said(turn.knowledge.forget(subject, relation, object)))


def tell(turn: Turn, subject: str, relation: str, object: str) -> None:
    turn.thoughts.append("now I know " + said(turn.knowledge.tell(subject, relation, object)))


def rule(turn: Turn, *terms: str) -> None:
    """Know a rule told as triples, the conclusion first: subject, relation, object, subject, ..."""
    if len(terms) < 6 or len(terms) % 3:
        raise ValueError("a rule is a conclusion and conditions, each a subject, relation and object")
    then, *conditions = (tuple(map(term, terms[at : at + 3])) for at in range(0, len(terms), 3))
    turn.knowledge.suppose(then, conditions)
    turn.thoughts.append(f"now I know {said(then)} if " + " and ".join(map(said, conditions)))


def update(turn: Turn, subject: str, relation: str, object: str) -> None:
    """Tell a fact that replaces what was known of the subject's relation."""
    turn.thoughts.append("now I know " + said(turn.knowledge.update(subject, relation, object)))
