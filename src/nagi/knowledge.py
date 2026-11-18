"""Knowledge: facts, rules taught as sentences, and proofs.

A fact is a triple of subject, relation and object, compared as plain words
(lowercase, no punctuation, no articles): "a whale is a mammal" is the fact
``("whale", "is", "mammal")``. A rule is a sentence of such triples with
``{variables}``, the same braces as slots::

    {x} is {z} if {x} is {y} and {y} is {z}

Each triple in a rule is its first word, its last word, and the relation
between them, so a term in a rule is one word or a variable.

Nagi answers by backward chaining: to show a triple, it finds a fact that
matches, or a rule whose conclusion matches, then shows the rule's
conditions in turn. A relation starting "not" holds when the rest can't be
shown: "cat not is big" holds unless "cat is big" does. Facts and rules are both tried newest first, so a later
lesson refines an earlier one, as a later learner does. Each proof is the facts it used and what it
concluded from them, in order, so it can be thought out loud.
"""

import re
from collections.abc import Iterator

from nagi.tokens import normalize

Triple = tuple[str, str, str]
Bindings = dict[str, str]
DEPTH = 8  # rules applied in a row before a proof gives up
STEPS = 20000  # facts and rules tried before a proof gives up
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
        self.indexed: list[list[str]] | None = None  # the facts as they were when last indexed

    def index(self) -> dict[tuple[int, str], list[Triple]]:
        """Facts by a term and its place, newest first, kept until the facts change."""
        if self.indexed != self.facts:
            self.by_term: dict[tuple[int, str], list[Triple]] = {}
            for fact in reversed(self.facts):
                for place, t in enumerate(fact):
                    self.by_term.setdefault((place, t), []).append(tuple(fact))
            self.indexed = self.facts[:]
        return self.by_term

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

    def forget(self, subject: str, relation: str, object: str) -> Triple:
        fact = term(subject), term(relation), term(object)
        self.facts[:] = [f for f in self.facts if tuple(f) != fact]
        return fact

    def rule(self, text: str) -> None:
        then, _, conditions = text.partition(" if ")
        if not conditions:
            raise ValueError(f'a rule is "<conclusion> if <condition> and <condition>": {text!r}')
        self.suppose(triple(then), [triple(c) for c in conditions.split(" and ")])

    def suppose(self, then: Triple, conditions: list[Triple]) -> None:
        """Know that ``then`` holds whenever the conditions do."""
        rule = {"then": list(then), "if": [list(c) for c in conditions]}
        if rule not in self.rules:
            self.rules.append(rule)

    def told(self, subject: str, relation: str, object: str) -> bool:
        """Whether the fact was told, not shown: a lookup, no proof."""
        fact = term(subject), term(relation), term(object)
        return fact in self.index().get((0, fact[0]), [])

    def holds(self, subject: str, relation: str, object: str) -> bool:
        return next(self.prove((term(subject), term(relation), term(object))), None) is not None

    def prove(self, goal: Triple) -> Iterator[tuple[Bindings, list[str]]]:
        """Every way to show the goal: the bindings of its variables, and the steps.

        The most bound condition is shown first, as Prolog programmers order
        them by hand, and proving gives up after STEPS facts and rules tried.
        """
        yield from self.show([goal], {}, [], 0, [STEPS], self.index())

    def show(self, goals: list[Triple], bound: Bindings, stack: list[Triple], depth: int, budget: list[int], index):
        if not goals:
            yield bound, []
            return
        resolved = [resolve(g, bound) for g in goals]
        ready = lambda g: not g[1].startswith("not ") or not any(map(is_variable, g))  # a negation waits for its terms
        at = max(range(len(goals)), key=lambda i: (ready(resolved[i]), sum(not is_variable(t) for t in resolved[i])))
        goal, rest = resolved[at], goals[:at] + goals[at + 1 :]
        if goal[1].startswith("not "):  # what can't be shown is not true
            positive = goal[0], goal[1][4:], goal[2]
            if next(self.show([positive], bound, [], depth, budget, index), None) is None:
                for done, steps in self.show(rest, bound, stack, depth, budget, index):
                    yield done, [f"I can't show {said(positive)}", *steps]
            return
        shape = tuple("{}" if is_variable(t) else t for t in goal)
        if shape in stack:  # showing this needs showing itself first
            return
        known = [index.get((place, t), []) for place, t in enumerate(goal) if not is_variable(t)]
        for fact in min(known, key=len) if known else map(tuple, reversed(self.facts)):
            budget[0] -= 1
            if budget[0] < 0:
                return
            if (more := unify(goal, fact, bound)) is not None:
                for done, steps in self.show(rest, more, stack, depth, budget, index):
                    yield done, [said(fact), *steps]
        if depth == DEPTH:
            return
        for rule in reversed(self.rules):
            budget[0] -= 1
            if budget[0] < 0:
                return
            fresh = lambda t, n=budget[0]: f"{t[:-1]}.{n}}}" if is_variable(t) else t  # new names for each use
            then = tuple(map(fresh, rule["then"]))
            if (more := unify(then, goal, bound)) is None:
                continue
            conditions = [tuple(map(fresh, c)) for c in rule["if"]]
            for shown, why in self.show(conditions, more, [*stack, shape], depth + 1, budget, index):
                conclusion = "so " + said(resolve(goal, shown))
                for done, steps in self.show(rest, shown, stack, depth, budget, index):
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
