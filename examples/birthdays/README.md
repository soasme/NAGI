# nagi-birthdays

Teach Nagi your family's birthdays from your own data, and ask about them.
A worked example of hooking **data and code into learning**, started with
`nagi new birthdays`.

| File | What it shows |
|---|---|
| `family.jsonl` | your data, in whatever shape suits it: `{"person": "Mei", "birthday": "3 May"}` |
| `src/nagi_birthdays/curriculum/t0/0-how-to-learn-birthdays.jsonl` | a **learner** for that shape: which records it reads and what it does with them |
| `src/nagi_birthdays/learning.py` | a **learning module** the learner calls (`birthdays.remember`), registered under `nagi.learning` |
| `src/nagi_birthdays/__init__.py` | a **response module** (`birthdays.when`) that answers from what was learned |
| `src/nagi_birthdays/curriculum/t0/birthdays.sft.jsonl` | teaching the question, whose untaught words name the person |

Learners can call only learning modules, and responses only response
modules. They meet in state: `lesson.state` when learning is `turn.state`
when responding.

```console
$ uv run nagi learn nagi birthdays examples/birthdays/family.jsonl
$ uv run nagi respond "when is Mei's birthday?"
Mei's birthday is 3 May.
```
