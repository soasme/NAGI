# Roadmap

Goal: Nagi handles everyday personal, life and chat scenarios well. It should
know who you are, keep track of your tasks and time, hold a conversation
across turns, and learn new skills from you, all as plain Python running
locally.

Four pillars matter more than any single skill:

| Pillar | Nagi… |
|---|---|
| **A. Understand** | catches known intents in messy input, and keeps what it didn't understand |
| **B. Think** | reasons step by step in code and in TLA+ state spaces, checks its answer, and shows its work |
| **C. Learn** | learns how to learn: new ways of learning are taught, not coded (**highest priority**) |
| **D. Remember** | keeps memory in layers you can train separately, download, keep training, and fork per conversation |

Today Nagi can greet. It has the three stages (token in → intent capture →
generate), code-mode programs calling `nagi.modules`, and a learning kernel
whose SFT, DPO and RLHF learners are taught, not coded. Each pillar is built
in stages that run through the phases. A phase is done when its exit
criteria pass in CI, not when its code exists.

## Order of work

Each step unblocks the next. ✅ done, ▶ next.

1. ✅ **C1, C2**: learning kernel; learners as data; SFT/DPO/RLHF re-taught;
   additive memory operations; versioned memory.
2. ▶ **Phase 0 evals**: `nagi eval` and eval sets. The eval gate in C3 and
   D4, and every later phase's exit criteria, depend on it.
3. **D1–D3**: memory layers, named teaching layers, export/import.
   Additive memory (step 1) already makes a layer a plain delta.
4. **D4 + C3**: conversation forks, and learners taught in chat, matched
   by text pattern and gated by evals.
5. **A1 + B1**: the `Understanding` report with inbox; typed thought steps.
   These are format work that must land before Phase 3 assets are written.
6. Phase 3 onward, in order.

## Pillar C: Learn how to learn (highest priority)

Hard-coded learning would need a new branch for every later feature: chat
teaching, aliases, rules, wiki text, specs. Instead, learning itself is
something Nagi is taught.

**C1. A small bootstrap kernel** ✅. The only learning built into Python
is the ability to learn a **learner**, plus **memory operations** that are
all sums, so lessons add up in any order:
- `learn.prompt(text, completion, weight)`: recognition, while the total
  weight is positive
- `learn.value(completion, delta)`: preference

Later operations join as their pillars need them: `learn.fact`,
`learn.alias`, `learn.rule`, `learn.spec`, and `learn.learner` (C3).
Everything else is data, compiler-style: `t0/0-how-to-learn.jsonl` teaches
Nagi how to read SFT, DPO and RLHF records, and the hard-coded `learn` is
gone. Proof of the bootstrap: on the curriculum, the taught learners
produce the same responses, the same recognized prompts in the same order,
and the same values as the hard-coded version did. The only addition is
negative evidence: a rejected completion's prompt weight goes below zero
instead of being dropped.

**C2. Learners are data** ✅. A learner says what input it handles and runs
a code-mode program that may call only `learn.*` and read `record`:

```json
{"learner": "dpo",
 "shape": {"prompt": "text", "chosen": "completion", "rejected": "completion"},
 "code": "learn.prompt(record.prompt, record.chosen, 1)\nlearn.prompt(record.prompt, record.rejected, -1)\nlearn.value(record.chosen, 1)\nlearn.value(record.rejected, -1)"}
```

A record goes to the most recently taught learner whose shape it fits
exactly. Teaching a learner under an existing name replaces it, so Nagi can
be taught to learn differently. Learners are compiled once like any other
program. Once layers exist, they will write only to the active memory layer
(Pillar D).

**C3. Teaching how to learn, on the fly** (Phase 2). After bootstrapping, a
new way of learning is taught in chat or in an asset, and works right away:

> "From now on, when I say *X means Y*, treat X as another word for Y."

That sentence becomes a learner (pattern `{x} means {y}`, code
`learn.alias(x, y)`). This needs two additions to C2:
- learners that match freeform text by **pattern**, using the same
  understanding as Pillar A, not only records by shape
- `learn.learner`, so a lesson can produce a learner

Three things keep taught learning safe:
- **Trial in a fork**: a new learner first runs in a fork of memory (D4).
- **Eval gate**: it is merged only if evals don't regress. Learning to learn
  means learning what works.
- **Learners have values**: DPO and RLHF apply to learners too, so a
  learner whose lessons get thumbs down fades.

