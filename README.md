# Nagi

Nagi is Not Artificial General Intelligence. It learns from teaching
records, remembers what it learned, and responds by running small programs
that call its own modules. No neural networks, just Python.

```console
$ uv run nagi respond hello
...?
$ uv run nagi learn
learned 2 records from greeting.dpo.jsonl
learned 2 records from greeting.rlhf.jsonl
learned 55 records from greeting.sft.jsonl
$ uv run nagi respond --think hey nagi
<think>They are greeting me. Greet them back, fitting the time of day.</think>
Good morning!
$ uv run nagi chat
```

Memory lives in `~/.nagi/memory.json` (change it with `--memory PATH`).

## Teaching assets

The curriculum is tiered like a child's: `src/nagi/assets/t0/` is for a
newborn, `t1/` comes next, and so on. `nagi learn` with no arguments walks the
tiers in order; `nagi learn FILE...` teaches your own.

Assets are JSON Lines in the usual fine-tuning shapes, told apart by their
fields:

| Format | Record | Effect |
|---|---|---|
| SFT | `{"prompt", "completion"}` | recognize the prompt as this completion |
| DPO | `{"prompt", "chosen", "rejected"}` | as SFT for chosen; value +1 chosen, −1 rejected |
| RLHF | `{"prompt", "completion", "reward"}` | value += reward; recognize the prompt if reward > 0 |

Every completion is a chain of thought and a program, never fixed text:

```json
{"think": "They are greeting me. Greet them back, fitting the time of day.",
 "code": "speech.say(greeting.hello())"}
```

Repeating a lesson reinforces it. Memory keeps one entry per distinct
completion, with the prompts that lead to it and its learned value.

## Code mode

A program is Python syntax restricted to `module.function(...)` calls and
string or number literals, one call per line. `module.function` must be in
`__all__` of `nagi.modules.<module>`, and each takes the current turn first:

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
   run the most valued (then best fitting) program, or say `...?`.

## Develop

```console
$ uv run pytest
```
