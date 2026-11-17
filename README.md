# Nagi

Nagi is Not Artificial General Intelligence. It is a meta-learning
framework: it learns how to learn, and you hook in your own training data
and code to teach it what you need. It remembers what it learned and
responds by running small programs that call its modules. No neural
networks, just Python.

This repo ships the learning kernel, the runtime and a small bootstrap
curriculum; skills come from your data and plugins. See
[ROADMAP.md](ROADMAP.md).

```console
$ uv run nagi respond hello
...?
$ uv run nagi learn
learned 3 records from 0-how-to-learn.jsonl
learned 3 records from greeting.dpo.jsonl
learned 3 records from greeting.rlhf.jsonl
learned 55 records from greeting.sft.jsonl
$ uv run nagi respond --think hi nagi, how are you
<think>They greet me and ask how I am. Greet back, then say how I am.</think>
Hi there! I'm doing well, thanks!
$ uv run nagi chat
```

Memory lives in `~/.nagi/memory.json` (change it with `--memory PATH`).

## Teaching assets

The curriculum is tiered like a child's: `src/nagi/assets/t0/` is for a
newborn, `t1/` comes next, and so on. `nagi learn` with no arguments walks the
tiers in order; `nagi learn FILE...` teaches your own.

Assets are JSON Lines. A newborn Nagi knows how to learn exactly one kind of
record, a **learner**: what shape of record it handles, and a program that
changes memory through `learn.*` operations only.

```json
{"learner": "dpo",
 "shape": {"prompt": "text", "chosen": "completion", "rejected": "completion"},
 "code": "learn.prompt(record.prompt, record.chosen, 1)\nlearn.prompt(record.prompt, record.rejected, -1)\nlearn.value(record.chosen, 1)\nlearn.value(record.rejected, -1)"}
```

The curriculum's first lesson, `t0/0-how-to-learn.jsonl`, teaches the
learners for the usual fine-tuning shapes:

| Learner | Record | Effect |
|---|---|---|
| `sft` | `{"prompt", "completion"}` | prompt weight +1 |
| `dpo` | `{"prompt", "chosen", "rejected"}` | prompt weight and value +1 for chosen, −1 for rejected |
| `rlhf` | `{"prompt", "completion", "reward"}` | prompt weight and value += reward |

A record goes to the most recently taught learner whose shape it fits
exactly (shape types: `text`, `number`, `completion`). So a new way of
learning is a new learner, taught in any asset, and teaching a learner
under an existing name changes how Nagi learns.
The memory operations are sums, so lessons add up in any order and
repeating one reinforces it:

| Operation | Effect |
|---|---|
| `learn.prompt(text, completion, weight)` | hearing `text` leads to `completion` while its total weight is positive |
| `learn.value(completion, delta)` | preference; below zero, never chosen |

Every completion is a chain of thought and a program, never fixed text:

```json
{"think": "They greet me and ask how I am. Greet back, then say how I am.",
 "code": "speech.say(greeting.hello())\nspeech.say(greeting.doing_well())"}
```

Memory keeps the learners and one entry per distinct completion, with each
prompt's weight and the completion's value. It is versioned; an older
memory file must be removed and relearned.

## Evals

An eval set sits next to the assets it checks (`*.eval.jsonl`) and is never
learned. Each case names the program Nagi should run for a prompt, or
`null` when Nagi should not understand it:

```json
{"prompt": "hey nagi", "expect": "speech.say(greeting.hello())"}
{"prompt": "what is the capital of france", "expect": null}
```

`nagi eval` checks the bundled sets, or the files you name, against your
memory. It prints every failure and exits non-zero below
`--min-accuracy` (default 95%) or above `--max-false-accepts` (default 2%
of the cases that should stay unknown).

## Code mode

A program is Python syntax restricted to `module.function(...)` calls and
string or number literals, one call per line. Responses may call response
modules (`nagi.modules`); learners may call learning modules
(`nagi.learning`), and may read `record` and its fields. `module.function`
must be in the module's `__all__`, and takes the current turn (or lesson)
first. A turn carries what was heard, the untaught words (`turn.residue`),
the time, a random source for variety, and `turn.state`, which persists:

```python
# src/nagi/modules/speech.py
__all__ = ["say"]

def say(turn, text):
    turn.said.append(text)
```

Programs are checked and compiled once, when learned or loaded, into
closures with every function already resolved. Running one costs only the
calls (about 4M calls/s on one core, 18× faster than `exec`); modules load on
first use. Nothing else (builtins, attributes, assignments) is allowed.

## Plugins

Nagi's own modules and curriculum are registered with Python entry points,
and so is everyone else's. A plugin is an ordinary package:

```toml
[project.entry-points."nagi.modules"]       # responses call birthdays.when()
birthdays = "nagi_birthdays"

[project.entry-points."nagi.learning"]      # learners call birthdays.remember(...)
birthdays = "nagi_birthdays.learning"

[project.entry-points."nagi.curricula"]     # t0/, t1/, ... of assets and *.eval.jsonl
birthdays = "nagi_birthdays.curriculum"
```

Response modules take a `Turn`, and learning modules take a `Lesson`. They
share state: what a learning module keeps in `lesson.state`, a response
module reads from `turn.state`. Core's `learn.*` is just the first learning
module, so your own data can be learned your own way: teach a learner for
its shape, and point it at your learning module.

```console
$ uv run nagi plugins                 # what is installed
$ uv run nagi learn nagi todo         # curricula by name, or asset files
$ uv run nagi eval todo               # check the plugin's evals
```

Start one with `nagi new NAME`: it creates a package with a module, a
curriculum with a teaching asset and an eval, and a test that learns and
checks it, all passing from the first `uv run pytest`.

Two complete plugins are built this way:
- [`examples/todo`](examples/todo): a todo list whose items come from the
  words Nagi wasn't taught (`turn.residue`) and whose list persists in
  `turn.state`.
- [`examples/birthdays`](examples/birthdays): birthdays learned from your
  own data file through a plugin learner and learning module, then
  answered.

Names share one namespace per group; two packages registering the same
name in a group is an error. Plugin code builds on `nagi.api`, which stays
stable within a major `VERSION`.

## How it responds

Three separate stages, one module each:

1. **Token in** (`tokens.py`). Like tiktoken, Nagi learns byte-pair merges
   from every prompt, so each taught word becomes one token and unseen words
   fall apart into learned pieces.
2. **Intent capture** (`intent.py`). Each response's prompts form a bigram
   model of token sequences. Every response whose model fits what you say
   well enough is captured, skipping untaught words at a cost (so "hey
   nagi" still fits); fitting means at least −4.7 bits (log₂ probability)
   per word.
3. **Generate** (`generate.py`). Of the captured responses with value ≥ 0,
   run the best fitting program, or say `...?`. Responses taught the same
   prompts fit equally, so preference (value) decides between them.

## Next

See [ROADMAP.md](ROADMAP.md).

## Develop

```console
$ uv run pytest
```
