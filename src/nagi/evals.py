"""Evals: check what Nagi would do, without teaching it anything.

An eval set is JSON Lines next to the assets it checks (``*.eval.jsonl``),
and is never learned. Each case names the program Nagi should run, or
``null`` when Nagi should not understand::

    {"prompt": "hey nagi", "expect": "speech.say(greeting.hello())"}
    {"prompt": "what is the capital of france", "expect": null}
"""

import json
from dataclasses import dataclass, field


@dataclass
class Case:
    prompt: str
    expect: str | None
    got: str | None


@dataclass
class Report:
    passed: int = 0
    failed: list[Case] = field(default_factory=list)
    unknowns: int = 0  # cases Nagi should not understand

    @property
    def total(self) -> int:
        return self.passed + len(self.failed)

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 1.0

    @property
    def false_accepts(self) -> list[Case]:
        """Understood something it should not have."""
        return [case for case in self.failed if case.expect is None]

    @property
    def false_rejects(self) -> list[Case]:
        """Did not understand something it should have."""
        return [case for case in self.failed if case.expect is not None and case.got is None]

    @property
    def false_accept_rate(self) -> float:
        return len(self.false_accepts) / self.unknowns if self.unknowns else 0.0

    def __add__(self, other: "Report") -> "Report":
        return Report(self.passed + other.passed, self.failed + other.failed, self.unknowns + other.unknowns)


def evaluate(brain, text: str) -> Report:
    report = Report()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match json.loads(line):
            case {"prompt": str(prompt), "expect": str() | None as expect}:
                report.unknowns += expect is None
                name = brain.choose(prompt)
                got = name and brain.memory["responses"][name]["code"]
                if got == expect:
                    report.passed += 1
                else:
                    report.failed.append(Case(prompt, expect, got))
            case _:
                raise ValueError(f'line {number}: an eval case is {{"prompt": "...", "expect": "code" or null}}')
    return report
