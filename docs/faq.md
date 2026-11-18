# FAQ

**Is this an LLM, or does it use one?**
No. There is no neural network and no model download. Nagi counts and adds
what it is taught, reads sentences with bigram models, and proves facts by
backward chaining. It is plain Python with no dependencies.

**Then why talk about SFT, DPO and RLHF?**
Because those are the shapes people already have training data in. In
Nagi they are not algorithms but learners taught in the first lesson: SFT
adds weight from a prompt to a completion, DPO adds to the chosen and takes
from the rejected, RLHF adds the reward. You can read and replace them in
`src/nagi/assets/t0/0-how-to-learn.jsonl`.

**Why does it answer `...?`**
It didn't understand. Either nothing was taught that fits the sentence well
enough, or what fits needs a slot the sentence doesn't fill. Teach a prompt
for it, or check that `nagi learn` was run against the memory you are
using.

**How do I see why it said something?**
`nagi respond --think ...` prints the response's chain of thought and,
for questions, the proof. Memory is readable JSON at
`~/.nagi/memory.json`.

**It understood a sentence it shouldn't have. How do I fix that?**
Add the sentence to an eval set with `"expect": null`, then find the prompt
that captured it. Usually a prompt is too open, like `i need {item}`; drop
or narrow it. `nagi eval` reports the false accept rate.

**Can it learn while we talk?**
It can learn facts and rules from conversation through `reason.tell`,
`reason.update` and `reason.rule`, and modules can keep state. Being
taught new prompts or new ways of learning in chat is planned; see
[ROADMAP.md](../ROADMAP.md).

**Does it send anything anywhere?**
Core doesn't. It runs locally and writes only its memory file, and
benchmarks download their datasets when you run them. Plugins are ordinary
Python, so check what the ones you install do.

**How big can it get?**
CLINC150's 15,000 prompts teach in about 40 seconds and read in about
3.5 ms a turn. The known bottlenecks, and plans for each, are in the
roadmap's Scale table.

**Why can't a program use `if`, variables or loops?**
To keep programs small enough to check and fast enough to run, and to push
decisions into modules, where they are Python and can be tested. A program
says *what* to do; modules say *how*.

**Can two plugins use the same module name?**
No. Names share one namespace per entry point group, and a clash is an
error naming both packages.

**My memory file stopped loading.**
The memory format changed. Delete the file and run `nagi learn` again,
along with any curricula and data files you had taught.

**Why the name?**
Nagi is Not Artificial General Intelligence. It is a small system that
learns what you teach it, and says so when it doesn't know.
