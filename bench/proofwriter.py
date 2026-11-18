"""ProofWriter: true or false, from a theory of facts and rules told in English.

Each theory is facts ("The cat is nice.") and rules ("If someone is nice
then they are big."), and each question asks whether a sentence follows.
In the closed world, what can't be shown is false, as for Nagi; in the open
world (``--world OWA``), theories also say what is not so, and what can be
shown neither way is unknown. A theory is all Nagi may use, so Nagi
learns only how to learn (the first lesson), the words the theories use
(names, qualities and verbs, as facts), and one prompt for each shape of
sentence in the train split, with slots for the words; its program tells a
fact, a rule or answers. Then Nagi hears each test theory, sentence by sentence, and
answers its questions::

    uv run python bench/proofwriter.py
    uv run python bench/proofwriter.py --world OWA

Tafjord et al., 2021, "ProofWriter: Generating Implications, Proofs, and
Abductive Statements over Natural Language". https://allenai.org/data/proofwriter
"""

import argparse
import json
import re
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

from nagi.brain import Brain
from nagi.plugins import curriculum

URL = "https://aristo-data-public.s3.amazonaws.com/proofwriter/proofwriter-dataset-V2020.12.3.zip"
CACHE = Path.home() / ".cache" / "nagi" / "proofwriter.zip"
SET = "proofwriter-dataset-V2020.12.3/{}/depth-5/meta-{}.jsonl"
NAMES = ["the bald eagle", "the bear", "the cat", "the cow", "the dog", "the lion", "the mouse", "the rabbit",
         "the squirrel", "the tiger", "anne", "bob", "charlie", "dave", "erin", "fiona", "gary", "harry"]
QUALITIES = ["big", "blue", "cold", "furry", "green", "kind", "nice", "quiet", "red", "rough", "round", "smart",
             "white", "young"]
VERBS = ["chase", "eat", "like", "need", "see", "visit"]
ANYONE = {"someone", "something", "they", "it"}
NOT = {"CWA": "not", "OWA": "denied"}  # how a world says not: can't be shown, or told so
ANSWERS = {True: "yes", False: "no", "Unknown": "I don't know"}
WORD = re.compile(r"\b(" + "|".join(NAMES + QUALITIES + VERBS + [v + "s" for v in VERBS]) + r")\b")


def theories(world: str, split: str) -> list[dict]:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, CACHE)
    with zipfile.ZipFile(CACHE) as archive:
        return [json.loads(line) for line in archive.open(SET.format(world, split))]


def sentences(theory: str) -> list[str]:
    return re.split(r"(?<=\.)\s+", theory.strip())


def question(sentence: str) -> str:
    return f"is it true that {sentence[:-1].lower()}?"


def shape(sentence: str) -> list[str]:
    """A sentence's words, with each name, quality and verb as its slot: "{n1:name} is {q1:quality}."."""
    counts = Counter()

    def slot(match: re.Match) -> str:
        word = match.group(1)
        kind = "name" if word in NAMES else "quality" if word in QUALITIES else "verb"
        counts[kind] += 1
        return f"{{{kind[0]}{counts[kind]}:{kind}}}"

    return WORD.sub(slot, sentence.lower()).replace(",", " ,").split()


def clauses(words: list[str], world: str) -> list[tuple[str, str, str, str]]:
    """The triples of clauses such as "someone is {q1} and not {q2}", and each one's opposite relation.

    As program arguments: "not big" is the relation "not is" in the closed
    world, where it holds when "is big" can't be shown, and "denied is" in
    the open one, where it must be told or shown like any other.
    """
    found, subject = [], None
    for clause in " ".join(words).split(" and "):
        *head, last = clause.replace(" ,", "").split()
        value = lambda w: '"{x}"' if w in ANYONE else f"slot.{w[1:].split(':')[0]}"
        if head and (head[0] in ANYONE or head[0].startswith("{n")):
            subject, head = value(head[0]), head[1:]
        verb = next((w for w in head if w.startswith("{v")), None)
        said = [f'reason.what({value(verb)}, "means")', f'reason.what({value(verb)}, "{NOT[world]}")'] if verb else [
            '"is"', f'"{NOT[world]} is"']
        relation, opposite = said[::-1] if "not" in head else said
        found.append((subject, relation, value(last), opposite))
    return found


