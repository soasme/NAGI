"""HWU64: 64 home-assistant intents across 21 domains, with slots marked.

Taught and scored like SNIPS (see ``snips.py``), on the first of the
dataset's ten cross-validation folds::

    uv run python bench/hwu64.py

Liu et al., 2019, "Benchmarking Natural Language Understanding Services for
building Conversational Agents". https://github.com/xliuhw/NLU-Evaluation-Data
"""

import csv
import json
import re
import urllib.request
from pathlib import Path

from snips import score, teach

from nagi.brain import Brain
from nagi.knowledge import term
from nagi.plugins import curriculum

REPO = "https://raw.githubusercontent.com/xliuhw/NLU-Evaluation-Data/master/"
FOLD = "CrossValidation/autoGeneFromRealAnno/autoGene_2018_03_22-13_01_25_169/CrossValidation/KFold_1/"
TREE = "https://api.github.com/repos/xliuhw/NLU-Evaluation-Data/git/trees/master?recursive=1"
CACHE = Path.home() / ".cache" / "nagi" / "hwu64"
SLOT = re.compile(r"\[\s*(\w+)\s*:\s*([^\]]*?)\s*\]")


def files(split: str) -> list[Path]:
    """The fold's files for a split, one per intent, fetched once."""
    folder = CACHE / split
    if not folder.exists():
        tree = json.load(urllib.request.urlopen(TREE))["tree"]
        under = FOLD + ("trainset/" if split == "train" else "testset/csv/")
        names = [t["path"] for t in tree if t["path"].startswith(under) and t["path"].endswith(".csv")]
        folder.mkdir(parents=True)
        for name in names:
            urllib.request.urlretrieve(REPO + name, folder / Path(name).name)
    return sorted(folder.glob("*.csv"))


def pieces(annotation: str) -> list[dict]:
    """ "wake me at [time : nine am]" as SNIPS's pieces of text, a slot's naming its entity."""
    found, at = [], 0
    for match in SLOT.finditer(annotation):
        slot = {"text": match.group(2), "entity": match.group(1)} if term(match.group(2)) else {"text": ""}  # "[date : ]" marks nothing
        found += [{"text": annotation[at : match.start()]}, slot]
        at = match.end()
    return [*found, {"text": annotation[at:]}]


def examples(split: str) -> list[tuple[str, list[dict]]]:
    found = []
    for path in files(split):
        with path.open(newline="", encoding="utf-8", errors="replace") as rows:
            for row in csv.DictReader(rows, delimiter=";"):
                found.append((f"{row['scenario']}_{row['intent']}", pieces(row["answer_annotation"])))
    return found


def main() -> None:
    brain = Brain()
    brain.learn(curriculum()[0].read_text())  # only how to learn
    teach(brain, examples("train"))
    score(brain, examples("test"))


if __name__ == "__main__":
    main()
