"""Intent capture: which intent makes the heard token sequence most probable.

Words count by how much they tell intents apart, as in TF-IDF: "spanish",
heard for one intent, weighs more than "how", heard for most of them, and a
word never heard weighs most of all. A word's weight scales the bits of its
tokens, or of skipping it, and a reading's score is bits per unit of weight.

A taught prompt may have slots, as in "is a {thing} a {kind}". A slot reads
one or more words heard in its place, each costing what skipping it would,
so a slot pays off only when the words around it fit; the reading says
which words filled it. A slot is entered only after a token a prompt put
before it, and that step weighs 1, like the end of a sentence, so a rare
word in a slot costs no more than in a skip. A slot may name the kind of
thing it holds, as in "i am {feeling:feeling}"; whether the words heard are
one is for knowledge to say (``kind_of``), so its words cost nothing to read.
"""

import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

SKIP = math.log2(0.01)  # bits to ignore a word, like the name in "hey nagi"
FILL = SKIP  # bits for a word read into a slot
UNSEEN = math.log2(0.0001)  # bits for a token transition never heard
TIE = 1e-9  # readings closer than this are equally probable; then the one skipping fewer words wins
KindOf = Callable[[str, str], bool]  # whether words heard are a kind of thing
THRESHOLD = -5.2  # bits per unit of weight an intent must reach to be captured


class Intent:
    """A bigram model of the token sequences heard for one intent."""

    def __init__(self, examples: list[list[list[str]]]):
        self.bigrams = Counter()
        for heard in examples:
            tokens = ["<s>", *(token for word in heard for token in word), "</s>"]
            self.bigrams.update(zip(tokens, tokens[1:]))
        self.words = {"".join(word) for heard in examples for word in heard}
        self.slots = {word for word in self.words if word[0] == "{"}
        self.following = Counter()
        for (a, _), n in self.bigrams.items():
            self.following[a] += n

    def bits(self, a: str, b: str) -> float:
        n = self.bigrams[a, b]
        return math.log2(n / self.following[a]) if n else UNSEEN

    def read(self, heard: list[list[str]], weights: list[float], kind_of: KindOf) -> "Fit":
        """The most probable reading, skipping words and filling slots as needed.

        A typed slot closes only if ``kind_of`` says its words are its kind.
        Readings in a slot are kept apart by where the slot began, so one
        that fails the check cannot crowd out one that passes it.
        """
        Path = tuple[float, tuple[int, ...], tuple[tuple[str, int], ...]]  # bits, skipped, filled
        paths: dict[tuple[str, int], Path] = {("<s>", -1): (0.0, (), ())}  # by the last token read, and where its slot began

        def closes(last: str, filled: tuple[tuple[str, int], ...]) -> bool:
            if ":" not in last:
                return True
            name, kind = last[1:-1].split(":")
            return kind_of(" ".join("".join(heard[at]) for slot, at in filled if slot == name), kind)

        for at, (word, weight) in enumerate(zip(heard, weights)):
            extended: dict[tuple[str, int], Path] = {}

            def offer(key: tuple[str, int], path: Path) -> None:
                held = extended.get(key)
                if held is None or path[0] > held[0] + TIE or (path[0] > held[0] - TIE and len(path[1]) < len(held[1])):
                    extended[key] = path

            for (last, began), (total, skipped, filled) in paths.items():
                offer((last, began), (total + weight * SKIP, (*skipped, at), filled))
                for slot in self.slots:
                    fill = 0 if ":" in slot else weight * FILL  # knowledge checks a typed slot instead
                    name = slot[1:-1].split(":")[0]
                    if slot == last:
                        offer((slot, began), (total + fill, skipped, (*filled, (name, at))))
                    elif self.bigrams[last, slot] and closes(last, filled):  # only where a prompt put it
                        into = self.bits(last, slot)  # weighs 1, like the end
                        offer((slot, at), (total + into + fill, skipped, (*filled, (name, at))))
                if closes(last, filled):
                    for token in word:
                        total += weight * self.bits(last, token)
                        last = token
                    offer((last, -1), (total, skipped, filled))
            paths = extended
        ended = [
            (total + self.bits(last, "</s>"), skipped, filled)
            for (last, _), (total, skipped, filled) in paths.items()
            if closes(last, filled)
        ]
        if not ended:
            return Fit(-math.inf, list(range(len(heard))))
        best = max(total for total, _, _ in ended)
        total, skipped, filled = min((path for path in ended if path[0] > best - TIE), key=lambda path: len(path[1]))
        slots: dict[str, list[int]] = {}
        for name, at in filled:
            slots.setdefault(name, []).append(at)
        return Fit(total / (sum(weights) + 1), list(skipped), slots)


@dataclass
class Fit:
    score: float  # bits per unit of weight
    skipped: list[int]  # positions of the words read as not part of the intent
    slots: dict[str, list[int]] = field(default_factory=dict)  # positions of the words filling each slot


def weigh(intents: dict[str, Intent], heard: list[list[str]]) -> list[float]:
    """Each word's weight: 1, plus the bits of surprise at it among the intents."""
    def heard_for(word: str) -> int:
        return sum(word in intent.words for intent in intents.values())

    return [1 + math.log2((len(intents) + 1) / (heard_for("".join(word)) + 1)) for word in heard]


def anything(words: str, kind: str) -> bool:
    return True


def readings(intents: dict[str, Intent], heard: list[list[str]], kind_of: KindOf = anything) -> dict[str, Fit]:
    """How each intent reads what was heard, however badly it fits."""
    weights = weigh(intents, heard)
    return {name: intent.read(heard, weights, kind_of) for name, intent in intents.items()}


def capture(intents: dict[str, Intent], heard: list[list[str]], kind_of: KindOf = anything) -> dict[str, Fit]:
    """Every intent that fits what was heard; a typed slot holds what ``kind_of`` allows."""
    return {name: fit for name, fit in readings(intents, heard, kind_of).items() if fit.score >= THRESHOLD}
