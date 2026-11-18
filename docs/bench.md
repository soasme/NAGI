# Benchmarks

`bench/` measures Nagi on public data, not only on its own evals. Each
script downloads its dataset to `~/.cache/nagi/` on first run.

```console
$ uv run python bench/clinc150.py        # intent capture
$ uv run python bench/banking77.py       # close intents
$ uv run python bench/snips.py           # slots
$ uv run python bench/babi.py            # reasoning over stories
$ uv run python bench/proofwriter.py     # reasoning over rules in English
$ uv run python bench/proofwriter.py --world OWA   # where unknown isn't false
```

| Bench | Measures | Nagi is taught |
|---|---|---|
| [CLINC150](https://github.com/clinc/oos-eval) | 150 assistant intents, and questions none of them covers | only how to learn, then the 15,000 train prompts as SFT, one response per intent |
| [Banking77](https://github.com/PolyAI-LDN/task-specific-datasets) | 77 close intents of one bank's customers | only how to learn, then the 10,003 train prompts as SFT |
| [SNIPS](https://github.com/sonos/nlu-benchmark) | 7 assistant intents, and which words fill each slot | only how to learn, then the train split as SFT, each annotated span a slot and its words a fact |
| [bAbI](https://research.facebook.com/downloads/babi/) | answering questions about short stories | the curriculum, then `bench/babi.jsonl`: how to read the stories' sentences, and rules for places, times, directions, ways, positions, sizes and motives |
| [ProofWriter](https://allenai.org/data/proofwriter) | true or false from facts and rules told in English, up to 5 steps deep, and in the open world also unknown | only how to learn, the theories' words as facts, and one prompt per sentence shape in the train split |

## Results

**CLINC150**

| | In-scope accuracy | Out-of-scope recall | Nearest intent |
|---|---|---|---|
| Bigram capture | 69.1% | 66.4% | 75.3% |
| + words weighed by 1 + IDF | 76.1% | 81.7% | 82.9% |

"Nearest intent" is in-scope accuracy as if nothing were rejected.
Teaching takes about 40 s, nearly all of it retraining the tokenizer;
understanding takes about 3.5 ms a turn over 150 intents.

**SNIPS** (700 test sentences)

| | Understood: intent | slot F1 | Nearest reading: intent | slot F1 |
|---|---|---|---|---|
| Slot words cost like skips | 37.4% | 21.2% | 96.4% | 34.0% |
| + words known to be what a slot holds are free | 94.3% | 69.2% | 96.6% | 69.0% |
| + only if every word is part of what was told | 93.7% | 75.8% | 96.1% | 75.4% |

**Banking77** (3,080 test questions): 78.6% understood, 81.2% nearest
intent.

**bAbI** (1,000 questions per task): all 20 tasks. Tasks 1, 2, 4, and 6 to
20 score 100%. Task 5 (three-argument relations) scores 99.7%: its misses
ask about an older gift between the same two people, and Nagi remembers
the newest. Task 3 (three supporting facts) scores 98.9%: a thing was
"before the kitchen" where its carrier came to the kitchen from, which
Nagi keeps only for the carrier's latest visit there.

**ProofWriter** (depth-5 test sets: 985 closed-world theories with 20,058
questions, 948 open-world ones with 20,030)

| Proof depth | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Closed world | 100% | 100% | 100% | 100% | 100% | 100% |
| Open world (true, false or unknown) | 100% | 100% | 100% | 100% | 100% | 100% |

**ARC-Easy and GSM8K**: the curriculum declines every question (0
answered, 0 false accepts). They become meaningful once t1 to t5 and the
reasoning engine land.

## What the runs showed

- Backing the bigrams off to single tokens raised CLINC in-scope accuracy
  about 2 points, but broke the shipped evals (92%) and doubled their false
  accepts, so it was not kept.
- The curriculum with the example plugins accepted 5.1% of CLINC's
  sentences, against the 2% target, mostly through open residue ("i need
  *to start a timer*" fit todo's "i need …"). With todo and birthdays on
  slots it is 4.0%. Most of the rest are prompts that tolerate trailing
  words ("how do you do" fits "how do you say dog in spanish"): one score
  averaging fit and skips allows about three quarters of a sentence to be
  skipped.
- Typed slots (`{feeling:feeling}`) let knowledge decide what a slot can
  hold. That fixed "i am a teacher" being read as a feeling, where every
  scoring change tried cost CLINC more than it gained.
- A slot word costs what a skip does. Cheaper slots let one slot swallow a
  whole sentence; a dearer skip cost CLINC more than it saved. What stops
  "what time is it" fitting "what is a {thing}" is that a response reading
  a slot needs it heard.
- Typed slots were first checked after reading, so a typed reading could
  lose to an untyped one and be thrown away. Checked while reading, they
  cost nothing, since knowledge vouches for them.
- Rules that call each other freely blow up a depth-first proof: bAbI task
  17's inverse, transitive and cross-axis rules ran out of budget before
  trying the plain transitive one. Telling both directions, and deriving
  `is left of` only from told `left of` facts, keeps every step on a fact
  and scores 100%. Rules must be written with the search in mind, as in
  Prolog.
- With the whole curriculum, ProofWriter slowed sixfold and missed deep
  proofs: "a thing does what its kind does" turns each goal about Dave into
  a search over everything Dave is. A theory is meant to be all there is,
  so the bench teaches only how to learn. Prior knowledge general enough to
  always apply is also general enough to always cost.
- SNIPS shows what slots lack. A slot word costs what a skip does, so a
  sentence that is mostly a playlist or film name falls below the
  threshold: Nagi picks the right intent 96% of the time but understands
  only 37%. Charging slot words less let slots swallow sentences again (48%
  false accepts on the shipped evals). And a slot knows nothing of what it
  holds, so where two slots meet ("my | Classical Relaxations") any split
  costs the same. Both point at slots learning their contents, as typed
  slots do through knowledge. So a plain slot's words are now free when
  Nagi knows they are what the slot is named for ("cita romántica is a
  playlist"), and cost a skip otherwise: understood intents rose from 37%
  to 94% and slot F1 from 21% to 69%, with no new false accepts on CLINC.
  Facts drop articles, so "the album" was told as much as "album", and a
  free slot swallowed the "the" that SNIPS leaves out: a span is now free
  only if each of its words is part of what was told (slot F1 69% to 76%).
  Unknown values still split arbitrarily where two slots meet. A free
  slot can also lure words out of place: in bAbI's "The hallway is east of
  the bathroom.", the known place "bathroom" was read into `{place}` rather
  than `{other}`, which names no kind, until the lesson typed it
  `{other:place}`. Name a slot for what it holds. Checking free words by
  proof made bAbI five times slower, so they are only looked up.
- The open world needs saying "no" apart from "I don't know":
  `reason.ask` tries the fact, then its opposite. Its deep misses (95% at
  depth 5) were two things. "Blue people are not round." was read without
  its "not", and the loop guard cut "who eats the dog?" while showing "the
  dog likes the tiger", which needs someone else who eats the dog. A goal
  with one unknown may now recur once, which also took the closed world's
  depth 5 to 100%.
- bAbI 10 ("Bill is either in the school or the office") is `reason.ask`
  too: "is away from" holds when someone is somewhere else, or might only
  be somewhere else. bAbI 14 keeps where someone was at each time, with a
  rule per place for "before the office": a rule whose relation is a
  variable matches every goal, and its search ran out of budget.
- bAbI 19 finds a two-step way with rules whose conditions have a
  variable relation ("{b} {r} {a} and {r} step {d}"), which is cheap,
  unlike a variable relation in a conclusion. `speech.answer` says several
  parts ("S, s."). It also found that `term` dropped a variable named
  `{a}`, taking it for an article.
- Rules are indexed by the relation they conclude, as facts are by term, so
  a goal tries only rules that could show it: bAbI runs in 4.5 minutes, from
  15. Size reasoning (task 18) had the same trouble as positions, and the
  same cure: tell both ways, and derive only a told step at a time.
- CLUTRR (kinship stories) is not tried yet: its crowd-written sentences
  each tell two or three facts ("Clarence's granddaughter, Emily, was busy
  helping her brother, Michael"), and Nagi reads one intent per sentence.

## Adding a benchmark

A bench is one script in `bench/` with a docstring naming the dataset, the
paper and how to run it. It downloads to `~/.cache/nagi/`, builds a fresh
`Brain`, teaches it only what the docstring says, and prints the scores.
Teach the general shape of the data (sentence forms, rules), never the test
answers. Record the result here, with what the run showed.
