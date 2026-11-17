"""Learn from SFT, DPO and RLHF records, remember, and respond.

A teaching asset is JSON Lines. Each record is one of::

    {"prompt": "hi", "completion": C}                     # SFT: do this
    {"prompt": "hi", "chosen": C, "rejected": C}          # DPO: this, not that
    {"prompt": "hi", "completion": C, "reward": 1.0}      # RLHF: that was this good

and every completion ``C`` is ``{"think": "...", "code": "..."}``: an optional
chain of thought, then a code-mode program (see ``nagi.code``).

A prompt shown to a completion teaches Nagi to recognize it: SFT, DPO's chosen
and positively rewarded RLHF do. Preferences move the completion's value: DPO
by +1 for chosen and -1 for rejected, RLHF by its reward. Repeating a lesson
reinforces it. Memory keeps one entry per distinct completion::

    {"responses": {"<id>": {"think": "...", "code": "...",
                            "prompts": ["hi"], "value": 1.0}}}

Responding is three separate stages: token in, intent capture, generate.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from nagi.code import Program, Turn
from nagi.generate import Response, generate
from nagi.intent import Intent, capture
from nagi.tokens import tokenize, train


def response_id(completion: dict) -> str:
    return hashlib.sha1(json.dumps([completion["think"], completion["code"]]).encode()).hexdigest()[:12]


class Brain:
    def __init__(self, memory: dict | None = None):
        self.memory = memory or {"responses": {}}
        self.fit()

    def fit(self) -> None:
        responses = self.memory["responses"]
        self.ranks = train([prompt for r in responses.values() for prompt in r["prompts"]])
        self.intents = {
            name: Intent([tokenize(prompt, self.ranks) for prompt in r["prompts"]])
            for name, r in responses.items()
            if r["prompts"]
        }
        self.responses = {name: Response(r["think"], Program(r["code"]), r["value"]) for name, r in responses.items()}

    def learn(self, text: str) -> int:
        learned = 0
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            match json.loads(line):
                case {"prompt": str(prompt), "chosen": {"code": str()} as chosen, "rejected": {"code": str()} as rejected}:
                    self.teach(prompt, chosen, 1.0)
                    self.teach(None, rejected, -1.0)
                case {"prompt": str(prompt), "completion": {"code": str()} as completion, "reward": int() | float() as reward}:
                    self.teach(prompt if reward > 0 else None, completion, reward)
                case {"prompt": str(prompt), "completion": {"code": str()} as completion}:
                    self.teach(prompt, completion, 0.0)
                case _:
                    raise ValueError(f"line {number}: not an SFT, DPO or RLHF record")
            learned += 1
        self.fit()
        return learned

    def teach(self, prompt: str | None, completion: dict, reward: float) -> None:
        completion = {"think": completion.get("think", ""), "code": completion["code"]}
        Program(completion["code"])  # reject bad code before remembering it
        known = self.memory["responses"].setdefault(response_id(completion), {**completion, "prompts": [], "value": 0.0})
        if prompt is not None and prompt not in known["prompts"]:
            known["prompts"].append(prompt)
        known["value"] += reward

    def respond(self, text: str, now: datetime | None = None) -> Turn:
        turn = Turn(text, now or datetime.now())
        heard = tokenize(text, self.ranks)
        fits = capture(self.intents, heard)
        return generate(self.responses, fits, turn)

    @classmethod
    def load(cls, path: Path) -> "Brain":
        return cls(json.loads(path.read_text()) if path.exists() else None)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.memory, indent=2, ensure_ascii=False))
