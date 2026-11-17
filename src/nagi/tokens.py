"""Token in: byte-pair tokens learned from what Nagi hears, as tiktoken does."""

import math
import re
from collections import Counter

Ranks = dict[tuple[str, str], int]


def said(text: str) -> list[str]:
    """The words as said, without surrounding punctuation, one per word Nagi reads."""
    return [re.sub(r"^\W+|\W+$", "", word) for word in text.split() if normalize(word)]


def words(text: str) -> list[str]:
    """The words as Nagi reads them: lowercase, no punctuation, " "-prefixed."""
    return [" " + normal for word in text.split() if (normal := normalize(word))]


def normalize(word: str) -> str:
    word = re.sub(r"[^\w]", "", word.lower())
    return re.sub(r"(.)\1{2,}", r"\1", word)  # "hiii" -> "hi"


def merge(parts: list[str], pair: tuple[str, str]) -> list[str]:
    merged, i = [], 0
    while i < len(parts):
        if tuple(parts[i : i + 2]) == pair:
            merged.append(parts[i] + parts[i + 1])
            i += 2
        else:
            merged.append(parts[i])
            i += 1
    return merged


def train(texts: list[str]) -> Ranks:
    """Byte-pair merges, ranked most frequent first, until every word is one token."""
    corpus = Counter(tuple(word) for text in texts for word in words(text))
    ranks: Ranks = {}
    while True:
        pairs = Counter()
        for word, n in corpus.items():
            for pair in zip(word, word[1:]):
                pairs[pair] += n
        if not pairs:
            return ranks
        pair = max(pairs, key=pairs.get)
        ranks[pair] = len(ranks)
        corpus = Counter({tuple(merge(list(word), pair)): n for word, n in corpus.items()})


def encode(word: str, ranks: Ranks) -> list[str]:
    """Merge the best-ranked pair until none is known."""
    parts = list(word)
    while len(parts) > 1:
        pair = min(zip(parts, parts[1:]), key=lambda p: ranks.get(p, math.inf))
        if pair not in ranks:
            break
        parts = merge(parts, pair)
    return parts


def tokenize(text: str, ranks: Ranks) -> list[list[str]]:
    """Tokens of each word, so later stages can still see word boundaries."""
    return [encode(word, ranks) for word in words(text)]
