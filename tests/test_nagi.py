import json
from datetime import datetime

import pytest

from nagi import main, plugins
from nagi.plugins import curriculum, evals
from nagi.brain import Brain
from nagi.code import Program, Turn
from nagi.evals import evaluate
from nagi.generate import CONFUSED
from nagi.intent import Intent, capture
from nagi.tokens import encode, tokenize, train

MORNING = datetime(2026, 1, 1, 9)
HELLO = {"think": "They greet me.", "code": "speech.say(greeting.time_of_day())"}
FIXED = {"code": 'speech.say("Hello!")'}


def jsonl(*records) -> str:
    return "\n".join(json.dumps(r) for r in records)


def newborn() -> Brain:
    """A brain that has had only its first lesson: how to learn."""
    brain = Brain()
    brain.learn(curriculum()[0].read_text())
    return brain


def greeter() -> Brain:
    brain = Brain()
    for asset in curriculum():
        brain.learn(asset.read_text())
    return brain


# token in


def test_tokens_are_learned_byte_pairs():
    ranks = train(["hello", "hello there", "help"])
    assert encode(" hello", ranks) == [" hello"]
    assert encode(" helps", ranks) == [" help", "s"]
    assert encode(" xyz", ranks) == [" ", "x", "y", "z"]
    assert tokenize("Hellooo, there!", ranks) == [[" hello"], [" there"]]


# intent capture


def test_capture_finds_every_fitting_intent():
    ranks = train(["hi", "bye"])
    intents = {"greeting": Intent([tokenize("hi", ranks)]), "farewell": Intent([tokenize("bye", ranks)])}
    assert capture(intents, tokenize("bye", ranks)).keys() == {"farewell"}
    assert capture(intents, tokenize("what", ranks)) == {}


# code mode


def test_program_calls_nagi_modules():
    turn = Turn("hi", MORNING)
    Program("speech.say(greeting.time_of_day())\nspeech.say('Nice to see you.')")(turn)
    assert turn.said == ["Good morning!", "Nice to see you."]


@pytest.mark.parametrize(
    "code",
    [
        "print('hi')",  # builtins
        "speech.shout('hi')",  # not exported
        "nowhere.say('hi')",  # no such module
        "speech.__dict__",  # attributes
        "x = speech.say('hi')",  # statements other than calls
        "speech.say(text='hi')",  # keywords
        "speech.say(None)",
    ],
)
def test_program_rejects_anything_else(code):
    with pytest.raises(ValueError):
        Program(code)


# plugins


class Point:
    def __init__(self, name, value, package):
        self.name, self.value, self.dist = name, value, type("Dist", (), {"name": package})


def test_core_registers_like_any_plugin():
    assert {"greeting", "learn", "speech"} <= plugins.modules().keys()
    assert plugins.curricula()["nagi"] == "nagi.assets"


def test_two_packages_cannot_register_one_name(monkeypatch):
    points = [Point("todo", "a.todo", "nagi-a"), Point("todo", "b.todo", "nagi-b")]
    monkeypatch.setattr(plugins, "entry_points", lambda group: points)
    with pytest.raises(ValueError, match="nagi-a and nagi-b"):
        plugins.registry("nagi.modules")


def test_unknown_curriculum_names_the_installed_ones():
    with pytest.raises(ValueError, match="installed: .*nagi"):
        curriculum("nope")


def test_cli_reports_missing_files(tmp_path):
    with pytest.raises(SystemExit) as exit:
        main(["--memory", str(tmp_path / "memory.json"), "learn", str(tmp_path / "missing.jsonl")])
    assert exit.value.code == 1


# learning


def test_sft_teaches_a_response():
    brain = newborn()
    assert brain.learn(jsonl({"prompt": "hi", "completion": HELLO})) == 1
    turn = brain.respond("hi", MORNING)
    assert turn.thoughts == ["They greet me."]
    assert turn.said == ["Good morning!"]


def test_dpo_prefers_chosen():
    brain = newborn()
    brain.learn(jsonl({"prompt": "hi", "completion": FIXED}, {"prompt": "hi", "completion": HELLO}))
    brain.learn(jsonl({"prompt": "hi", "chosen": HELLO, "rejected": FIXED}))
    assert brain.respond("hi", MORNING).said == ["Good morning!"]


def test_rlhf_reward_moves_preference():
    brain = newborn()
    brain.learn(jsonl({"prompt": "hi", "completion": FIXED}, {"prompt": "hi", "completion": HELLO}))
    brain.learn(jsonl({"prompt": "hi", "completion": HELLO, "reward": -1}))
    assert brain.respond("hi", MORNING).said == ["Hello!"]
    brain.learn(jsonl({"prompt": "hi", "completion": FIXED, "reward": -1}))
    assert brain.respond("hi", MORNING).said == [CONFUSED]


def test_repetition_reinforces():
    brain = newborn()
    record = jsonl({"prompt": "hi", "chosen": HELLO, "rejected": FIXED})
    brain.learn(record)
    brain.learn(record)
    [hello] = [r for r in brain.memory["responses"].values() if r["code"] == HELLO["code"]]
    assert hello["prompts"] == {"hi": 2}
    assert hello["value"] == 2


@pytest.mark.parametrize(
    "line",
    [
        '{"prompt": "hi"}',
        '{"prompt": "hi", "completion": "Hello!"}',
        '{"prompt": "hi", "completion": {"think": "no code"}}',
        '{"prompt": "hi", "completion": {"code": "os.system(\'ls\')"}}',
    ],
)
def test_learn_rejects_malformed(line):
    with pytest.raises(ValueError):
        newborn().learn(line)


