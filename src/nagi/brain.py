"""Learn, remember, and respond.

A teaching asset is JSON Lines. A newborn Nagi knows how to learn only one
kind of record, a learner (see ``nagi.learning``). The curriculum's first
lesson teaches the learners for SFT, DPO and RLHF records, and every
completion they teach is ``{"think": "...", "code": "..."}``: an optional
chain of thought, then a code-mode program (see ``nagi.code``).

Memory keeps the learners, and one entry per distinct completion with the
weight of each prompt toward it and its value::

    {"version": 2,
     "learners": {"sft": {"shape": {...}, "code": "..."}},
     "responses": {"<id>": {"think": "...", "code": "...",
                            "prompts": {"hi": 1}, "value": 0}}}

Responding is three separate stages: token in, intent capture, generate.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from nagi.code import Program, Turn
from nagi.generate import Response, generate
from nagi.intent import Intent, capture
from nagi.learning import Learner, Lesson
from nagi.tokens import tokenize, train

VERSION = 2


class Brain:
    def __init__(self, memory: dict | None = None):
        self.memory = memory or {"version": VERSION, "learners": {}, "responses": {}}
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

    def respond(self, text: str, now: datetime | None = None) -> Turn:
        turn = Turn(text, now or datetime.now())
        heard = tokenize(text, self.ranks)
        fits = capture(self.intents, heard)
        return generate(self.responses, fits, turn)

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
