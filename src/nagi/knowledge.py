"""Knowledge: facts, rules taught as sentences, and proofs.

A fact is a triple of subject, relation and object, compared as plain words
(lowercase, no punctuation, no articles): "a whale is a mammal" is the fact
``("whale", "is", "mammal")``. A rule is a sentence of such triples with
``{variables}``, the same braces as slots::

    {x} is {z} if {x} is {y} and {y} is {z}

Each triple in a rule is its first word, its last word, and the relation
between them, so a term in a rule is one word or a variable.

Nagi answers by backward chaining: to show a triple, it finds a fact that
matches, newest first, or a rule whose conclusion matches, then shows the
rule's conditions in turn. Each proof is the facts it used and what it
concluded from them, in order, so it can be thought out loud.
"""

import re
from collections.abc import Iterator

from nagi.tokens import normalize

Triple = tuple[str, str, str]
Bindings = dict[str, str]
DEPTH = 8  # rules applied in a row before a proof gives up
ARTICLES = {"a", "an", "the"}


def term(text: str) -> str:
    """Words as knowledge compares them; a {variable} stays as is."""
    return " ".join(
        word if re.fullmatch(r"\{\w+\}", word) else normal
        for word in text.split()
        if (normal := normalize(word)) and normal not in ARTICLES
    )


def triple(text: str) -> Triple:
    words = term(text).split()
    if len(words) < 3:
        raise ValueError(f"not a subject, relation and object: {text!r}")
    return words[0], " ".join(words[1:-1]), words[-1]


def said(fact: Triple) -> str:
    return " ".join(fact)


class Knowledge:
    """What Nagi knows, kept in memory's ``facts`` and ``rules`` lists, changed in place."""

    def __init__(self, facts: list[list[str]], rules: list[dict]):
        self.facts = facts
        self.rules = rules

    def tell(self, subject: str, relation: str, object: str) -> Triple:
        fact = term(subject), term(relation), term(object)
        if not all(fact):
            raise ValueError(f"a fact needs a subject, relation and object: {fact!r}")
        if list(fact) not in self.facts:
            self.facts.append(list(fact))
        return fact

    def update(self, subject: str, relation: str, object: str) -> Triple:
        """Tell a fact that replaces what was known of the subject's relation, as for where someone is."""
        s, r = term(subject), term(relation)
        self.facts[:] = [f for f in self.facts if f[:2] != [s, r]]
        return self.tell(subject, relation, object)

    def rule(self, text: str) -> None:
        then, _, conditions = text.partition(" if ")
        if not conditions:
            raise ValueError(f'a rule is "<conclusion> if <condition> and <condition>": {text!r}')
        rule = {"then": list(triple(then)), "if": [list(triple(c)) for c in conditions.split(" and ")]}
        if rule not in self.rules:
            self.rules.append(rule)

    def prove(self, goal: Triple) -> Iterator[tuple[Bindings, list[str]]]:
        """Every way to show the goal: the bindings of its variables, and the steps."""
        yield from self.show([goal], {}, [], 0)

    def show(self, goals: list[Triple], bound: Bindings, stack: list[Triple], depth: int):
        if not goals:
            yield bound, []
            return
        goal, rest = resolve(goals[0], bound), goals[1:]
        shape = tuple("{}" if is_variable(t) else t for t in goal)
        if shape in stack:  # showing this needs showing itself first
            return
        for fact in reversed(self.facts):
            if (more := unify(goal, tuple(fact), bound)) is not None:
                for done, steps in self.show(rest, more, stack, depth):
                    yield done, [said(tuple(fact)), *steps]
        if depth == DEPTH:
            return
        for number, rule in enumerate(self.rules):
            fresh = lambda t: f"{t[:-1]}.{depth}.{number}}}" if is_variable(t) else t
            then = tuple(map(fresh, rule["then"]))
            if (more := unify(then, goal, bound)) is None:
                continue
            conditions = [tuple(map(fresh, c)) for c in rule["if"]]
            for shown, why in self.show(conditions, more, [*stack, shape], depth + 1):
                conclusion = "so " + said(resolve(goal, shown))
                for done, steps in self.show(rest, shown, stack, depth):
                    yield done, [*why, conclusion, *steps]


def is_variable(t: str) -> bool:
    return t.startswith("{")


def resolve(t: Triple, bound: Bindings) -> Triple:
    def value(x: str) -> str:
        while is_variable(x) and x in bound:
            x = bound[x]
        return x

    return value(t[0]), value(t[1]), value(t[2])


def unify(a: Triple, b: Triple, bound: Bindings) -> Bindings | None:
    a, b = resolve(a, bound), resolve(b, bound)
    more = dict(bound)
    for x, y in zip(a, b):
        if x == y:
            continue
        if is_variable(x):
            more[x] = y
        elif is_variable(y):
            more[y] = x
        else:
            return None
        a, b = resolve(a, more), resolve(b, more)
    return more
