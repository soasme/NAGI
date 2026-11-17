"""Intent capture: which intent makes the heard token sequence most probable."""

import math
from collections import Counter

SKIP = math.log2(0.01)  # bits to ignore a word, like the name in "hey nagi"
UNSEEN = math.log2(0.0001)  # bits for a token transition never heard
THRESHOLD = -4.7  # bits per word an intent must reach to be captured


class Intent:
    """A bigram model of the token sequences heard for one intent."""

    def __init__(self, examples: list[list[list[str]]]):
        self.bigrams = Counter()
        for heard in examples:
            tokens = ["<s>", *(token for word in heard for token in word), "</s>"]
            self.bigrams.update(zip(tokens, tokens[1:]))
        self.following = Counter()
        for (a, _), n in self.bigrams.items():
            self.following[a] += n

    def bits(self, a: str, b: str) -> float:
        n = self.bigrams[a, b]
        return math.log2(n / self.following[a]) if n else UNSEEN

    def score(self, heard: list[list[str]]) -> float:
        """Bits per word of the most probable reading, skipping words as needed."""
        paths = {"<s>": 0.0}  # last token kept -> best bits so far
        for word in heard:
            extended: dict[str, float] = {}
            for last, total in paths.items():
                extended[last] = max(extended.get(last, -math.inf), total + SKIP)
                for token in word:
                    total += self.bits(last, token)
                    last = token
                extended[last] = max(extended.get(last, -math.inf), total)
            paths = extended
        best = max(total + self.bits(last, "</s>") for last, total in paths.items())
        return best / (len(heard) + 1)


def capture(intents: dict[str, Intent], heard: list[list[str]]) -> dict[str, float]:
    """Every intent that fits what was heard, with its score."""
    scores = {name: intent.score(heard) for name, intent in intents.items()}
    return {name: score for name, score in scores.items() if score >= THRESHOLD}
