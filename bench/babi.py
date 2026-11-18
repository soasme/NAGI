"""bAbI: stories and questions that need reasoning over what was said.

Nagi learns its curriculum and ``bench/babi.jsonl``: how to read the
stories' sentences (prompts with slots), and rules for where things are,
directions, positions, sizes and motives. Deduction ("Gertrude is a sheep",
"sheep are afraid of wolves") needs nothing new: the curriculum already
teaches that a thing does what its kind does. Then Nagi hears each test
story, sentence by sentence, and answers its questions::

    uv run python bench/babi.py

Weston et al., 2015, "Towards AI-Complete Question Answering: A Set of
Prerequisite Toy Tasks". https://research.facebook.com/downloads/babi/
"""

import tarfile
import time
import urllib.request
from pathlib import Path

from nagi.brain import Brain
from nagi.plugins import curriculum
from nagi.tokens import normalize

URL = "https://s3.amazonaws.com/text-datasets/babi_tasks_1-20_v1-2.tar.gz"
CACHE = Path.home() / ".cache" / "nagi" / "babi_tasks_1-20_v1-2.tar.gz"
LESSON = Path(__file__).with_name("babi.jsonl")
TASKS = {
    1: "single-supporting-fact",
    2: "two-supporting-facts",
    4: "two-arg-relations",
    5: "three-arg-relations",
    6: "yes-no-questions",
    7: "counting",
    8: "lists-sets",
    9: "simple-negation",
    10: "indefinite-knowledge",
    11: "basic-coreference",
    12: "conjunction",
    13: "compound-coreference",
    14: "time-reasoning",
    15: "basic-deduction",
    16: "basic-induction",
    17: "positional-reasoning",
    18: "size-reasoning",
    20: "agents-motivations",
}


def stories(task: int) -> list[list[tuple[str, str | None]]]:
    """Each story as (sentence, answer) lines; a statement's answer is None."""
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, CACHE)
    with tarfile.open(CACHE) as archive:
        name = f"tasks_1-20_v1-2/en/qa{task}_{TASKS[task]}_test.txt"
        text = archive.extractfile(name).read().decode()
    found = []
    for line in text.splitlines():
        number, _, line = line.partition(" ")
        if number == "1":
            found.append([])
        sentence, *answer = line.split("\t")
        found[-1].append((sentence.strip(), answer[0] if answer else None))
    return found


def words(text: str) -> set[str]:
    """An answer's words, so "milk and apple" is "apple,milk", and "I don't know" is "maybe"."""
    text = text.replace("I don't know", "maybe")
    return {normalize(w) for w in text.split()} - {"and", ""}


def main() -> None:
    brain = Brain()
    for asset in curriculum():
        brain.learn(asset.read_text())
    brain.learn(LESSON.read_text())
    known = list(brain.memory["facts"])
    for task, name in TASKS.items():
        start, right, asked, unread = time.time(), 0, 0, 0
        for story in stories(task):
            brain.memory["facts"][:] = known
            for sentence, answer in story:
                turn = brain.respond(sentence)
                unread += turn.said == ["...?"]
                if answer is not None:
                    asked += 1
                    right += words(turn.said[-1]) == words(answer.replace(",", " "))
        print(f"task {task:2} {name:24} {right / asked:6.1%} of {asked}"
              f"  ({unread} sentences not understood, {time.time() - start:.1f}s)")


if __name__ == "__main__":
    main()
