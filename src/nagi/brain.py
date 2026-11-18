"""Learn, remember, and respond.

A teaching asset is JSON Lines. A newborn Nagi knows how to learn only one
kind of record, a learner (see ``nagi.learning``). The curriculum's first
lesson teaches the learners for SFT, DPO and RLHF records, and every
completion they teach is ``{"think": "...", "code": "..."}``: an optional
chain of thought, then a code-mode program (see ``nagi.code``).

Memory keeps the learners, one entry per distinct completion with the
weight of each prompt toward it and its value, the facts and rules Nagi
reasons with (see ``nagi.knowledge``), and the modules' state::

    {"version": 2,
     "learners": {"sft": {"shape": {...}, "code": "..."}},
     "responses": {"<id>": {"think": "...", "code": "...",
                            "prompts": {"hi": 1}, "value": 0}},
     "facts": [["whale", "is", "mammal"]],
     "rules": [{"then": ["{x}", "is", "{z}"], "if": [["{x}", "is", "{y}"], ["{y}", "is", "{z}"]]}],
     "state": {"todo": ["oat milk"]}}

Responding is three separate stages: token in, intent capture, generate.
"""

import copy
import functools
import hashlib
import json
from datetime import datetime
from pathlib import Path

from nagi.code import Program, Turn
from nagi.generate import Response, choose, generate
from nagi.intent import THRESHOLD, Fit, Intent, readings
from nagi.knowledge import Knowledge, term
from nagi.learning import Learner, Lesson
from nagi.tokens import said, tokenize, train

VERSION = 2


class Brain:
    def __init__(self, memory: dict | None = None):
        self.memory = memory or {"version": VERSION, "learners": {}, "responses": {}}
        for kept in ("facts", "rules"):
            self.memory.setdefault(kept, [])
        self.memory.setdefault("state", {})
        self.knowledge = Knowledge(self.memory["facts"], self.memory["rules"])
        self.fit()

    def fit(self) -> None:
        self.learners = {name: Learner(**learner) for name, learner in self.memory["learners"].items()}
        recognized = {
            name: [prompt for prompt, weight in r["prompts"].items() if weight > 0]
            for name, r in self.memory["responses"].items()
        }
        self.ranks = train([prompt for prompts in recognized.values() for prompt in prompts])
        self.intents = {
            name: Intent([tokenize(prompt, self.ranks) for prompt in prompts])
            for name, prompts in recognized.items()
            if prompts
        }
        self.responses = {
            name: Response(r["think"], Program(r["code"]), r["value"]) for name, r in self.memory["responses"].items()
        }

    def learn(self, text: str) -> int:
        learned = 0
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line)
            lesson = Lesson(self, record)
            try:
                if isinstance(record, dict) and "learner" in record:
                    self.teach_learner(record)
                else:
                    self.learner_for(record).program(lesson)
            except ValueError as error:
                raise ValueError(f"line {number}: {error}") from error
            learned += 1
        self.fit()
        return learned

    def learner_for(self, record) -> Learner:
        if isinstance(record, dict):
            for learner in reversed(self.learners.values()):
                if learner.fits(record):
                    return learner
        raise ValueError("no learner knows this kind of record yet")

    def teach_learner(self, record: dict) -> None:
        match record:
            case {"learner": str(name), "shape": shape, "code": str(code)} if len(record) == 3:
                self.learners.pop(name, None)
                self.learners[name] = Learner(shape, code)
                self.memory["learners"].pop(name, None)
                self.memory["learners"][name] = {"shape": shape, "code": code}
            case _:
                raise ValueError('a learner is {"learner": name, "shape": {...}, "code": "..."}')

    def remember(self, completion: dict) -> dict:
        """The memory entry for a completion, made on first sight."""
        think, code = completion.get("think", ""), completion["code"]
        name = hashlib.sha1(json.dumps([think, code]).encode()).hexdigest()[:12]
        if name not in self.memory["responses"]:
            Program(code)  # reject bad code before remembering it
            self.memory["responses"][name] = {"think": think, "code": code, "prompts": {}, "value": 0}
        return self.memory["responses"][name]

    def read(self, text: str) -> dict[str, Fit]:
        """How each intent reads the text, however badly, with what Nagi knows of kinds."""
        kind_of = functools.cache(lambda words, kind: self.knowledge.holds(words, "is", kind))
        whole = lambda words: len(term(words).split()) == len(words.split())  # no word read for nothing, as "the"
        told = functools.cache(lambda words, kind: whole(words) and self.knowledge.told(words, "is", kind))
        return readings(self.intents, tokenize(text, self.ranks), kind_of, told)

    def understand(self, text: str) -> tuple[str | None, list[str], dict[str, str]]:
        """The response Nagi would give, the words it read as not part of it, and its slots."""
        fits = {name: fit for name, fit in self.read(text).items() if fit.score >= THRESHOLD}
        name = choose(self.responses, fits)
        words = said(text)
        if name is None:
            return None, words, {}
        fit = fits[name]
        return name, [words[at] for at in fit.skipped], {s: " ".join(words[at] for at in ats) for s, ats in fit.slots.items()}

    def respond(self, text: str, now: datetime | None = None, keep: bool = True) -> Turn:
        """Respond; unless ``keep``, on a copy of the state and knowledge, so nothing changes."""
        name, residue, slots = self.understand(text)
        state, knowledge = self.memory["state"], self.knowledge
        if not keep:
            state = copy.deepcopy(state)
            knowledge = Knowledge(copy.deepcopy(knowledge.facts), copy.deepcopy(knowledge.rules))
        turn = Turn(text, now or datetime.now(), residue=residue, slots=slots, state=state, knowledge=knowledge)
        return generate(self.responses.get(name), turn)

    @classmethod
    def load(cls, path: Path) -> "Brain":
        if not path.exists():
            return cls()
        memory = json.loads(path.read_text())
        if memory.get("version") != VERSION:
            raise ValueError(f"{path} is an older memory format; remove it and run `nagi learn` again")
        return cls(memory)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.memory, indent=2, ensure_ascii=False))
