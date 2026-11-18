"""SNIPS: seven assistant intents, with the words of each slot marked.

Teaches the train split as SFT, one response per intent, each annotated span
a slot ("add {music_item} to the {playlist} playlist"), and each span's words
as a fact ("cita romántica is a playlist"), then reads the test split.
Scores the intent, and the slots as exact (slot, words) pairs, for what Nagi
understands and for the nearest reading, as if nothing were rejected::

    uv run python bench/snips.py

Coucke et al., 2018, "Snips Voice Platform: an embedded Spoken Language
Understanding system for private-by-design voice interfaces".
https://github.com/sonos/nlu-benchmark
"""

import json
import time
import urllib.request
from collections import Counter
from pathlib import Path

from nagi.brain import Brain
from nagi.generate import choose
from nagi.intent import THRESHOLD
from nagi.plugins import curriculum
from nagi.tokens import said

URL = "https://raw.githubusercontent.com/sonos/nlu-benchmark/master/2017-06-custom-intent-engines/{0}/{1}"
CACHE = Path.home() / ".cache" / "nagi" / "snips"
INTENTS = ["AddToPlaylist", "BookRestaurant", "GetWeather", "PlayMusic", "RateBook", "SearchCreativeWork",
           "SearchScreeningEvent"]


def examples(intent: str, split: str) -> list[list[dict]]:
    """Each utterance as its pieces of text, a slot's piece naming its ``entity``."""
    name = f"train_{intent}_full.json" if split == "train" else f"validate_{intent}.json"
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL.format(intent, name), path)
    return [utterance["data"] for utterance in json.loads(path.read_text(encoding="utf-8", errors="replace"))[intent]]


def prompt(pieces: list[dict]) -> str:
    return "".join(f" {{{p['entity']}}} " if "entity" in p else p["text"] for p in pieces)


def slots(pieces: list[dict]) -> Counter:
    found = {}
    for p in pieces:
        if "entity" in p:
            found.setdefault(p["entity"], []).extend(said(p["text"]))
    return Counter((name, " ".join(words).lower()) for name, words in found.items())


def code(intent: str) -> str:
    return f"speech.say({json.dumps(intent)})"


def teach(brain: Brain, train: list[tuple[str, list[dict]]]) -> None:
    """Each utterance as a prompt with its spans as slots, and each span's words as what its slot holds."""
    start = time.time()
    values = {(p["text"], p["entity"]) for _, pieces in train for p in pieces if "entity" in p}
    brain.learn("\n".join(
        [json.dumps({"subject": text, "relation": "is a", "object": entity}) for text, entity in sorted(values)]
        + [json.dumps({"prompt": prompt(pieces), "completion": {"code": code(intent)}}) for intent, pieces in train]
    ))
    print(f"taught {len(train)} prompts and {len(values)} slot values in {time.time() - start:.0f}s")


def score(brain: Brain, test: list[tuple[str, list[dict]]]) -> None:
    start = time.time()
    right, found, wanted, matched = Counter(), Counter(), Counter(), Counter()  # understood, and nearest
    for intent, pieces in test:
        text = "".join(p["text"] for p in pieces)
        words, fits = said(text), brain.read(text)
        nearest = choose(brain.responses, fits)
        name = nearest if fits[nearest].score >= THRESHOLD else None
        gold = slots(pieces)
        for kind, chosen in (("understood", name), ("nearest", nearest)):
            heard = {} if chosen is None else fits[chosen].slots
            guess = Counter((slot, " ".join(words[at] for at in ats).lower()) for slot, ats in heard.items())
            right[kind] += chosen is not None and brain.memory["responses"][chosen]["code"] == code(intent)
            found[kind] += guess.total()
            wanted[kind] += gold.total()
            matched[kind] += (gold & guess).total()
    print(f"read {len(test)} in {time.time() - start:.0f}s")
    for kind in right:
        precision, recall = matched[kind] / max(found[kind], 1), matched[kind] / wanted[kind]
        print(f"{kind:10}  intent {right[kind] / len(test):6.1%}  slot F1 {2 * precision * recall / max(precision + recall, 1e-9):6.1%}"
              f"  (precision {precision:.1%}, recall {recall:.1%})")


def main() -> None:
    brain = Brain()
    brain.learn(curriculum()[0].read_text())  # only how to learn
    teach(brain, [(intent, pieces) for intent in INTENTS for pieces in examples(intent, "train")])
    score(brain, [(intent, pieces) for intent in INTENTS for pieces in examples(intent, "test")])


if __name__ == "__main__":
    main()