**C4. Freeform and wiki text** (Phase 4). A wiki learner reads MediaWiki or
Markdown:
- headings → topics
- infoboxes and definition lists → facts
- links → relations between topics
- sentences matching taught patterns ("*X* is a *Y*", "*X* was born in
  *Y*") → facts
- every sentence → a retrieval index, so "what is X?" is answered with the
  source sentence

This knowledge goes into memory with provenance (page, revision, line), kept
apart from personal facts. The extraction patterns are themselves learners,
so users can teach new ones.

Pillar exit: a new way of learning (aliases, or a CSV of birthdays) is
taught in at most three turns, used immediately, still there after a
restart, and automatically rejected if it regresses evals. SFT, DPO and
RLHF run only as taught learners.

## Pillar D: Remember in layers

**D1. Memory is a stack of layers** (Phase 1):

```
base       the curriculum, read-only
teaching   what you taught (one or more, named)
fork       this conversation (optional, throwaway)
```

Everything Nagi learns is counts and sums: prompt counts, bigram counts,
values. So a layer is a **delta**, the memory Nagi actually uses is the sum
of its layers, and merging is addition. This is why forks are cheap, the
same way a LoRA adapter is: the base stays frozen, and a layer costs only
what it changes. Forgetting is the one exception: it is a tombstone that
hides a lower entry.

**D2. Separate teaching memories** (Phase 1). Several named teaching layers
share one base, so a user can train Nagi in different directions
(`--teach family`, `--teach work`), switch between them, and compare them
with `nagi eval`.

**D3. Download a memory and keep training** (Phase 1). `nagi memory export`
and `nagi memory import FILE|URL` move a layer or a whole stack. A package
carries:
- a manifest: format version, the hash of the base it builds on,
  provenance, and its eval scores
- the sufficient statistics (counts and sums), plus the tokenizer state

That is enough to keep training a downloaded memory exactly as if you had
trained it yourself. Imported programs and learners still compile under the
allow-list, and a package never brings permissions with it (Phase 7).

**D4. A conversation forks memory** (Phase 2). Each chat can open a fork
layer, copy-on-write, holding what this conversation taught or changed. At
the end, it is dropped, kept under a name, or merged into a teaching layer
behind the eval gate. Pillar C uses the same mechanism to trial new
learners.

Pillar exit: two teaching layers on one base give different answers to the
same prompt. A downloaded package keeps training and matches a locally
trained twin byte for byte. Opening a fork costs O(1); merging a fork costs
O(size of the fork).

## Pillar A: Understand in an open world

Today intent capture skips untaught words at a cost and drops them.

**A1. Understanding is a report, not a label** (Phase 0). Intent capture
returns an `Understanding`: the intents that fit, their scores and the
margin between them, which words matched, and the **residue** (the words
that were skipped). Confidence falls into three bands: confident → do it;
unsure → do it and confirm, or ask "did you mean …?"; unknown → say so and
offer to learn. Thresholds are per intent and calibrated from evals. Every
residue and every unknown input goes to an **inbox**, so the most common
gaps show up first.

**A2. Noise tolerance** (Phase 3): typos (back off to character pieces),
shortenings and slang (aliases, taught by a learner: C3), word forms, and
mixed language, each with its own eval set.

**A3. Residue does work** (Phase 4). In "remind me about the dentist
thing", the residue "the dentist thing" is the reminder's text. Residue
fills open slots before being called noise. When a task can't proceed, Nagi
asks only about the part it missed.

**A4. More than one thing at a time** (Phase 5). Split an utterance into
segments with an intent each ("hi! remind me to call mom at 5, thanks").
Resolve references to earlier turns ("move it to Friday").

Pillar exit: on noisy variants of every taught prompt, ≥ 90% still run the
right program. False accepts stay ≤ 2%. Every skipped word reaches the
inbox.

## Pillar B: Think

The reasoning engine is plain Python, with no neural model. It has one
trace format and two ways to plan: chaining **code** by module contracts,
and walking **state spaces** written in TLA+.

**B1. Thoughts are typed steps** (Phase 0, format only). `think` becomes a
list of steps, and a plain string still means one `note` step:

```json
"think": [
  {"goal": "tell whether lunch at 2:30 fits today"},
  {"recall": "calendar.events_on(time.parse('today'))"},
  {"check": "no event overlaps 14:30-15:30"},
  {"conclude": "it fits"}
]
```

Step kinds: `note`, `goal`, `recall`, `do`, `check`, `ask`, `conclude`, plus
`step` for TLA+ transitions (B4). Each turn records the trace of what
actually ran. `--think` prints it, and the same trace is the training
format.

**B2. Working memory and inference** (Phase 4). Each turn has a working
memory holding facts, slots and step results. Rules are code-mode conditions
with conclusions, taught by a learner (C2). Forward chaining derives what
follows; backward chaining answers questions.

**B3. Planning in code by contracts** (Phases 5–6). Type annotations are
contracts (`parse(turn, text: Text) -> Date`,
`events_on(turn, day: Date) -> Events`). The planner searches for chains of
calls from what is known to the goal type, best-first within a step
budget, ordered by learned values. Recurring plans are learned as
**methods** from SFT traces.

**B4. Planning in state spaces with TLA+** (Phases 5–6). A skill can be a
TLA+ spec instead of, or alongside, a program:

```tla
CONSTANT NULL
VARIABLES text, when, scheduled
Init     == text = NULL /\ when = NULL /\ scheduled = FALSE
GetText  == text = NULL /\ text' = Ask("What should I remind you of?") /\ UNCHANGED <<when, scheduled>>
GetWhen  == when = NULL /\ when' = Ask("When?") /\ UNCHANGED <<text, scheduled>>
Schedule == text # NULL /\ when # NULL /\ ~scheduled /\ scheduled' = TRUE /\ Do("reminder.schedule", <<text, when>>) /\ UNCHANGED <<text, when>>
Next     == GetText \/ GetWhen \/ Schedule
End      == scheduled
Safe     == scheduled => text # NULL /\ when # NULL
```

When the current situation (working memory and conversation) **falls inside
a spec's state space**, Nagi does not need a taught program for that exact
case:
1. Search transitions from the current state to an `End` state,
   breadth-first like TLC, within the turn's budget.
2. Run that path one action at a time. Each action's `Do(...)` is a
   code-mode call, and `Ask(...)` pauses for the user.
3. Check the invariants (`Safe`) at every step.

A situation outside every state space falls back to code planning (B3) or
asks. A multi-turn task, like slot filling or a booking flow, is just a
path through the spec, one transition per turn. Every transition is
recorded as a `step` in the trace.

Nagi evaluates a **subset** of TLA+ in Python, compiled once into closures
like code mode: variables, `Init`, `Next` as a disjunction of actions,
primed variables, `UNCHANGED`, sets, records, and the operators `Ask` and
`Do`. The full TLC model checker runs on the same specs in CI only, to
prove invariants over the whole state space; it is a Java dev tool, never a
runtime dependency. Specs are taught as learning assets by a spec learner
(`learn.spec`).

**B5. Check, recover, explain** (Phase 6). Before replying, `check` steps
verify the result against the goal. On failure Nagi backtracks to the next
plan or path, or `ask`s. Every turn has a time and step budget and returns
the best result found. "Why?" replays the trace.

Pillar exit: a tier-3 eval of personal scenarios. Each answer's trace
replays to the same result. Every shipped spec passes TLC with its
invariants. The reminder spec handles any order of missing details without
a program written for each. p95 thinking time is ≤ 50 ms.

## Phases

### Phase 0: Measure, and fix the formats

- **Eval sets per tier**: held-out prompts, negatives, and noisy variants,
  never learned. **`nagi eval`** reports accuracy, false accepts and rejects,
  margins, and calibration. **`nagi lint`** validates assets without
  learning them.
- **Format versions** for assets, memory and packages, and a migration path.
- **A1** (Understanding and inbox) and **B1** (typed thought steps and
  traces).

Exit: `nagi eval` runs in CI; t0 reaches ≥ 95% accuracy with ≤ 2% false
accepts.

### Phase 1: Learning kernel and layered memory

- ✅ **C1, C2**: the kernel, memory operations, and learners as data. SFT,
  DPO and RLHF are re-taught as learners, and the hard-coded learning is
  deleted.
- **D1, D2, D3**: the layer stack, named teaching layers, and
  export/import with continued training.

Exit: the bootstrap proof (C1) and the layer tests (D) pass.

### Phase 2: Conversation, forks, teaching on the fly

- A `Conversation` with recent turns and a pending question; feedback
  (👍/"wrong") as reward.
- **D4**: each conversation forks memory.
- **C3**: new learners taught in chat, trialled in a fork, merged behind the
  eval gate.
- `nagi inbox` turns the most common unknowns into lessons.

Exit: Pillar C's "taught in three turns" scenario passes.

### Phase 3: Social basics (finish t0)

Farewell, thanks, apology, yes/no, "who are you", feelings, plus **A2**
noise tolerance, using learners from Phase 1–2 wherever possible (aliases
come from a learner, not code).

Exit: t0 eval passes, noisy variants included, with every intent
competing.

### Phase 4: Knowledge and personal memory (t1)

- **C4**: the wiki learner and the knowledge store with provenance.
- Slots in prompts (`my name is {name}`) and **A3** (residue fills slots).
- A personal fact store, separate from skills and from wiki knowledge.
- **B2**: working memory and rules.

Exit: learn a wiki page, then answer "what is X?" with the source sentence.
Answer "when is my sister's birthday?" by inference. "Forget it" erases a
fact.

### Phase 5: Time and tasks (t2)

- Time parsing from `turn.now`; lists; reminders and timers (`nagi daemon`).
- **B4** begins: reminders, lists and clarifying questions as TLA+ specs,
  checked by TLC in CI.
- **A4**: several requests in one utterance, and references to earlier
  turns.
- **B3** begins: contracts on the time, list and reminder modules.

Exit: a scripted week with a fake clock passes end to end, with details
given in any order.

### Phase 6: Thinking that acts (t3)

**B3**, **B4** and **B5** in full: contract planning, state-space search,
checking, backtracking, budgets, "why?". Scenarios: plan my day, weekly
review, scheduling conflicts.

Exit: Pillar B's exit.

### Phase 7: The wider world, with guardrails

Pure tools first (calculator, units, time zones). Then side effects behind
permissions: modules declare them (`__permissions__ = ["network"]`), the
user grants them once, and code mode, the planners and imported packages
all refuse ungranted modules. Then connectors (weather, calendar, email,
files), each a module with contracts and, where it has state, a spec. Every
side effect goes to an audit log with its trace.

Exit: a denied module never runs and is never planned, even when it comes
in a downloaded package.

## Cross-cutting: scale

| Bottleneck | Now | Plan |
|---|---|---|
| Tokenizer | retrained from all prompts on every load | persist ranks in each layer; train only on new records |
| Intent capture | scores every response every turn | inverted index from token to intents; score only the candidates |
| Layers | none | flatten the stack once per load; forks overlay a small dict on top |
| Learner dispatch | three hard-coded cases | index learners by shape keys and leading pattern tokens |
| State-space search | none | budgeted BFS from the current state, memoized per spec; TLC offline |
| Contract planning | none | index modules by contract types; cache plans per goal type |
| Memory | one JSON file, rewritten whole | SQLite per layer once it grows; keep JSON export |
| Tool calls | ~4M/s compiled closures | keep calls free of per-call lookups; batch side effects |

## Cross-cutting: privacy and trust

- Everything stays local by default, the inbox included. Network modules
  are opt-in (Phase 7).
- Facts, knowledge and the inbox are inspectable and erasable.
- Every record and every layer carries its source (curriculum, user, chat,
  wiki page, package), so a bad lesson can be traced and undone.
- Downloaded memory is data, not trust: its code compiles under the
  allow-list, and it brings no permissions.
- Traces explain every action and every transition.

## Decisions to make

Before Phase 0 ends:
1. **Thought step vocabulary**: whether the step kinds of B1 cover rules,
   plans and TLA+ transitions without later breaking changes.
2. **Format versions**: memory is versioned (v2) ✅; assets and packages
   still need it, along with whether a package is one file or a
   directory.

Before Phase 1:
3. **The memory operations**: started with `prompt` and `value` (sums) ✅.
   Still open: whether facts, aliases, rules and specs can stay sums too,
   which keeps layers simple.
4. **Layer semantics**: how tombstones work, and how merging values and
   decisions behind the eval gate interact.

Before Phase 4:
5. **Slot syntax**: `{name}` placeholders in prompts and patterns, shared
   by intents and learners.
6. **One user or many**: whether teaching layers are per user from the
   start.

Before Phase 5:
7. **The TLA+ subset**: which operators Nagi evaluates, and how `Ask` and
   `Do` bind to modules while the spec stays valid for TLC.
8. **Contract types**: a small fixed set (`Text`, `Date`, `Number`,
   `Person`, …), or types defined by modules.
