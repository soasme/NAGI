"""Nagi is Not Artificial General Intelligence."""

import argparse
from importlib.resources import files
from pathlib import Path

from nagi.brain import Brain
from nagi.code import Turn

ASSETS = files("nagi") / "assets"
MEMORY = Path.home() / ".nagi" / "memory.json"


def curriculum():
    """Bundled teaching assets, tier by tier: t0, t1, ..."""
    tiers = sorted(ASSETS.iterdir(), key=lambda t: int(t.name[1:]))
    return [a for tier in tiers for a in sorted(tier.iterdir(), key=lambda a: a.name)]


def show(turn: Turn, think: bool) -> None:
    if think:
        for thought in turn.thoughts:
            print(f"<think>{thought}</think>")
    print(" ".join(turn.said))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="nagi", description=__doc__)
    parser.add_argument("--memory", type=Path, default=MEMORY, help=f"default: {MEMORY}")
    commands = parser.add_subparsers(dest="command", required=True)
    learn = commands.add_parser("learn", help="learn from teaching assets (default: bundled curriculum)")
    learn.add_argument("assets", nargs="*", type=Path)
    respond = commands.add_parser("respond", help="respond to what you say")
    respond.add_argument("words", nargs="+")
    chat = commands.add_parser("chat", help="talk until EOF")
    for command in (respond, chat):
        command.add_argument("--think", action="store_true", help="show the chain of thought")
    args = parser.parse_args(argv)

    brain = Brain.load(args.memory)
    if args.command == "learn":
        for asset in args.assets or curriculum():
            print(f"learned {brain.learn(asset.read_text())} records from {asset.name}")
        brain.save(args.memory)
    elif args.command == "respond":
        show(brain.respond(" ".join(args.words)), args.think)
    else:
        try:
            while True:
                show(brain.respond(input("> ")), args.think)
        except (EOFError, KeyboardInterrupt):
            print()
