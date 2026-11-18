# Teaching

You teach Nagi with **assets**: JSON Lines files, one record per line.

```console
$ uv run nagi learn my-lessons.jsonl
```

## Learners

A newborn Nagi knows how to learn exactly one kind of record, a
**learner**: a name, the shape of record it handles, and a program that
changes memory.

```json
{"learner": "dpo",
 "shape": {"prompt": "text", "chosen": "completion", "rejected": "completion"},
 "code": "learn.prompt(record.prompt, record.chosen, 1)\nlearn.prompt(record.prompt, record.rejected, -1)\nlearn.value(record.chosen, 1)\nlearn.value(record.rejected, -1)"}
```

The curriculum's first lesson, `src/nagi/assets/t0/0-how-to-learn.jsonl`,
teaches five:

| Learner | Record | Effect |
|---|---|---|
| `sft` | `{"prompt", "completion"}` | prompt weight +1 |
| `dpo` | `{"prompt", "chosen", "rejected"}` | prompt weight and value +1 for chosen, −1 for rejected |
| `rlhf` | `{"prompt", "completion", "reward"}` | prompt weight and value += reward |
| `fact` | `{"subject", "relation", "object"}` | a fact to reason with |
| `rule` | `{"rule"}` | a rule, as a sentence |

Every other record goes to the most recently taught learner whose shape it
fits exactly: the same keys, each value of the right type. Shape types are
`text` (a string), `number`, and `completion` (see below). A record no
learner fits is an error naming its line.

Teaching a learner under an existing name replaces it. So a new way of
learning is a new learner, taught in any asset, and you can change how
Nagi learns SFT records without touching Python.

## Memory operations

A learner's program changes memory only through learning modules. Core's
is `learn`:

| Operation | Effect |
|---|---|
| `learn.prompt(text, completion, weight)` | hearing `text` leads to `completion` while its total weight is positive |
| `learn.value(completion, delta)` | preference; below zero, never chosen |
| `learn.fact(subject, relation, object)` | Nagi knows the fact |
| `learn.rule(text)` | Nagi reasons with the rule |

They add up, so lessons can be taught in any order and repeating one does
no harm. A plugin can register its own learning module, so your data can be
learned your own way (see [Plugins](plugins.md)).

## Completions

A completion is a chain of thought and a program, never fixed text:

```json
{"prompt": "hi nagi, how are you",
 "completion": {"think": "They greet me and ask how I am. Greet back, then say how I am.",
                "code": "speech.say(greeting.hello())\nspeech.say(greeting.doing_well())"}}
```

`think` is optional; `nagi respond --think` shows it. `code` is a
[code mode](code-mode.md) program, checked when it is learned. Memory keeps
one entry per distinct completion, with the weight of each prompt toward it
and its value.

When several responses fit what was heard equally well, as responses
taught the same prompts do, the one with the highest value is chosen. DPO
and RLHF records are how you teach that preference.

## Slots

A prompt can leave a place for words, a **slot**, which its program reads
as `slot.NAME`:

```json
{"prompt": "add {item} to my list",
 "completion": {"code": "speech.say(todo.add(slot.item))"}}
```

Nagi reads "add oat milk to my list" with `slot.item` as "oat milk". A
response that reads a slot is chosen only when that slot was heard.

A slot can name the kind of thing it holds: `{feeling:feeling}` reads only
words Nagi can show are a feeling. Taught `"i am {feeling:feeling}"`, it
reads "i am bored" (once `bored is a feeling` is known) but not "i am a
teacher". Its words cost nothing to read, since knowledge vouches for them.

When the wrong words end up in a slot, teach more prompts before writing
code. The todo example teaches `add {item} to my list please`, so "add
bread to the list, please" adds "bread".

## Tiers and curricula

A curriculum is a directory of tiers, `t0/`, `t1/` and so on, like a
child's years. `nagi learn NAME` teaches a curriculum's assets tier by
tier, in file-name order within each tier. Prefixing a file with `0-`
makes it go first, which is how the learners arrive before the records
they read.

The bundled curriculum is named `nagi`. Plugins add their own (see
[Plugins](plugins.md)). `nagi plugins` lists what is installed.

## Evals

An eval set sits next to the assets it checks, named `*.eval.jsonl`, and is
never learned. Each case names the program Nagi should run for a prompt,
or `null` when Nagi should not understand it. It may also say what Nagi
should say:

```json
{"prompt": "hey nagi", "expect": "speech.say(greeting.hello())"}
{"prompt": "what is the capital of france", "expect": null}
{"prompt": "what does a cow say?", "expect": "speech.answer(reason.what(slot.thing, \"says\"))", "say": ["Moo."]}
```

A case with `say` runs its program on a copy of memory, so evals never
change what Nagi knows.

```console
$ uv run nagi eval              # the bundled sets
$ uv run nagi eval todo         # a plugin's
$ uv run nagi eval my.eval.jsonl
```

It prints every failure, then accuracy and the false accept rate (of the
cases that should stay unknown, how many were understood). Write negatives:
they are what keeps a new prompt from swallowing sentences it shouldn't.
