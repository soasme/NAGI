"""Intent capture: which intent makes the heard token sequence most probable.

Words count by how much they tell intents apart, as in TF-IDF: "spanish",
heard for one intent, weighs more than "how", heard for most of them, and a
word never heard weighs most of all. A word's weight scales the bits of its
tokens, or of skipping it, and a reading's score is bits per unit of weight.
"""

import math
from collections import Counter
from dataclasses import dataclass

SKIP = math.log2(0.01)  # bits to ignore a word, like the name in "hey nagi"
UNSEEN = math.log2(0.0001)  # bits for a token transition never heard
THRESHOLD = -5.2  # bits per unit of weight an intent must reach to be captured


class Intent:
    """A bigram model of the token sequences heard for one intent."""

    def __init__(self, examples: list[list[list[str]]]):
        self.bigrams = Counter()
        for heard in examples:
            tokens = ["<s>", *(token for word in heard for token in word), "</s>"]
            self.bigrams.update(zip(tokens, tokens[1:]))
        self.words = {"".join(word) for heard in examples for word in heard}
        self.following = Counter()
        for (a, _), n in self.bigrams.items():
            self.following[a] += n

    def bits(self, a: str, b: str) -> float:
        n = self.bigrams[a, b]
        return math.log2(n / self.following[a]) if n else UNSEEN

    def read(self, heard: list[list[str]], weights: list[float]) -> "Fit":
        """The most probable reading, skipping words as needed."""
        paths = {"<s>": (0.0, ())}  # last token kept -> (best weighted bits so far, positions skipped)
        for at, (word, weight) in enumerate(zip(heard, weights)):
            extended: dict[str, tuple[float, tuple[int, ...]]] = {}

            def offer(last: str, total: float, skipped: tuple[int, ...]) -> None:
                if last not in extended or total > extended[last][0]:
                    extended[last] = (total, skipped)

            for last, (total, skipped) in paths.items():
                offer(last, total + weight * SKIP, (*skipped, at))
                for token in word:
                    total += weight * self.bits(last, token)
                    last = token
                offer(last, total, skipped)
            paths = extended
        total, skipped = max((total + self.bits(last, "</s>"), skipped) for last, (total, skipped) in paths.items())
        return Fit(total / (sum(weights) + 1), list(skipped))


@dataclass
class Fit:
    score: float  # bits per unit of weight
    skipped: list[int]  # positions of the words read as not part of the intent


def weigh(intents: dict[str, Intent], heard: list[list[str]]) -> list[float]:
    """Each word's weight: 1, plus the bits of surprise at it among the intents."""
    def heard_for(word: str) -> int:
        return sum(word in intent.words for intent in intents.values())

    return [1 + math.log2((len(intents) + 1) / (heard_for("".join(word)) + 1)) for word in heard]


def capture(intents: dict[str, Intent], heard: list[list[str]]) -> dict[str, Fit]:
    """Every intent that fits what was heard."""
    weights = weigh(intents, heard)
    fits = {name: intent.read(heard, weights) for name, intent in intents.items()}
    return {name: fit for name, fit in fits.items() if fit.score >= THRESHOLD}
