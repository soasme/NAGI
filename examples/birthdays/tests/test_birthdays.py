from pathlib import Path

import pytest

from nagi.brain import Brain
from nagi.evals import evaluate
from nagi.plugins import curriculum, evals

FAMILY = Path(__file__).parent.parent / "family.jsonl"


@pytest.fixture
def nagi() -> Brain:
    brain = Brain()
    for asset in curriculum("nagi") + curriculum("birthdays"):
        brain.learn(asset.read_text())
    brain.learn(FAMILY.read_text())
    return brain


def say(brain: Brain, text: str) -> str:
    return " ".join(brain.respond(text).said)


def test_passes_its_evals(nagi):
    for eval_set in evals("birthdays"):
        assert evaluate(nagi, eval_set.read_text()).failed == [], eval_set.name


def test_learns_birthdays_from_your_own_data(nagi):
    assert say(nagi, "when is Mei's birthday?") == "Mei's birthday is 3 May."
    assert say(nagi, "what day is sam's birthday") == "Sam's birthday is 29 February."


def test_new_data_keeps_training(nagi):
    nagi.learn('{"person": "Mei", "birthday": "4 May"}\n{"person": "Ada", "birthday": "10 December"}')
    assert say(nagi, "when is Mei's birthday?") == "Mei's birthday is 4 May."
    assert say(nagi, "when was Ada born") == "Ada's birthday is 10 December."


def test_says_what_it_does_not_know(nagi):
    assert say(nagi, "when is Bob's birthday") == "I don't know when Bob's birthday is yet."
