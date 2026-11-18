# Code mode

Responses and learners are small programs. A program is Python syntax
restricted to `module.function(...)` calls and string or number literals,
one call per line:

```python
speech.say(greeting.hello())
speech.say(greeting.doing_well())
```

Nothing else is allowed: no builtins, attributes, assignments, keywords or
control flow. Anything a program needs to decide belongs in a module.

## What a program may use

| | Responses | Learners |
|---|---|---|
| Modules | response modules (`nagi.modules` group) | learning modules (`nagi.learning` group) |
| Reads | `slot.NAME`, the words heard in a slot | `record` and `record.FIELD`, the record being learned |
| Context passed first | a `Turn` | a `Lesson` |

The function must be listed in its module's `__all__`. Response programs
can't call learning modules and learners can't call response modules,
which is what keeps responding from rewriting how Nagi learns.

`nagi plugins` lists every module a program can name.

## Bundled modules

| Module | Functions |
|---|---|
| `speech` | `say(text)`; `answer(text)` says a short answer as a sentence, "moo" as "Moo." |
| `greeting` | `hello()`, `time_of_day()`, `doing_well()`, `echo()` |
| `reason` | see [Reasoning](reasoning.md) |
| `learn` (learning) | `prompt`, `value`, `fact`, `rule`; see [Teaching](teaching.md) |

## The turn

A response module's functions take the current `Turn` first:

| Field | Holds |
|---|---|
| `heard` | the text as heard |
| `residue` | the words read as not part of the intent: `["oat", "milk"]` in "add oat milk to my list" taught as "add to my list" |
| `slots` | the words heard in each slot: `{"thing": "whale"}` |
| `now` | the time |
| `random` | a random source, for variety |
| `state` | a dict kept in memory between turns; each module keeps its data under its own name |
| `knowledge` | the facts and rules Nagi reasons with |
| `thoughts`, `said` | what Nagi thinks and says this turn |

```python
# src/nagi/modules/speech.py
__all__ = ["answer", "say"]

def say(turn, text: str) -> None:
    turn.said.append(text)
```

A learning module takes a `Lesson` first: `lesson.record`, and
`lesson.state`, which is the same dict as `turn.state`.

## Speed

A program is checked and compiled once, when learned or loaded, into
closures with every function already resolved. Running one costs only the
calls: about 4M calls a second on one core, 18× faster than `exec`.
Modules are imported on first use. Bad code is rejected when it is learned,
with a message saying which call isn't allowed.
