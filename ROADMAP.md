# Roadmap

Nagi is a meta-learning framework in plain Python. It learns how to learn,
and users hook in their own training data and code to teach it whatever
they need, from everyday chat to personal and life skills.

This repo does not try to ship every capability. It ships what makes Nagi
Nagi:

- **the learning kernel**: learners taught as data, so new ways of learning
  are taught rather than coded
- **the runtime**: understanding, a reasoning engine, code mode, and layered
  memory
- **the hooks**: a stable way for anyone's data and code to plug in
- **a default curriculum, t0 to t5**: the common knowledge a child has by
  age five, so every Nagi starts out knowing the everyday world (see
  [The default curriculum](#the-default-curriculum-t0t5))

Everything else, like reminders, calendars, weather or wiki parsing, is a
plugin. A plugin can live anywhere, and the repo keeps only a few in
`examples/` to prove the hooks work.

## What goes where

| In this repo | Plugins (users, `examples/`) |
|---|---|
| learning kernel, `learn.*` memory operations | domain learners (CSV of birthdays, MediaWiki pages) |
| code mode runtime and sandbox | domain modules (time, lists, reminders, connectors) |
| understanding: tokens, intents, residue, inbox | domain curricula and their eval sets |
| reasoning engine: traces, contract planner, TLA+ subset | domain TLA+ specs |
| memory layers, forks, packages | shared memory packages |
| eval harness, permissions, audit log | permissions they request |
| t0–t5 curriculum: what a five-year-old knows, and the small modules it needs (numbers, calendar words, knowledge lookup) | specialist knowledge and adult skills |

The test for adding something to core: does it help Nagi *learn*, or is it
needed for Nagi to be Nagi? Knowing what a five-year-old knows is part of
being Nagi. Running your calendar is a skill, so it's a plugin.

## Order of work

Each step unblocks the next. ✅ done, ▶ next.

1. ✅ **Learning kernel**: learners as data; SFT/DPO/RLHF re-taught;
   additive memory operations; versioned memory.
2. ▶ **Evals**: `nagi eval` and eval sets. The gate for taught learners and
   forks, and the way plugin authors know their data works.
3. **Hooks**: plugin modules, learners and curricula from any Python
   package. This is what makes adoption possible, so it comes before
   memory and reasoning grow.
4. **Memory layers and packages**: named teaching layers, export/import,
   keep training a downloaded memory.
5. **Learning in conversation**: forks per conversation, learners taught in
   chat, matched by text pattern, gated by evals.
6. **Formats for thinking and understanding**: typed thought steps, the
   `Understanding` report, and the inbox.
7. **Reasoning engine**: working memory and rules, contract planning, TLA+
   state spaces, check and recover.
8. **Finish t0**: the small talk every Nagi needs, taught with the
   machinery above.
9. **t1–t5**: common knowledge up to age five. Each tier lands once the
   machinery it needs exists (see the table below), so the curriculum also
   tests that machinery.

## 1. Learning kernel ✅

The only learning built into Python is the ability to learn a **learner**:
a record shape plus a code-mode program that may call only `learn.*` and
read `record`. The SFT, DPO and RLHF learners are taught by
`t0/0-how-to-learn.jsonl`. A record goes to the most recently taught learner
whose shape it fits exactly, and teaching a learner under an existing name
replaces it.

Memory operations are sums, so lessons add up in any order:
`learn.prompt(text, completion, weight)` and `learn.value(completion,
delta)`. Later operations (`fact`, `alias`, `rule`, `spec`, `learner`) join
when a step below needs them, and stay sums wherever possible so layers
stay simple.

## 2. Evals

Evals are how Nagi, its curriculum and every plugin know they still work,
and they are what lets learning be gated automatically.

- **Eval sets** sit next to assets (`*.eval.jsonl`) and are never learned.
  They hold prompts with the expected program, negatives that must stay
  unknown, and noisy variants.
- **`nagi eval`** reports accuracy, false accepts and false rejects per
  intent, along with score margins. It also compares two memories (or
  layers) on the same set, which is what the gate needs.
- **`nagi lint`** validates assets without learning them: code compiles,
  shapes are known, no prompt is taught to two intents.

Exit: `nagi eval` runs in CI on t0, at ≥ 95% accuracy with ≤ 2% false
accepts.

## 3. Hooks

A plugin is an ordinary Python package. It adds nothing core doesn't
already understand: modules, learners, assets and evals.

- **Modules**: register with an entry point. Code mode resolves
  `calendar.events_on(...)` through the registry, imports lazily, and
  resolves at compile time, so plugin calls cost the same as core ones.
  ```toml
  [project.entry-points."nagi.modules"]
  calendar = "nagi_calendar.module"
  ```
- **Curricula**: an entry point naming a directory of tiers, assets and
  evals. `nagi learn --curriculum calendar` teaches it, and `nagi eval
  --curriculum calendar` checks it.
- **Learners**: already data, so a plugin ships them in its curriculum.
  Plugins may add **shape types** (`date`, `csv-row`) that learners can
  match on.
- **Without packaging**: `--modules DIR` and `nagi learn FILE` for trying
  things out.
- **Stability**: the hook surface is versioned on its own (`nagi.api`), and
  core changes may not break it within a major version.
- **`nagi new plugin NAME`**: scaffolds a package with a module, a
  learner, an asset, an eval and a test.

Exit: an `examples/todo` plugin, installed into a clean environment, adds a
module and a curriculum, learns, passes its own evals, and is used in chat,
with no change to core.

## 4. Memory layers and packages

Memory is a stack of layers: a read-only **base**, one or more named
**teaching** layers, and an optional **fork** per conversation. All of
Nagi's learning is sums, so a layer is a delta, the effective memory is the
sum of the layers, and merging is addition, the way a LoRA adapter adds to
frozen weights. Forgetting is a tombstone that hides a lower entry.

- **Separate teaching memories**: `--teach family` and `--teach work` on one
  base, trained differently and compared with `nagi eval`.
- **Packages**: `nagi memory export` and `nagi memory import FILE|URL` move
  a layer or a stack. A package carries a manifest (format version, base
  hash, provenance, eval scores), the sums, and the tokenizer state, so a
  downloaded memory keeps training exactly as if it had been trained
  locally. Imported code still compiles under the allow-list, and a
  package never brings permissions.

Exit: two teaching layers on one base answer the same prompt differently.
A downloaded package keeps training and matches a locally trained twin.

## 5. Learning in conversation

- **Conversation state**: recent turns and a pending question, so "yes"
  means something only after a question.
- **Forks**: each conversation writes to its own fork. At the end, the fork
  is dropped, kept under a name, or merged into a teaching layer if
  `nagi eval` doesn't regress.
- **Learners matched by text pattern**, not only by record shape. With
  `learn.learner`, a sentence can teach a new way of learning:
  > "From now on, when I say *X means Y*, treat X as another word for Y."

  That becomes a learner with pattern `{x} means {y}` and code
  `learn.alias(x, y)`, trialled in the fork and kept behind the eval gate.
- **Feedback as reward**: 👍 or "wrong" after a reply adds an RLHF lesson to
  the fork.
- **Learners have values**: a learner whose lessons get thumbs down fades.

Exit: a new way of learning is taught in at most three turns, used
straight away, still there after a restart, and rejected automatically if
it regresses evals.

## 6. Formats for thinking and understanding

These are format changes, and they must land before more curriculum is
written in the old formats.

- **Typed thought steps**: `think` becomes a list of steps (`note`, `goal`,
  `recall`, `do`, `check`, `ask`, `conclude`, `step`), and a plain string
  still means one `note`. Each turn records the trace of what actually ran.
  The trace is also the training format, so SFT teaches how to reason and
  DPO teaches which reasoning is better.
- **`Understanding`**: intent capture returns the intents that fit with
  their scores and margins, the words matched, and the **residue** (the
  words skipped). Residue can fill open slots ("remind me about *the
  dentist thing*"). Confidence falls into three bands: do it, confirm it,
  or say it's unknown and offer to learn.
- **Inbox**: residue and unknown inputs are counted locally, and
  `nagi inbox` turns the most common ones into lessons.

Exit: t0 assets use typed thoughts; on noisy variants, ≥ 90% still run the
right program, and every skipped word reaches the inbox.

## 7. Reasoning engine

The engine is plain Python, with no neural model. It is generic, and
plugins supply the domain: modules with contracts, rules, and specs.

- **Working memory and rules**: facts, slots and step results; rules taught
  by learners; forward chaining to derive, backward chaining to answer.
- **Contract planning**: type annotations are contracts
  (`parse(turn, text: Text) -> Date`). The planner chains calls from what
  is known to the goal type, best-first within a budget, ordered by learned
  values. Recurring plans are learned from traces as methods.
- **TLA+ state spaces**: a skill can be a TLA+ spec. When the situation
  falls inside its state space, Nagi searches transitions to an `End`
  state, runs the path one action at a time (`Do("module.fn", …)` calls
  code, `Ask(…)` pauses for the user), and checks invariants at every step.
  Nagi evaluates a TLA+ subset in Python, compiled once like code mode, and
  TLC proves invariants in CI only. A multi-turn task is just a path
  through the spec.
- **Check, recover, explain**: verify against the goal, backtrack or ask,
  answer within the time budget, and replay the trace for "why?".

Exit: a reference spec and a contract-planning scenario, both shipped as
`examples/` plugins, work end to end. Their traces replay to the same
result, TLC passes, and p95 thinking time is ≤ 50 ms.

## 8. Finish t0

The small talk every Nagi needs, taught as curriculum, not coded: greeting
(done), farewell, thanks, apology, yes/no, "who are you", feelings, and how
to teach Nagi in chat. Tolerance for typos, slang and word forms comes from
the shared machinery (aliases from step 5, residue from step 6), not from
special cases.

Exit: the t0 eval passes, noisy variants included, with every intent
competing.

## The default curriculum: t0–t5

Tiers follow a child's first five years. Each tier teaches common
knowledge, never trivia, and ships an eval that reads like a quiz for a
child of that age. A tier needs certain machinery, so it lands only after
that machinery exists. The knowledge itself is data, written as plain
sentences or simple records, so it doubles as the reference for how users
teach Nagi their own world.

| Tier | Age | What Nagi learns | Needs | Sample eval |
|---|---|---|---|---|
| **t0** | 0–1 | how to learn; greetings, farewells, thanks, sorry, yes/no; "who are you"; being taught in chat | kernel ✅, evals, conversation | "bye!" → a farewell |
| **t1** | 1–2 | words for things: family, body parts, animals and their sounds, food, toys, clothes; basic needs (hungry, tired) | facts (`learn.fact`), pattern learners, knowledge lookup | "what does a cow say?" → "Moo!" |
| **t2** | 2–3 | colors, shapes, big/small, hot/cold and other opposites, counting to 10, feelings, my name and age, daily routines | slots, numbers module, personal facts | "what color is grass?" → "Green." |
| **t3** | 3–4 | counting to 20; adding within 5; morning/afternoon/night; weather; in/on/under; categories ("is a whale a fish?"); helpers (doctor, firefighter); safety rules | rules and inference, typed thoughts | "is a whale a fish?" → "No, it's a mammal." |
| **t4** | 4–5 | the alphabet; rhymes; days of the week; seasons; what comes next in a sequence; where animals live; how plants grow; washing hands and why; following two- or three-step instructions | sequences and planning in code, the inbox for gaps | "what comes after Tuesday?" → "Wednesday." |
| **t5** | 5 | counting to 100; adding and taking away within 10; yesterday, today, tomorrow; telling time on the hour; left and right; simple cause and effect ("if it rains, take an umbrella"); fairness and taking turns; the rules of simple games | the reasoning engine: rules, planning, TLA+ for game rules | "I have 3 apples and eat 1. How many left?" → "2." |

Rules for the curriculum:
- **Knowledge is data**: facts, rules and specs go in assets. Core gets only
  the small, generic modules a five-year-old's knowledge needs (`numbers`,
  `calendar` words, `knowledge` lookup), never a module per topic.
- **Answers show their reasoning**: from t3 on, answers come with typed
  thoughts ("a whale breathes air and feeds milk to its young → mammal"),
  so the curriculum also teaches *how* to reason.
- **Safe by design**: the curriculum covers safety rules (hot stoves,
  crossing the street) and never asks for or stores personal details
  beyond what the user chooses to teach.
- **Measured like a child**: each tier's eval is a quiz. A tier is done
  when Nagi passes it, noisy variants included, without regressing the
  tiers below.

## Cross-cutting

**Scale**. These are done when evals show they are needed, but the design
must not block them.

| Bottleneck | Now | Plan |
|---|---|---|
| Tokenizer | retrained from all prompts on every load | persist ranks per layer; train only on new records |
| Intent capture | scores every response every turn | inverted index from token to intents |
| Learner dispatch | linear scan | index by shape keys and pattern tokens |
| Layers | none | flatten once per load; forks overlay a small dict |
| Plugin modules | n/a | lazy import; resolved at compile time |
| Planning | none | index modules by contract types; memoize state-space search |
| Memory | one JSON file | SQLite per layer once it grows; keep JSON export |
| Tool calls | ~4M/s compiled closures | keep calls free of per-call lookups |

**Trust**. Everything stays local by default. Plugins declare permissions
(`__permissions__ = ["network"]`); the user grants them once, and code
mode, the planner and imported packages all refuse ungranted modules. Side
effects go to an audit log with their trace. Every record and layer
carries its source, so a bad lesson can be traced and undone.

## Decisions to make

Before step 3:
1. **Module namespace**: whether plugin modules share one flat namespace
   with core (`calendar.x`) or are prefixed by plugin, and what happens on
   a name collision.
2. **Shape types from plugins**: how a plugin defines a type, and whether
   types are checked in Python or declared as data.

Before step 4:
3. **Layer semantics**: tombstones, and how merging interacts with the eval
   gate.
4. **Package format**: one file or a directory; versioning of assets and
   packages (memory is already v2).

Before step 6:
5. **Thought step vocabulary**: whether these step kinds cover rules,
   plans and TLA+ transitions without later breaking changes.
6. **Slot syntax**: `{name}` placeholders, shared by intents and pattern
   learners.

Before step 7:
7. **The TLA+ subset**, and how `Ask` and `Do` bind to modules while specs
   stay valid for TLC.
8. **Contract types**: a fixed core set (`Text`, `Date`, `Number`, …) that
   plugins extend.

Before step 9:
9. **Fact format**: plain sentences read by pattern learners, structured
   records, or both, and how a fact links to the tier that taught it.
