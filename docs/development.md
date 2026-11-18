# Development

How to work on Nagi itself. To extend Nagi without changing it, write a
[plugin](plugins.md).

## Setup

```console
$ git clone https://github.com/soasme/nagi
$ cd nagi
$ uv sync
$ uv run pytest
```

`uv sync` installs the example plugins as workspace members, so their
entry points are registered and their tests run with core's.

## Layout

```
src/nagi/          the package; see Architecture for each file
src/nagi/modules/  core's response and learning modules
src/nagi/assets/   the bundled curriculum, t0/ to t3/
examples/          todo and birthdays, two plugins built with `nagi new`
tests/             core's tests
bench/             public benchmarks
docs/              these docs
ROADMAP.md         what comes next, and why
AGENTS.md          the code taste every change is held to
```

## Checks

Before a change is done:

```console
$ uv run pytest                 # core and examples
$ uv run nagi --memory /tmp/m.json learn
$ uv run nagi --memory /tmp/m.json eval      # ≥ 95% accuracy, ≤ 2% false accepts
```

A change to understanding or reasoning should also run the benches it
touches (see [Benchmarks](bench.md)) and record the new numbers there,
including the ones that got worse.

## Where a change goes

Ask whether it helps Nagi *learn*, or is needed for Nagi to be Nagi. If so,
it belongs in core. A skill, like a calendar or the weather, is a plugin.
Common knowledge a five-year-old has belongs in the curriculum, as data.

| To change | Edit |
|---|---|
| what Nagi knows or says | an asset in `src/nagi/assets/`, with its eval |
| how a kind of record is learned | a learner in an asset, not Python |
| what responses can do | a module in `src/nagi/modules/`, listed in `pyproject.toml` |
| how sentences are read | `tokens.py`, `intent.py`, `generate.py` |
| how proofs work | `knowledge.py` |
| what plugins see | `api.py`; keep it stable within a major `VERSION` |

## Conventions

- No dependencies. Nagi is standard-library Python 3.12.
- Fix with data before code. A misread sentence usually needs another
  prompt or a negative eval case, not a new branch.
- Every asset that teaches responses has an eval set beside it, with
  negatives.
- Memory operations add up. A new one should be a sum too, so lessons stay
  order-free.
- A change to the memory format bumps `VERSION` in `brain.py`.
- Each module starts with a docstring saying what it does in plain words;
  keep it true when the code changes.
- Prefer deleting to adding. Read [AGENTS.md](../AGENTS.md) before your
  first change.
- Commit messages say what changed and, for results, the number: "Index
  facts by term for each proof: bAbI runs twice as fast".
