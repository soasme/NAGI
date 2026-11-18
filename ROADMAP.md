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
| learning kernel, `learn.*` memory operations | domain learners and learning modules (birthdays, MediaWiki pages) |
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
2. ✅ **Evals**: `nagi eval` and eval sets. The gate for taught learners and
   forks, and the way plugin authors know their data works.
3. ✅ **Hooks**: plugin modules, learners and curricula from any Python
   package. This is what makes adoption possible, so it comes before
   memory and reasoning grow.
4. ▶ **Memory layers and packages**: named teaching layers, export/import,
   keep training a downloaded memory.
5. **Learning in conversation**: forks per conversation, learners taught in
   chat, matched by text pattern, gated by evals.
6. **Formats for thinking and understanding**: typed thought steps, the
   `Understanding` report, and the inbox.
7. ◐ **Reasoning engine**: facts, rules and proofs ✅; contract planning,
   TLA+ state spaces, check and recover to come.
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

## 3. Hooks ✅

A plugin is an ordinary Python package registering three kinds of things
with entry points. Core registers its own the same way, so core is just the
first plugin.

| Entry point group | What it is | Called by |
|---|---|---|
| `nagi.modules` | response modules: functions taking a `Turn` | response programs |
| `nagi.learning` | learning modules: functions taking a `Lesson` (core's `learn` is one) | learners |
| `nagi.curricula` | a directory of tiers holding assets and `*.eval.jsonl` | `nagi learn NAME`, `nagi eval NAME` |

What came with it:
- **Learning hooks**, beyond the plan: a plugin's learner reads the user's
  own data shape and calls the plugin's learning module. Learning and
  responding meet in shared state (`lesson.state` is `turn.state`). This is
  what lets users hook in *their data*, not only their code.
- **What modules need for real tasks**: `turn.residue` (the words Nagi
  wasn't taught, such as the item in "add oat milk to my list") and
  `turn.state` (kept in memory between turns). These are the first slice
  of step 6's `Understanding`.
- **Separate namespaces enforce the sandbox**: response programs can't
  reach learning modules, and learners can't reach response modules.
- **`nagi new NAME`** scaffolds a package that passes its own tests and
  evals from the first run. **`nagi plugins`** lists what is installed.
- **`nagi.api`** (`Turn`, `Lesson`, `VERSION = 1`) is the surface plugins
  build on.
- **Two examples**, built with `nagi new` and run by the core test suite
  through real entry points: `examples/todo` (residue and state) and
  `examples/birthdays` (learning from the user's own data file).

Not done, and not needed yet:
- **Plugin shape types**: learning modules validate their own values, so
  the three core types (`text`, `number`, `completion`) have been enough.
- **`--modules DIR`**: `nagi new` plus `uv sync` turned out to be the
  shorter path.

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

- ✅ **Facts and rules**: facts are triples, rules are sentences with
  `{variables}` (a relation can be a variable too), both taught by learners
  or told in conversation. Backward chaining answers, and the proof becomes
  the turn's thoughts. Facts and rules are tried newest first, so a later
  lesson refines an earlier one. Facts are indexed by each term, so a goal
  looks only at facts that could match. 15 of bAbI's 20 tasks score 100%.
  Still to come: forward chaining, step results as facts, and word forms
  (bAbI's "mice" needs a taught plural today).
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
| **t1** ◐ | 1–2 | words for things: family, body parts, animals and their sounds, food, toys, clothes; basic needs (hungry, tired) | facts (`learn.fact`), pattern learners, knowledge lookup | "what does a cow say?" → "Moo!" |
| **t2** ◐ | 2–3 | colors, shapes, big/small, hot/cold and other opposites, counting to 10, feelings, my name and age, daily routines | slots, numbers module, personal facts | "what color is grass?" → "Green." |
| **t3** ◐ | 3–4 | counting to 20; adding within 5; morning/afternoon/night; weather; in/on/under; categories ("is a whale a fish?"); helpers (doctor, firefighter); safety rules | rules and inference, typed thoughts | "is a whale a fish?" → "No, it's a mammal." |
| **t4** | 4–5 | the alphabet; rhymes; days of the week; seasons; what comes next in a sequence; where animals live; how plants grow; washing hands and why; following two- or three-step instructions | sequences and planning in code, the inbox for gaps | "what comes after Tuesday?" → "Wednesday." |
| **t5** | 5 | counting to 100; adding and taking away within 10; yesterday, today, tomorrow; telling time on the hour; left and right; simple cause and effect ("if it rains, take an umbrella"); fairness and taking turns; the rules of simple games | the reasoning engine: rules, planning, TLA+ for game rules | "I have 3 apples and eat 1. How many left?" → "2." |

Shipped so far (◐): t1 `animals`, what 20 animals say; t2 `colors`,
`feelings` (and what helps with each) and `numbers` (words, and what comes
before and after, to twenty); t3 `kinds`, 50
things in 9 kinds, and what follows from a kind (breathes, lives in, is
alive), from one rule: a thing does what its kind does.

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
| Plugin modules | lazy import; resolved at compile time ✅ | keep it so |
| Planning | none | index modules by contract types; memoize state-space search |
| Memory | one JSON file | SQLite per layer once it grows; keep JSON export |
| Tool calls | ~4M/s compiled closures | keep calls free of per-call lookups |

**Benchmarks**. `bench/` measures Nagi on public data rather than only its
own evals. CLINC150 (150 assistant intents and out-of-scope questions,
15,000 training prompts):

| | In-scope accuracy | Out-of-scope recall | Nearest intent |
|---|---|---|---|
| Bigram capture | 69.1% | 66.4% | 75.3% |
| + words weighed by 1 + IDF ✅ | 76.1% | 81.7% | 82.9% |

bAbI (stories and questions; Nagi is taught `bench/babi.jsonl`, sentence
forms with slots and the rules they need, on top of the curriculum). Tasks
1, 2, 4, 6, 7, 8, 9, 11, 12, 13, 15, 16, 17, 18 and 20 score 100% of 1000
each, and 5 (three-argument relations) 99.7%: its misses ask about an
older gift between the same two people, and Nagi remembers the newest.
Not yet tried: 3 (three supporting facts) and 14 (time reasoning) need
facts in time order; 10 (indefinite knowledge) needs "maybe", which `check`
can't say; 19 (path finding) needs answers built from steps.

What the runs showed:

- Backing the bigrams off to single tokens raised CLINC in-scope accuracy
  about 2 points, but broke the shipped evals (92%) and doubled their false
  accepts, so it was not kept.
- The shipped curriculum with the example plugins accepted 5.1% of CLINC's
  sentences, against the 2% target, mostly through open residue ("i need
  *to start a timer*" fit todo's "i need …"). With todo and birthdays on
  slots it is 4.0%. Most of the rest are prompts that tolerate trailing
  words ("how do you do" fits "how do you say dog in spanish"): one score
  averaging fit and skips allows about three quarters of a sentence to be
  skipped.
- Typed slots (`{feeling:feeling}`) let knowledge decide what a slot can
  hold, which fixed "i am a teacher" being read as a feeling where every
  scoring change tried (a dearer missing ending, a dearer skip) cost CLINC
  more than it gained.
- A slot word costs what a skip does. Cheaper slots let one slot swallow a
  whole sentence; a dearer skip cost CLINC more than it saved. What stops
  "what time is it" fitting "what is a {thing}" is that a response reading
  a slot needs it heard.
- Rules that call each other freely blow up a depth-first proof: task 17's
  inverse, transitive and cross-axis rules ran out of budget before trying
  the plain transitive one. Telling both directions, and deriving `is left
  of` only from told `left of` facts, keeps every step on a fact and
  scores 100%. Rules must be written with the search in mind, as in
  Prolog.
- Typed slots were first checked after reading, so a typed reading could
  lose to an untyped one and be thrown away. Checked while reading, they
  cost nothing, since knowledge vouches for them.
- Teaching 15,000 prompts takes about 40 s, nearly all of it retraining the
  tokenizer; understanding takes about 3.5 ms a turn over 150 intents.
- On ARC-Easy and GSM8K the shipped curriculum declines every question
  (0 answered, 0 false accepts). They become meaningful once t1–t5 and the
  reasoning engine land.

**Trust**. Everything stays local by default. Plugins declare permissions
(`__permissions__ = ["network"]`); the user grants them once, and code
mode, the planner and imported packages all refuse ungranted modules. Side
effects go to an audit log with their trace. Every record and layer
carries its source, so a bad lesson can be traced and undone.

## Decisions to make

Settled in step 3:
1. ✅ **Module namespace**: one flat namespace per entry point group,
   shared with core; two packages registering a name is an error naming
   both.
2. ✅ **Shape types from plugins**: not needed yet. Learning modules
   validate values in Python and raise `ValueError` on bad data.

Before step 4:
3. **Layer semantics**: tombstones, and how merging interacts with the eval
   gate.
4. **Package format**: one file or a directory; versioning of assets and
   packages (memory is already v2).

Before step 6:
5. **Thought step vocabulary**: whether these step kinds cover rules,
   plans and TLA+ transitions without later breaking changes.
6. ✅ **Slot syntax**: `{name}` in prompts, read as `slot.name`; the same
   braces are a rule's variables.

Before step 7:
7. **The TLA+ subset**, and how `Ask` and `Do` bind to modules while specs
   stay valid for TLC.
8. **Contract types**: a fixed core set (`Text`, `Date`, `Number`, …) that
   plugins extend.

Before step 9:
9. ◐ **Fact format**: facts are structured records (`subject`, `relation`,
   `object`) and rules are sentences. Still open: plain sentences as facts,
   and how a fact links to the tier that taught it.