def program(words: list[str], world: str) -> str:
    """What a sentence's shape says to do: tell a fact, know a rule, or answer."""
    def rule(then, conditions):
        return "reason.rule(" + ", ".join(t for c in [*then, *conditions] for t in c[:3]) + ")"

    text = " ".join(words)
    if words[0] == "is":  # is it true that ...?
        (fact,) = clauses(words[4:], world)
        if world == "CWA":
            return f"speech.say(reason.check({', '.join(fact[:3])}))"
        return f"speech.say(reason.ask({', '.join(fact)}))"
    if words[0] == "if":
        conditions, _, then = text[3:-1].partition(" then ")
        return rule(clauses(then.split(), world), clauses(conditions.split(), world))
    if "things" in words or "people" in words:  # all big, kind things are red.
        kinds = [w for w in words[:words.index("are")] if w.startswith("{q")]
        are = words.index("are")
        return rule(clauses(["something", "is", *words[are + 1 : -1], words[-1][:-1]], world),
                    clauses(["something", "is", " and ".join(kinds)], world))
    (fact,) = clauses(text[:-1].split(), world)
    return f"reason.tell({', '.join(fact[:3])})"


def lesson(world: str) -> list[dict]:
    """The words, and one prompt for each shape of sentence in the train split."""
    words = [{"subject": name, "relation": "is a", "object": "name"} for name in NAMES]
    words += [{"subject": quality, "relation": "is a", "object": "quality"} for quality in QUALITIES]
    for verb in VERBS:
        for form in (verb, verb + "s"):
            words.append({"subject": form, "relation": "is a", "object": "verb"})
            words.append({"subject": form, "relation": "means", "object": verb + "s"})
            words.append({"subject": form, "relation": NOT[world], "object": f"{NOT[world]} {verb}s"})
    shapes = set()
    for theory in theories(world, "train"):
        shapes.update(" ".join(shape(s)) for s in sentences(theory["theory"]))
        shapes.update(" ".join(shape(question(q["question"]))) for q in theory["questions"].values())
    prompts = [{"prompt": s.replace(" ,", ","), "completion": {"code": program(s.split(), world)}} for s in sorted(shapes)]
    return words + prompts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--world", choices=NOT, default="CWA", help="closed (default), or open: answers may be unknown")
    world = parser.parse_args().world
    brain = Brain()
    brain.learn(curriculum()[0].read_text())  # how to learn, and nothing else
    taught = lesson(world)
    brain.learn("".join(json.dumps(record) + "\n" for record in taught))
    print(f"taught {len(taught)} records")
    facts, rules = list(brain.memory["facts"]), list(brain.memory["rules"])
    start, unread, right, asked = time.time(), 0, Counter(), Counter()
    for theory in theories(world, "test"):
        brain.memory["facts"][:], brain.memory["rules"][:] = facts, rules
        for sentence in sentences(theory["theory"]):
            unread += brain.respond(sentence).said == ["...?"]
        for q in theory["questions"].values():
            said = brain.respond(question(q["question"])).said
            asked[q["QDep"]] += 1
            right[q["QDep"]] += said == [ANSWERS[q["answer"]]]
    for depth in sorted(asked):
        print(f"depth {depth}  {right[depth] / asked[depth]:6.1%} of {asked[depth]}")
    print(f"all      {sum(right.values()) / sum(asked.values()):6.1%} of {sum(asked.values())}"
          f"  ({unread} sentences not understood, {time.time() - start:.0f}s)")


if __name__ == "__main__":
    main()
