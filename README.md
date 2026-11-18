# Nagi

Nagi is Not Artificial General Intelligence. It is a meta-learning
framework: it learns how to learn, and you hook in your own training data
and code to teach it what you need. It remembers what it learned and
responds by running small programs that call its modules. No neural
networks, just Python.

This repo ships the learning kernel, the runtime and a small bootstrap
curriculum; skills come from your data and plugins.

```console
$ uv sync
$ uv run nagi respond hello
...?
$ uv run nagi learn
learned 5 records from 0-how-to-learn.jsonl
learned 3 records from greeting.dpo.jsonl
learned 3 records from greeting.rlhf.jsonl
learned 58 records from greeting.sft.jsonl
...
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
```

Teaching is JSON Lines. A record goes to the learner whose shape it fits,
and a completion is a thought and a program:

```json
{"prompt": "hi nagi, how are you",
 "completion": {"think": "They greet me and ask how I am. Greet back, then say how I am.",
                "code": "speech.say(greeting.hello())\nspeech.say(greeting.doing_well())"}}
```

## Docs

- [Overview](docs/overview.md): what Nagi is and isn't
- [Getting started](docs/getting-started.md): install, commands, memory
- [Teaching](docs/teaching.md): assets, learners, slots, evals
- [Reasoning](docs/reasoning.md): facts, rules, proofs
- [Code mode](docs/code-mode.md): the programs responses and learners run
- [Plugins](docs/plugins.md): your own modules, learners and curricula
- [Architecture](docs/architecture.md): how a sentence becomes a response
- [Benchmarks](docs/bench.md): CLINC150, Banking77, SNIPS, bAbI, ProofWriter
- [Development](docs/development.md): working on Nagi itself
- [FAQ](docs/faq.md)

What comes next is in [ROADMAP.md](ROADMAP.md).

## Develop

```console
$ uv run pytest
```
