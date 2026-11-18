# Reasoning

Nagi reasons with facts and rules, not with code written for a domain. The
engine is in `src/nagi/knowledge.py`; responses reach it through the
`reason` module.

## Facts

A fact is a subject, a relation and an object, compared as plain words:
lowercase, no punctuation, no articles. So "a whale is a mammal" is
`whale | is | mammal`, and `is a` and `is` are the same relation.

Teach facts with the `fact` learner:

```json
{"subject": "a whale", "relation": "is a", "object": "mammal"}
{"subject": "a cow", "relation": "says", "object": "moo"}
```

## Rules

A rule is a sentence of triples with `{variables}`, the same braces as
slots. Teach it with the `rule` learner:

```json
{"rule": "{x} is {z} if {x} is {y} and {y} is {z}"}
{"rule": "{x} {r} {z} if {x} is {y} and {y} {r} {z}"}
```

The second says a thing does what its kind does; a relation can be a
variable too. Each triple in a rule is its first word, its last word and
the relation between them, so a term in a rule is one word or a variable.

## Proofs

To answer, Nagi chains backward. To show a triple it tries a matching fact,
or a rule whose conclusion matches, then shows the rule's conditions in
turn. Facts and rules are both tried newest first, so a later lesson
refines an earlier one.

What Nagi can't show is not true, and a relation starting with `not` says
so: `cat | not is | big` holds unless `cat is big` can be shown. Where not
knowing isn't knowing not, say what is not so as a fact like any other
(`cat | denied is | big`) and ask with `reason.ask(slot.thing, "is",
slot.kind, "denied is")`, which can answer that it doesn't know.

A goal that needs itself is a loop and fails, but a goal with unknowns may
recur once: showing "something eats the dog" may need "the dog likes the
tiger", which needs someone else who eats the dog.

A proof is thought out loud:

```console
$ uv run nagi respond --think is a whale an animal
<think>They ask whether a thing is a kind of thing. Check what I know about its kind.</think>
<think>whale is mammal</think>
<think>mammal is animal</think>
<think>so whale is animal</think>
Yes.
```

A proof gives up after 8 rules in a row or 20,000 facts and rules tried.
Rules that call each other freely can use that up before reaching the
simple answer, so write them with the search in mind, as in Prolog. The
bAbI notes in [Benchmarks](bench.md) show an example.

## The `reason` module

Responses ask and tell through `reason`, usually with slots:

| Call | Does |
|---|---|
| `reason.check(subject, relation, object)` | `"yes"` if it can be shown, else `"no"` |
| `reason.ask(subject, relation, object, opposite)` | `"yes"` if it can be shown, `"no"` if the opposite can, else `"I don't know"` |
| `reason.what(subject, relation)` | the object it can show, newest first |
| `reason.which(relation, object)` | the subject it can show, newest first |
| `reason.each(relation, object)` | every such subject, as `"milk and apple"`, or `"nothing"` |
| `reason.count(relation, object)` | how many, as a number: `"2"` |
| `reason.tell(subject, relation, object)` | knows a new fact |
| `reason.update(subject, relation, object)` | the same, replacing what was known of the subject's relation |
| `reason.forget(subject, relation, object)` | no longer knows the fact |
| `reason.rule(subject, relation, object, ...)` | knows a rule: the conclusion's triple, then each condition's |

For example, simplified from the bAbI lesson (`bench/babi.jsonl`):

```json
{"prompt": "{person} went to the {place}.", "completion": {"code": "reason.update(slot.person, \"is in\", slot.place)"}}
{"prompt": "where is {person}?", "completion": {"code": "speech.answer(reason.what(slot.person, \"is in\"))"}}
```

Rules can be told in conversation too. Taught `"all {kind} things are
{other}."` with `reason.rule("{x}", "is", slot.other, "{x}", "is",
slot.kind)`, Nagi hears "All zorby things are blippy." and reasons with it.
Facts and rules told in conversation are kept in memory like any other.
