# Getting started

## Install

Nagi needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```console
$ git clone https://github.com/soasme/nagi
$ cd nagi
$ uv sync
```

`uv sync` installs Nagi and the two example plugins in `examples/`.

## First session

A new Nagi knows nothing, not even how to learn a prompt:

```console
$ uv run nagi respond hello
...?
```

Teach it the bundled curriculum. With no arguments, `nagi learn` walks the
tiers in order, `t0/` first:

```console
$ uv run nagi learn
learned 5 records from 0-how-to-learn.jsonl
learned 3 records from greeting.dpo.jsonl
learned 3 records from greeting.rlhf.jsonl
learned 58 records from greeting.sft.jsonl
learned 27 records from animals.jsonl
...
learned 90 records from kinds.jsonl
```

Now talk to it. `--think` shows the chain of thought:

```console
$ uv run nagi respond --think hi nagi, how are you
<think>They greet me and ask how I am. Greet back, then say how I am.</think>
Hi there! I'm doing well, thanks!
$ uv run nagi respond --think is a whale an animal
<think>They ask whether a thing is a kind of thing. Check what I know about its kind.</think>
<think>whale is mammal</think>
<think>mammal is animal</think>
<think>so whale is animal</think>
Yes.
$ uv run nagi chat
> what does a cow say?
Moo.
```

`nagi chat` reads lines until end of input (Ctrl-D).

## Commands

| Command | Does |
|---|---|
| `nagi learn [CURRICULUM_OR_FILE...]` | learn curricula by name, or asset files (default: `nagi`) |
| `nagi respond [--think] WORDS...` | respond once |
| `nagi chat [--think]` | respond to each line until end of input |
| `nagi eval [CURRICULUM_OR_FILE...]` | check eval sets against memory (default: `nagi`) |
| `nagi plugins` | list installed modules, learning modules and curricula |
| `nagi new NAME [--dir DIR]` | create a plugin package |

`nagi eval` exits non-zero when accuracy falls below `--min-accuracy`
(default 0.95) or false accepts rise above `--max-false-accepts` (default
0.02).

## Memory

Everything Nagi learns, and everything its modules keep between turns,
lives in `~/.nagi/memory.json`. Pass `--memory PATH` before the command to
use another file:

```console
$ uv run nagi --memory work.json learn nagi todo
$ uv run nagi --memory work.json chat
```

To start over, delete the file. When Nagi's memory format changes, an older
file is refused; delete it and run `nagi learn` again.

## Next

- Teach it your own sentences: [Teaching](teaching.md).
- Give it new abilities in Python: [Plugins](plugins.md).
