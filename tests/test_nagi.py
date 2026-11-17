import json
from datetime import datetime

import pytest

from nagi import curriculum, main
from nagi.brain import Brain
from nagi.code import Program, Turn
from nagi.generate import CONFUSED
from nagi.intent import Intent, capture
from nagi.tokens import encode, tokenize, train

MORNING = datetime(2026, 1, 1, 9)
HELLO = {"think": "They greet me.", "code": "speech.say(greeting.hello())"}
FIXED = {"code": 'speech.say("Hello!")'}


def jsonl(*records) -> str:
    return "\n".join(json.dumps(r) for r in records)


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
    Program("speech.say(greeting.hello())\nspeech.say('Nice to see you.')")(turn)
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


# learning


def test_sft_teaches_a_response():
    brain = Brain()
    assert brain.learn(jsonl({"prompt": "hi", "completion": HELLO})) == 1
    turn = brain.respond("hi", MORNING)
    assert turn.thoughts == ["They greet me."]
    assert turn.said == ["Good morning!"]


def test_dpo_prefers_chosen():
    brain = Brain()
    brain.learn(jsonl({"prompt": "hi", "completion": FIXED}, {"prompt": "hi", "completion": HELLO}))
    brain.learn(jsonl({"prompt": "hi", "chosen": HELLO, "rejected": FIXED}))
    assert brain.respond("hi", MORNING).said == ["Good morning!"]


def test_rlhf_reward_moves_preference():
    brain = Brain()
    brain.learn(jsonl({"prompt": "hi", "completion": FIXED}, {"prompt": "hi", "completion": HELLO}))
    brain.learn(jsonl({"prompt": "hi", "completion": HELLO, "reward": -1}))
    assert brain.respond("hi", MORNING).said == ["Hello!"]
    brain.learn(jsonl({"prompt": "hi", "completion": FIXED, "reward": -1}))
    assert brain.respond("hi", MORNING).said == [CONFUSED]


def test_repetition_reinforces_without_duplicating_prompts():
    brain = Brain()
    record = jsonl({"prompt": "hi", "chosen": HELLO, "rejected": FIXED})
    brain.learn(record)
    brain.learn(record)
    [hello] = [r for r in brain.memory["responses"].values() if r["code"] == HELLO["code"]]
    assert hello["prompts"] == ["hi"]
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
        Brain().learn(line)


# all together


def test_newborn_is_confused():
    assert Brain().respond("hello").said == [CONFUSED]


@pytest.mark.parametrize(
    "said",
    [
        "hello",
        "Hi!",
        "hiii",
        "Good morning!",
        "hey nagi",
        "hey there, nagi",
        "hi nagi how are you",
        "Howdy partner!",
        "sup dude",
        "what's up?",
        "how r u",
        "Bonjour!",
        "你好",
    ],
)
def test_greets_back_by_time_of_day(said):
    assert greeter().respond(said, MORNING).said == ["Good morning!"]


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


def test_cli_remembers_across_runs(tmp_path, capsys):
    memory = tmp_path / "memory.json"
    main(["--memory", str(memory), "respond", "hi"])
    assert capsys.readouterr().out == f"{CONFUSED}\n"

    main(["--memory", str(memory), "learn"])
    assert "records from greeting.sft.jsonl" in capsys.readouterr().out

    main(["--memory", str(memory), "respond", "--think", "good", "morning"])
    think, said = capsys.readouterr().out.splitlines()
    assert think.startswith("<think>")
    assert said in ("Good morning!", "Good afternoon!", "Good evening!", "Hello!")
