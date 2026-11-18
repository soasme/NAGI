# Overview

Nagi is a small assistant that you teach. It ships knowing how to learn and
a little of what a young child knows. Everything else comes from the data
and code you give it.

There is no neural network. Nagi is about 1,300 lines of Python with no
dependencies. What it learned is a JSON file you can read.

## The ideas

**It learns how to learn.** The only thing built into Python is how to
learn a *learner*: a record shape plus a small program saying what to do
with records of that shape. SFT, DPO and RLHF are not code in Nagi. They
are learners taught in the first lesson of the curriculum, and you can
teach new ones or replace them.

**Responses are programs.** Nagi never stores fixed replies. Every response
is an optional chain of thought and a short program that calls modules,
like `speech.say(greeting.hello())`. Modules are plain Python functions,
so a response can check the time, keep a list or prove a fact.

**Knowledge is data.** Facts are triples (`whale | is | mammal`) and rules
are sentences (`{x} is {z} if {x} is {y} and {y} is {z}`). Nagi answers by
proving, and it can think the proof out loud.

**Memory adds up.** Every lesson changes memory by adding to it: a
prompt's weight toward a response, a response's value, a fact or a rule.
So lessons can be taught in any order, and repeating one does no harm.

**Core is the first plugin.** Nagi's own modules and curriculum are
registered with the same entry points a plugin uses. Anything you build
plugs in the same way.

## What it is not

- Not a language model. It does not generate text. It runs the program of
  the response it understood, or says `...?`.
- Not general. It understands the kinds of sentences it was taught, with
  some tolerance for extra words, and it is built to say "I don't know"
  rather than guess.
- Not trained by gradient descent. Learning is counting and adding, so it
  is fast, inspectable and reversible.

## Where it stands

Working today: the learning kernel, evals, plugins, intent capture with
slots, code mode, and reasoning with facts and rules. The curriculum covers
greetings (t0), animal sounds (t1), colors, feelings and numbers (t2), and
kinds of things (t3).

On public benchmarks, Nagi scores 100% on 18 of bAbI's 20 tasks (and 99.7%
and 98.9% on the other two) and 100% on ProofWriter, closed and open world.
Reading real assistant requests is weaker: 76% on CLINC150, 79% on
Banking77, 94% on SNIPS.
See [Benchmarks](bench.md).

Planned: memory layers and packages, learning in conversation, typed
thoughts, planning, and the rest of the t0 to t5 curriculum. See
[ROADMAP.md](../ROADMAP.md).
