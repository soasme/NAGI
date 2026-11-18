# Plugins

A plugin is an ordinary Python package that gives Nagi modules, learners
and curricula. Nagi's own are registered the same way, so core is just the
first plugin.

## Start one

```console
$ uv run nagi new weather
created nagi-weather/pyproject.toml
created nagi-weather/src/nagi_weather/__init__.py
created nagi-weather/src/nagi_weather/curriculum/t0/weather.sft.jsonl
created nagi-weather/src/nagi_weather/curriculum/t0/weather.eval.jsonl
created nagi-weather/tests/test_weather.py
created nagi-weather/README.md
$ cd nagi-weather
$ uv run pytest
```

The package has a module, a curriculum with a teaching asset and an eval,
and a test that learns Nagi's curriculum and the plugin's and checks the
evals. It passes from the first run. Names are lowercase letters, digits
and `_`.

## Entry points

A plugin registers up to three things in its `pyproject.toml`:

```toml
[project.entry-points."nagi.modules"]       # responses call birthdays.when()
birthdays = "nagi_birthdays"

[project.entry-points."nagi.learning"]      # learners call birthdays.remember(...)
birthdays = "nagi_birthdays.learning"

[project.entry-points."nagi.curricula"]     # t0/, t1/, ... of assets and *.eval.jsonl
birthdays = "nagi_birthdays.curriculum"
```

| Group | What it is | Called by |
|---|---|---|
| `nagi.modules` | response modules: functions taking a `Turn` | response programs |
| `nagi.learning` | learning modules: functions taking a `Lesson` | learners |
| `nagi.curricula` | a package directory of tiers holding assets and evals | `nagi learn NAME`, `nagi eval NAME` |

Names share one namespace per group. Two packages registering the same
name in a group is an error naming both.

From the plugin's directory, `uv run` installs it next to Nagi:

```console
$ uv run nagi plugins
module     weather      nagi_weather
curriculum weather      nagi_weather.curriculum
...
$ uv run nagi learn nagi weather
$ uv run nagi eval weather
```

## A response module

```python
from nagi.api import Turn

__all__ = ["add", "show"]


def add(turn: Turn, item: str) -> str:
    turn.state.setdefault("todo", []).append(item)
    return f"Added {item}."
```

Only functions in `__all__` can be called from code mode. Keep data under
your module's name in `turn.state`, and it persists between turns. The
fields of a turn are listed in [Code mode](code-mode.md#the-turn).

Teach the prompts that lead to it in the curriculum:

```json
{"prompt": "add {item} to my list", "completion": {"think": "They want something on their list.", "code": "speech.say(todo.add(slot.item))"}}
```

## Learning your own data

A learning module lets a learner store data your way. Learners call only
learning modules, and responses only response modules; they meet in state,
since `lesson.state` when learning is `turn.state` when responding.

```python
# nagi_birthdays/learning.py
from nagi.api import Lesson

__all__ = ["remember"]


def remember(lesson: Lesson, person: str, day: str) -> None:
    lesson.state.setdefault("birthdays", {})[person] = day
```

Teach a learner for your data's shape, in the plugin's curriculum:

```json
{"learner": "birthday", "shape": {"person": "text", "birthday": "text"}, "code": "birthdays.remember(record.person, record.birthday)"}
```

Then your data file is just records:

```console
$ cat family.jsonl
{"person": "Mei", "birthday": "3 May"}
$ uv run nagi learn nagi birthdays family.jsonl
$ uv run nagi respond "when is Mei's birthday?"
Mei's birthday is 3 May.
```

Learning modules check their own values and raise `ValueError` on bad
data; Nagi reports it with the line number.

## The API

Plugins build on `nagi.api`: `Turn`, `Lesson` and `VERSION`. It stays
stable within a major `VERSION` (now 1). Anything else in `nagi` may
change.

## Examples

- [`examples/todo`](../examples/todo): a todo list whose items are slots
  and whose list persists in `turn.state`.
- [`examples/birthdays`](../examples/birthdays): birthdays learned from
  your own data file through a plugin learner and learning module, then
  answered.

Both were started with `nagi new` and are run by the core test suite.

## Tips

- Fix understanding with data first. When a slot picks up the wrong words,
  teach another prompt; when a prompt fits too much, drop it and add a
  negative to the eval.
- Write negatives in every eval set, including sentences close to yours
  that mean something else.
- Test that core's evals still pass with your plugin learned alongside.
