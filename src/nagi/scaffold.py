"""`nagi new NAME`: a plugin package that works from the first run.

The package registers one module and one curriculum under NAME, ships a
teaching asset and an eval for it, and a test that learns Nagi's curriculum
and the plugin's, then checks the plugin's evals.
"""

import json
import re
from pathlib import Path

import nagi


def files(name: str) -> dict[str, str]:
    package = f"nagi_{name}"
    sources = ""
    root = Path(nagi.__file__).resolve().parents[2]
    if (root / "pyproject.toml").is_file() and 'name = "nagi"' in (root / "pyproject.toml").read_text():
        sources = f'\n[tool.uv.sources]\nnagi = {{ path = "{root}", editable = true }}\n'
    say = f"speech.say({name}.hello())"
    asset = [{"prompt": p, "completion": {"think": f"They want to try {name}.", "code": say}}
             for p in (f"try {name}", f"use {name}", f"what can {name} do", f"show me {name}")]
    evals = [{"prompt": f"can I try {name}?", "expect": say}, {"prompt": f"use {name} please", "expect": say},
             {"prompt": "what is the capital of france", "expect": None}]
    return {
        "pyproject.toml": f'''[project]
name = "nagi-{name.replace("_", "-")}"
version = "0.1.0"
description = "A Nagi plugin: {name}"
requires-python = ">=3.12"
dependencies = ["nagi"]

[project.entry-points."nagi.modules"]
{name} = "{package}"

[project.entry-points."nagi.curricula"]
{name} = "{package}.curriculum"

[build-system]
requires = ["uv_build>=0.10.6,<0.11.0"]
build-backend = "uv_build"

[dependency-groups]
dev = ["pytest"]
{sources}''',
        f"src/{package}/__init__.py": f'''"""The {name} module. Code mode calls these functions as {name}.<function>()."""

from nagi.api import Turn

__all__ = ["hello"]


def hello(turn: Turn) -> str:
    return "Hello from {name}!"
''',
        f"src/{package}/curriculum/t0/{name}.sft.jsonl": "".join(json.dumps(r) + "\n" for r in asset),
        f"src/{package}/curriculum/t0/{name}.eval.jsonl": "".join(json.dumps(r) + "\n" for r in evals),
        f"tests/test_{name}.py": f'''from nagi.brain import Brain
from nagi.evals import evaluate
from nagi.plugins import curriculum, evals


def brain() -> Brain:
    brain = Brain()
    for asset in curriculum("nagi") + curriculum("{name}"):
        brain.learn(asset.read_text())
    return brain


def test_passes_its_evals():
    taught = brain()
    for eval_set in evals("{name}"):
        assert evaluate(taught, eval_set.read_text()).failed == [], eval_set.name


def test_responds():
    assert brain().respond("try {name}").said == ["Hello from {name}!"]
''',
        "README.md": f'''# nagi-{name.replace("_", "-")}

A Nagi plugin.

- `src/{package}/__init__.py`: the `{name}` module; code mode calls `{name}.hello()`.
- `src/{package}/curriculum/t0/`: what to teach Nagi (`*.jsonl`) and how to check it (`*.eval.jsonl`).

```console
$ uv run pytest
$ uv run nagi learn nagi {name}
$ uv run nagi eval {name}
$ uv run nagi respond try {name}
```
''',
    }


def create(name: str, where: Path) -> list[Path]:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError(f"a plugin name is lowercase letters, digits and _: {name!r}")
    if where.exists():
        raise ValueError(f"{where} already exists")
    made = []
    for relative, content in files(name).items():
        path = where / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        made.append(path)
    return made