# learning how to learn


def test_newborn_knows_only_how_to_learn_learners():
    with pytest.raises(ValueError, match="no learner"):
        Brain().learn(jsonl({"prompt": "hi", "completion": HELLO}))


def test_a_new_way_of_learning_is_taught_not_coded():
    brain = newborn()
    brain.learn(jsonl(
        {"learner": "faq", "shape": {"q": "text", "a": "completion"}, "code": "learn.prompt(record.q, record.a, 1)"},
        {"q": "hi", "a": HELLO},
    ))
    assert brain.respond("hi", MORNING).said == ["Good morning!"]


def test_reteaching_a_learner_changes_how_nagi_learns():
    brain = newborn()
    eager = "learn.prompt(record.prompt, record.completion, 1)\nlearn.value(record.completion, 1)"
    brain.learn(jsonl({"learner": "sft", "shape": {"prompt": "text", "completion": "completion"}, "code": eager}))
    brain.learn(jsonl({"prompt": "hi", "completion": HELLO}))
    assert list(brain.learners) == ["dpo", "rlhf", "sft"]
    assert [r["value"] for r in brain.memory["responses"].values()] == [1]


@pytest.mark.parametrize(
    "learner",
    [
        {"learner": "x", "shape": {"q": "text"}, "code": "speech.say(record.q)"},  # learners only learn
        {"learner": "x", "shape": {"q": "words"}, "code": "learn.value(record.q, 1)"},  # unknown type
        {"learner": "x", "shape": {}, "code": "learn.value(record, 1)"},  # empty shape
        {"learner": "x", "shape": {"q": "text"}},  # no code
    ],
)
def test_bad_learners_are_rejected(learner):
    with pytest.raises(ValueError):
        newborn().learn(jsonl(learner))


@pytest.mark.parametrize("code", ["learn.value(record, 1)", "speech.say(record.prompt)"])
def test_responses_cannot_learn_or_read_records(code):
    with pytest.raises(ValueError):
        Program(code)


# all together


def test_newborn_is_confused():
    assert Brain().respond("hello").said == [CONFUSED]


def test_curriculum_passes_its_evals():
    brain = greeter()
    for eval_set in evals():
        report = evaluate(brain, eval_set.read_text())
        assert report.failed == [], eval_set.name


def test_eval_reports_false_accepts_and_rejects():
    report = evaluate(
        greeter(),
        jsonl(
            {"prompt": "hello", "expect": "speech.say(greeting.hello())"},
            {"prompt": "hello", "expect": "speech.say(greeting.echo())"},
            {"prompt": "hello", "expect": None},
            {"prompt": "what is the capital of france", "expect": "speech.say(greeting.hello())"},
            {"prompt": "what is the capital of france", "expect": None},
        ),
    )
    assert (report.passed, report.total, report.unknowns) == (2, 5, 2)
    assert [c.prompt for c in report.false_accepts] == ["hello"]
    assert [c.prompt for c in report.false_rejects] == ["what is the capital of france"]
    assert report.false_accept_rate == 0.5


def test_eval_does_not_teach():
    brain = greeter()
    before = json.dumps(brain.memory)
    evaluate(brain, jsonl({"prompt": "goodbye", "expect": None}))
    assert json.dumps(brain.memory) == before


def test_residue_is_what_was_not_part_of_the_intent():
    brain = greeter()
    assert brain.respond("Hey, Nagi!").residue == ["Nagi"]
    assert brain.respond("hello").residue == []
    assert brain.respond("what time is it?").residue == ["what", "time", "is", "it"]


def test_state_is_kept_between_turns():
    brain = greeter()
    turn = brain.respond("hello")
    turn.state.setdefault("count", 0)
    turn.state["count"] += 1
    assert brain.respond("hello").state == {"count": 1}
    assert brain.memory["state"] == {"count": 1}


def test_replies_fit_what_was_heard():
    brain = greeter()
    assert brain.respond("good evening", MORNING).said == ["Good morning!"]
    assert brain.respond("hola nagi!").said == ["Hola nagi!"]
    assert len(brain.respond("how are you").said) == 2


def test_replies_vary():
    brain = greeter()
    assert len({brain.respond("hello").said[0] for _ in range(50)}) > 1


@pytest.mark.parametrize(
    "said",
    ["what is the capital of france", "this", "you", "help", "nice weather", "see you later", "goodbye", "what time is it", ""],
)
def test_ignores_what_it_was_not_taught(said):
    assert greeter().respond(said).said == [CONFUSED]


def test_memory_round_trips(tmp_path):
    memory = tmp_path / "memory.json"
    brain = greeter()
    brain.save(memory)
    assert Brain.load(memory).memory == brain.memory


def test_cli_eval_fails_below_threshold(tmp_path, capsys):
    with pytest.raises(SystemExit) as exit:
        main(["--memory", str(tmp_path / "memory.json"), "eval"])
    assert exit.value.code == 1


def test_cli_remembers_across_runs(tmp_path, capsys):
    memory = tmp_path / "memory.json"
    main(["--memory", str(memory), "respond", "hi"])
    assert capsys.readouterr().out == f"{CONFUSED}\n"

    main(["--memory", str(memory), "learn"])
    assert "records from greeting.sft.jsonl" in capsys.readouterr().out

    main(["--memory", str(memory), "eval"])
    assert "accuracy 100.0%" in capsys.readouterr().out

    main(["--memory", str(memory), "respond", "--think", "good", "morning"])
    think, said = capsys.readouterr().out.splitlines()
    assert think.startswith("<think>")
    assert said in ("Good morning!", "Good afternoon!", "Good evening!", "Hello!")
