# Benchmarks

`bench/` measures Nagi on public data, not only on its own evals. Each
script downloads its dataset to `~/.cache/nagi/` on first run.

```console
$ uv run python bench/clinc150.py        # intent capture
$ uv run python bench/snips.py           # slots
$ uv run python bench/babi.py            # reasoning over stories
$ uv run python bench/proofwriter.py     # reasoning over rules in English
```

| Bench | Measures | Nagi is taught |
|---|---|---|
| [CLINC150](https://github.com/clinc/oos-eval) | 150 assistant intents, and questions none of them covers | only how to learn, then the 15,000 train prompts as SFT, one response per intent |
| [SNIPS](https://github.com/sonos/nlu-benchmark) | 7 assistant intents, and which words fill each slot | only how to learn, then the train split as SFT, each annotated span a slot and its words a fact |
| [bAbI](https://research.facebook.com/downloads/babi/) | answering questions about short stories | the curriculum, then `bench/babi.jsonl`: how to read the stories' sentences, and rules for places, directions, positions, sizes and motives |
| [ProofWriter](https://allenai.org/data/proofwriter) | true or false from facts and rules told in English, up to 5 steps deep | only how to learn, the theories' words as facts, and one prompt per sentence shape in the train split |

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

**bAbI** (1,000 questions per task). Tasks 1, 2, 4, 6, 7, 8, 9, 11, 12, 13,
15, 16, 17, 18 and 20 score 100%. Task 5 (three-argument relations) scores
99.7%: its misses ask about an older gift between the same two people, and
Nagi remembers the newest. Not yet tried: 3 (three supporting facts) and 14
(time reasoning) need facts in time order; 10 (indefinite knowledge) needs
"maybe", which `check` can't say; 19 (path finding) needs answers built
from steps.

**ProofWriter** (closed world, depth-5 test set: 985 theories, 20,058
questions; 99.96% overall)

| Proof depth | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Accuracy | 100% | 100% | 100% | 100% | 99.9% | 99.7% |

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
  Unknown values still split arbitrarily where two slots meet. A free
  slot can also lure words out of place: in bAbI's "The hallway is east of
  the bathroom.", the known place "bathroom" was read into `{place}` rather
  than `{other}`, which names no kind, until the lesson typed it
  `{other:place}`. Name a slot for what it holds. Checking free words by
  proof made bAbI five times slower, so they are only looked up.
- CLUTRR (kinship stories) is not tried yet: its crowd-written sentences
  each tell two or three facts ("Clarence's granddaughter, Emily, was busy
  helping her brother, Michael"), and Nagi reads one intent per sentence.

## Adding a benchmark

A bench is one script in `bench/` with a docstring naming the dataset, the
paper and how to run it. It downloads to `~/.cache/nagi/`, builds a fresh
`Brain`, teaches it only what the docstring says, and prints the scores.
Teach the general shape of the data (sentence forms, rules), never the test
answers. Record the result here, with what the run showed.
