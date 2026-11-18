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
A plain slot's words cost nothing too when Nagi was told they are what the
slot is named for: "song" in {music_item}, once "song is a music_item".
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

    def read(self, heard: list[list[str]], weights: list[float], kind_of: KindOf, told: KindOf) -> "Fit":
        """The most probable reading, skipping words and filling slots as needed.

        A slot's words are checked as it closes: a typed slot closes only on
        words ``kind_of`` its kind, and a plain one gets its words free if
        Nagi was ``told`` they are what it is named, as "song" for
        {music_item}. Readings in a slot are kept apart by where it began,
        so one that fails the check cannot crowd out one that passes it.
        """
        Path = tuple[float, tuple[int, ...], tuple[tuple[str, int], ...]]  # bits, skipped, filled
        paths: dict[tuple[str, int], Path] = {("<s>", -1): (0.0, (), ())}  # by the last token read, and where its slot began

        def leave(last: str, began: int, total: float, filled: tuple[tuple[str, int], ...]) -> float | None:
            """The bits once the slot just read closes, or None if it can't."""
            if last[0] != "{":
                return total
            name, _, kind = last[1:-1].partition(":")
            span = [at for slot, at in filled if slot == name and at >= began]
            words = " ".join("".join(heard[at]) for at in span)
            if kind:
                return total if kind_of(words, kind) else None
            return total - sum(weights[at] * FILL for at in span) if told(words, name) else total

        for at, (word, weight) in enumerate(zip(heard, weights)):
            extended: dict[tuple[str, int], Path] = {}

            def offer(key: tuple[str, int], path: Path) -> None:
                held = extended.get(key)
                if held is None or path[0] > held[0] + TIE or (path[0] > held[0] - TIE and len(path[1]) < len(held[1])):
                    extended[key] = path

            for (last, began), (total, skipped, filled) in paths.items():
                offer((last, began), (total + weight * SKIP, (*skipped, at), filled))
                left = leave(last, began, total, filled)
                for slot in self.slots:
                    fill = 0 if ":" in slot else weight * FILL  # knowledge checks a typed slot instead
                    name = slot[1:-1].split(":")[0]
                    if slot == last:
                        offer((slot, began), (total + fill, skipped, (*filled, (name, at))))
                    elif self.bigrams[last, slot] and left is not None:  # only where a prompt put it
                        into = self.bits(last, slot)  # weighs 1, like the end
                        offer((slot, at), (left + into + fill, skipped, (*filled, (name, at))))
                if left is not None:
                    for token in word:
                        left += weight * self.bits(last, token)
                        last = token
                    offer((last, -1), (left, skipped, filled))
            paths = extended
        ended = [
            (left + self.bits(last, "</s>"), skipped, filled)
            for (last, began), (total, skipped, filled) in paths.items()
            if (left := leave(last, began, total, filled)) is not None
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


def nothing(words: str, kind: str) -> bool:
    return False


def readings(
    intents: dict[str, Intent], heard: list[list[str]], kind_of: KindOf = nothing, told: KindOf = nothing
) -> dict[str, Fit]:
    """How each intent reads what was heard, however badly it fits."""
    weights = weigh(intents, heard)
    return {name: intent.read(heard, weights, kind_of, told) for name, intent in intents.items()}

