"""Banking77: 77 fine-grained intents of one bank's customers.

Teaches the train split as SFT, one response per intent, then reads the test
split. Every question is in scope, so this measures telling close intents
apart ("card arrival" from "card delivery estimate")::

    uv run python bench/banking77.py

Casanueva et al., 2020, "Efficient Intent Detection with Dual Sentence
Encoders". https://github.com/PolyAI-LDN/task-specific-datasets
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

from nagi.brain import Brain
from nagi.generate import choose
from nagi.plugins import curriculum

URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/{}.csv"
CACHE = Path.home() / ".cache" / "nagi" / "banking77"


def examples(split: str) -> list[tuple[str, str]]:
    path = CACHE / f"{split}.csv"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL.format(split), path)
    with path.open(newline="", encoding="utf-8") as rows:
        return [(row["text"], row["category"]) for row in csv.DictReader(rows)]


def code(intent: str) -> str:
    return f"speech.say({json.dumps(intent)})"


def main() -> None:
    brain = Brain()
    brain.learn(curriculum()[0].read_text())  # only how to learn
    start, train = time.time(), examples("train")
    brain.learn("\n".join(json.dumps({"prompt": text, "completion": {"code": code(intent)}}) for text, intent in train))
    print(f"taught {len(train)} prompts in {time.time() - start:.0f}s")

    start, test, right, best = time.time(), examples("test"), 0, 0
    for text, intent in test:
        name, *_ = brain.understand(text)
        right += name is not None and brain.memory["responses"][name]["code"] == code(intent)
        best += brain.memory["responses"][choose(brain.responses, brain.read(text))]["code"] == code(intent)
    print(f"read {len(test)} in {time.time() - start:.0f}s")
    print(f"accuracy        {right / len(test):.1%}")
    print(f"nearest intent  {best / len(test):.1%}  (accuracy if nothing were rejected)")


if __name__ == "__main__":
    main()
