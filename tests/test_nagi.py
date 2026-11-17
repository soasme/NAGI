import json
from datetime import datetime

import pytest

from nagi import main, plugins, scaffold
from nagi.plugins import curriculum, evals
from nagi.brain import Brain
from nagi.code import Program, Turn
from nagi.evals import evaluate
from nagi.generate import CONFUSED
from nagi.intent import Intent, capture
from nagi.knowledge import Knowledge, triple
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
    assert {"greeting", "speech"} <= plugins.modules().keys()
    assert "learn" in plugins.learning()
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


def test_new_plugin_learns_and_passes_its_evals(tmp_path, monkeypatch):
    made = scaffold.create("weather", tmp_path / "nagi-weather")
    assert {p.name for p in made} >= {"pyproject.toml", "__init__.py", "weather.sft.jsonl", "weather.eval.jsonl"}
    monkeypatch.syspath_prepend(str(tmp_path / "nagi-weather" / "src"))
    monkeypatch.setattr(plugins, "modules", lambda: {**plugins.registry("nagi.modules"), "weather": "nagi_weather"})
    monkeypatch.setattr(
        plugins, "curricula", lambda: {**plugins.registry("nagi.curricula"), "weather": "nagi_weather.curriculum"}
    )
    brain = greeter()
    for asset in curriculum("weather"):
        brain.learn(asset.read_text())
    assert evaluate(brain, evals("weather")[0].read_text()).failed == []
    assert brain.respond("try weather").said == ["Hello from weather!"]


@pytest.mark.parametrize("name", ["Weather", "my-plugin", "1st", ""])
def test_new_plugin_needs_a_python_name(tmp_path, name):
    with pytest.raises(ValueError):
        scaffold.create(name, tmp_path / "x")


def test_new_plugin_never_overwrites(tmp_path):
    with pytest.raises(ValueError, match="already exists"):
        scaffold.create("weather", tmp_path)


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
    assert list(brain.learners) == ["dpo", "rlhf", "fact", "rule", "sft"]
    assert [r["value"] for r in brain.memory["responses"].values()] == [1]


@pytest.mark.parametrize(
    "learner",
    [
        {"learner": "x", "shape": {"q": "text"}, "code": "speech.say(record.q)"},  # learners only learn
        {"learner": "x", "shape": {"q": "text"}, "code": "birthdays.when(record.q)"},  # not a learning module
        {"learner": "x", "shape": {"q": "words"}, "code": "learn.value(record.q, 1)"},  # unknown type
        {"learner": "x", "shape": {}, "code": "learn.value(record, 1)"},  # empty shape
        {"learner": "x", "shape": {"q": "text"}},  # no code
    ],
)
def test_bad_learners_are_rejected(learner):
    with pytest.raises(ValueError):
        newborn().learn(jsonl(learner))


@pytest.mark.parametrize(
    "code", ["learn.value(record, 1)", "speech.say(record.prompt)", "birthdays.remember('Mei', '3 May')"]
)
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


def test_slots_hold_the_words_heard_in_their_place():
    brain = greeter()
    asks = {"code": "speech.say(slot.thing)\nspeech.say(slot.kind)"}
    brain.learn(jsonl({"prompt": "is a {thing} a {kind}?", "completion": asks}))
    turn = brain.respond("Is a polar bear a mammal?")
    assert turn.slots == {"thing": "polar bear", "kind": "mammal"}
    assert turn.said == ["polar bear", "mammal"]
    assert turn.residue == []
    assert brain.respond("hello").slots == {}


def test_a_slot_does_not_make_anything_fit():
    brain = greeter()
    brain.learn(jsonl({"prompt": "is a {thing} a {kind}?", "completion": FIXED}))
    for text in ("what is the capital of france", "is it raining today", "i need to start a timer"):
        assert brain.understand(text)[0] is None, text


def test_a_response_reading_a_slot_needs_it_heard():
    brain = greeter()
    brain.learn(jsonl({"prompt": "what is a {thing}?", "completion": {"code": "speech.say(slot.thing)"}}))
    assert brain.respond("what is a shark?").said == ["shark"]
    assert brain.understand("what time is it")[0] is None


def test_a_slot_is_one_token():
    assert tokenize("is a {thing}?", train(["is a cat"])) == [[" is"], [" a"], ["{thing}"]]


# reasoning


def zoo() -> Knowledge:
    knowledge = Knowledge([], [])
    knowledge.tell("a whale", "is a", "mammal")
    knowledge.tell("a mammal", "is an", "animal")
    knowledge.tell("a mammal", "breathes", "air")
    knowledge.rule("{x} is {z} if {x} is {y} and {y} is {z}")
    knowledge.rule("{x} breathes {z} if {x} is {y} and {y} breathes {z}")
    return knowledge


def test_facts_are_compared_as_plain_words():
    assert zoo().facts[0] == ["whale", "is", "mammal"]
    assert triple("{x} is at the {y}") == ("{x}", "is at", "{y}")


def test_a_proof_is_the_facts_used_and_what_follows():
    proofs = zoo().prove(("whale", "breathes", "{what}"))
    bound, steps = next(proofs)
    assert bound["{what}"] == "air"
    assert steps == ["whale is mammal", "mammal breathes air", "so whale breathes air"]


def test_what_cannot_be_shown_is_not_true():
    assert list(zoo().prove(("whale", "is", "fish"))) == []


def test_rules_that_lead_back_to_themselves_end():
    knowledge = zoo()
    knowledge.tell("animal", "is", "mammal")
    assert next(knowledge.prove(("whale", "is", "animal")))[1][-1] == "so whale is animal"
    assert list(knowledge.prove(("whale", "is", "fish"))) == []


def test_update_replaces_what_was_known():
    knowledge = Knowledge([], [])
    knowledge.update("Mary", "is in", "the kitchen")
    knowledge.update("Mary", "is in", "the garden")
    assert knowledge.facts == [["mary", "is in", "garden"]]


def test_a_rule_needs_a_condition():
    with pytest.raises(ValueError, match="if"):
        Knowledge([], []).rule("{x} is {y}")


def test_nagi_reasons_out_loud():
    brain = greeter()
    asks = {"code": 'speech.say(reason.check(slot.thing, "is", slot.kind))'}
    tells = {"code": 'reason.tell(slot.thing, "is", slot.kind)'}
    brain.learn(jsonl(
        {"rule": "{x} is {z} if {x} is {y} and {y} is {z}"},
        *({"prompt": f"is a {{thing}} {a} {{kind}}?", "completion": asks} for a in ("a", "an")),
        *({"prompt": f"a {{thing}} is {a} {{kind}}.", "completion": tells} for a in ("a", "an")),
    ))
    brain.respond("A zorb is a blip.")
    brain.respond("A blip is an orb.")
    turn = brain.respond("Is a zorb an orb?")
    assert turn.said == ["yes"]
    assert turn.thoughts == ["zorb is blip", "blip is orb", "so zorb is orb"]
    assert brain.respond("Is a zorb a fish?").said == ["no"]
    assert brain.memory["facts"][-2:] == [["zorb", "is", "blip"], ["blip", "is", "orb"]]


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
