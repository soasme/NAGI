# nagi-todo

A todo list for Nagi, and a worked example of extending it. It was started
with `nagi new todo`; everything here is plain data and one Python module.

| File | What it shows |
|---|---|
| `pyproject.toml` | registering a module (`todo`) and a curriculum (`todo`) with entry points |
| `src/nagi_todo/__init__.py` | a module: functions that take the turn and the item, and keep data in `turn.state` |
| `src/nagi_todo/curriculum/t0/todo.sft.jsonl` | teaching intents with SFT records whose completions call the module |
| `src/nagi_todo/curriculum/t0/todo.eval.jsonl` | checking them, including inputs that must stay unknown |
| `tests/test_todo.py` | testing what Nagi says, and that core's evals still pass alongside |

The item is a slot: taught `add {item} to my list` with the program
`speech.say(todo.add(slot.item))`, Nagi reads "add oat milk to my list" as
adding "oat milk". When a word that isn't part of the item ends up in it,
teach more prompts rather than writing code: "please" is taught (`add
{item} to my list please`), so "Add bread to the list, please" adds
"bread". Prompts too open to mean a todo, like `i need to {item}`, are left
out: real requests ("i need to start a timer") would fit them.

```console
$ uv run nagi learn nagi todo
$ uv run nagi eval todo
$ uv run nagi chat
> add oat milk to my list
Added oat milk.
> what's on my list?
On your list: oat milk.
```
