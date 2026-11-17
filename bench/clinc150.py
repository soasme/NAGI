"""CLINC150: 150 everyday assistant intents, and questions none of them covers.

Teaches the train split as SFT, one response per intent, then reads the test
split. Out-of-scope questions should not be understood::

    uv run python bench/clinc150.py            # 100 train prompts per intent
    uv run python bench/clinc150.py --per-intent 10

Larson et al., 2019, "An Evaluation Dataset for Intent Classification and
Out-of-Scope Prediction". https://github.com/clinc/oos-eval
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

from nagi.brain import Brain
from nagi.generate import choose
from nagi.intent import weigh
from nagi.plugins import curriculum
from nagi.tokens import tokenize

URL = "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json"
CACHE = Path.home() / ".cache" / "nagi" / "clinc150.json"


def data() -> dict:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, CACHE)
    return json.loads(CACHE.read_text())


def code(intent: str) -> str:
    return f"speech.say({json.dumps(intent)})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-intent", type=int, help="train prompts per intent (default: all 100)")
    limit = parser.parse_args().per_intent
    clinc = data()

    taught: dict[str, list[str]] = {}
    for text, intent in clinc["train"]:
        taught.setdefault(intent, []).append(text)
    brain = Brain()
    brain.learn(curriculum()[0].read_text())  # only how to learn
    start = time.time()
    brain.learn("\n".join(
        json.dumps({"prompt": text, "completion": {"code": code(intent)}})
        for intent, texts in taught.items() for text in texts[:limit]
    ))
    print(f"taught {sum(len(t[:limit]) for t in taught.values())} prompts in {time.time() - start:.0f}s")

    start = time.time()
    right = best = 0
    for text, intent in clinc["test"]:
        heard = tokenize(text, brain.ranks)
        name, *_ = brain.understand(text)
        right += name is not None and brain.memory["responses"][name]["code"] == code(intent)
        nearest = choose(brain.responses, {n: i.read(heard, weigh(brain.intents, heard)) for n, i in brain.intents.items()})
        best += brain.memory["responses"][nearest]["code"] == code(intent)
    rejected = sum(brain.understand(text)[0] is None for text, _ in clinc["oos_test"])
    print(f"read {len(clinc['test']) + len(clinc['oos_test'])} in {time.time() - start:.0f}s")
    print(f"in-scope accuracy    {right / len(clinc['test']):.1%}")
    print(f"out-of-scope recall  {rejected / len(clinc['oos_test']):.1%}")
    print(f"nearest intent right {best / len(clinc['test']):.1%}  (in-scope accuracy if nothing were rejected)")


if __name__ == "__main__":
    main()
