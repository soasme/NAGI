# Architecture

Nagi has two paths through it: **learning**, which turns records into
memory, and **responding**, which turns a sentence into a program run.
Both go through code mode, and both meet in memory.

```
              learning                                 responding

 asset.jsonl ──► learner (by shape) ──► learn.*      "hey nagi, how are you"
                        │                  │                   │
                        ▼                  ▼                   ▼
                    ┌──────────────── memory ────────────┐  1. token in
                    │ learners   responses   facts       │  2. intent capture
                    │            (prompts,   rules       │  3. generate
                    │             value)     state       │         │
                    └────────────────────────────────────┘         ▼
                                                           program runs on a Turn
                                                           → thoughts, said
```

## Modules

| File | Does |
|---|---|
| `src/nagi/__init__.py` | the `nagi` command |
| `src/nagi/brain.py` | `Brain`: memory, learning, responding, load and save |
| `src/nagi/learning.py` | `Learner` (shape and program) and `Lesson` |
| `src/nagi/tokens.py` | stage 1: byte-pair tokens |
| `src/nagi/intent.py` | stage 2: intent capture, slots, skips |
| `src/nagi/generate.py` | stage 3: choosing and running a response |
| `src/nagi/code.py` | code mode: `Program` and `Turn` |
| `src/nagi/knowledge.py` | facts, rules and backward chaining |
| `src/nagi/evals.py` | eval sets and reports |
| `src/nagi/plugins.py` | entry point registries and curricula |
| `src/nagi/scaffold.py` | `nagi new` |
| `src/nagi/api.py` | the stable surface for plugins |
| `src/nagi/modules/` | core's modules: `speech`, `greeting`, `reason`, and `learn` for learners |
| `src/nagi/assets/` | the bundled curriculum, `t0/` to `t3/` |

## Learning

`Brain.learn` reads an asset line by line. A learner record is kept as
taught. Any other record goes to the most recently taught learner whose
shape it fits, and that learner's program runs on a `Lesson`. Its calls to
`learn.*` (or a plugin's learning module) change memory. After the asset,
`Brain.fit` rebuilds what responding needs from memory: the tokenizer, an
intent model per response, and the compiled programs.

## Responding

Three stages, one module each.

1. **Token in** (`tokens.py`). Like tiktoken, Nagi learns byte-pair merges
   from every prompt it was taught, so each taught word becomes one token
   and unseen words fall apart into learned pieces. Words are lowercased,
   stripped of punctuation, and repeated letters squeezed ("hiii" is
   "hi").
2. **Intent capture** (`intent.py`). Each response's prompts form a bigram
   model of token sequences. Nagi reads what was heard with every model,
   skipping untaught words at a cost (so "hey nagi" still fits) and
   filling slots. Words weigh by how much they tell intents apart, as in
   TF-IDF: "spanish" counts for more than "how". A response is captured
   when its reading scores at least −5.2 bits (log₂ probability) per unit
   of weight.
3. **Generate** (`generate.py`). Of the captured responses with value ≥ 0
   whose slots were all heard, run the best fitting program; equal fits go
   to the most valued. If none is captured, say `...?`.

The program runs on a `Turn` that carries the slots, the skipped words
(`residue`), the time, a random source, the knowledge and the modules'
state. What it thinks and says is the response.

## Memory

Memory is one JSON file, versioned:

```json
{"version": 2,
 "learners": {"sft": {"shape": {"prompt": "text", "completion": "completion"}, "code": "..."}},
 "responses": {"<id>": {"think": "...", "code": "...", "prompts": {"hi": 1}, "value": 0}},
 "facts": [["whale", "is", "mammal"]],
 "rules": [{"then": ["{x}", "is", "{z}"], "if": [["{x}", "is", "{y}"], ["{y}", "is", "{z}"]]}],
 "state": {"todo": ["oat milk"]}}
```

A response's id is a hash of its thought and code, so the same completion
taught twice is one entry. A prompt counts toward a response only while
its weight is positive. Nothing derived (tokens, bigrams, compiled
programs) is stored; it is rebuilt on load.

## Plugins

`plugins.py` reads three entry point groups: `nagi.modules`,
`nagi.learning` and `nagi.curricula`. Code mode resolves `module.function`
against the first group for responses and the second for learners, when
the program is compiled. Modules are imported on first use. Core's own
`pyproject.toml` registers `speech`, `greeting`, `reason`, `learn` and the
`nagi` curriculum this way.

## Design rules

- **Learning is data.** Ways of learning are learners taught in assets,
  not Python. Python provides only operations that add to memory.
- **Memory adds up.** Every operation is a sum, so order doesn't matter and
  layers can later be merged by addition.
- **Small, closed code.** Programs are calls and literals only, checked
  and compiled once. Decisions live in modules, where they can be tested.
- **Unknown is an answer.** Nagi says `...?` rather than guess, and evals
  measure false accepts as closely as accuracy.
- **Core is a plugin.** Anything core does with its modules and curriculum,
  a plugin can do with its own.
