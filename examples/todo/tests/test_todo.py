from datetime import datetime

import pytest

from nagi.brain import Brain
from nagi.evals import evaluate
from nagi.plugins import curriculum, evals


@pytest.fixture
def nagi() -> Brain:
    brain = Brain()
    for asset in curriculum("nagi") + curriculum("todo"):
        brain.learn(asset.read_text())
    return brain


def say(brain: Brain, text: str) -> str:
    return " ".join(brain.respond(text, datetime(2026, 1, 1, 9)).said)


def test_passes_its_evals(nagi):
    for eval_set in evals("todo"):
        assert evaluate(nagi, eval_set.read_text()).failed == [], eval_set.name


def test_core_still_passes_its_evals(nagi):
    for eval_set in evals("nagi"):
        assert evaluate(nagi, eval_set.read_text()).failed == [], eval_set.name


def test_the_item_is_what_was_not_taught(nagi):
    assert say(nagi, "add oat milk to my list") == "Added oat milk."
    assert say(nagi, "Add bread to the list, please") == "Added bread."
    assert say(nagi, "remember to call Mei") == "Added call Mei."
    assert say(nagi, "what's on my list?") == "On your list: oat milk, bread and call Mei."


def test_cross_off_and_clear(nagi):
    say(nagi, "add eggs to my list")
    say(nagi, "add tea to my list")
    assert say(nagi, "cross Eggs off my list") == "Crossed off eggs."
    assert say(nagi, "cross jam off my list") == "jam isn't on your list."
    assert say(nagi, "clear my list") == "Cleared 1 item."
    assert say(nagi, "show my list") == "Your list is empty."


def test_asks_when_there_is_nothing_to_add(nagi):
    assert say(nagi, "add to my list") == "What should I add?"
