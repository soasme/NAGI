"""Nagi is Not Artificial General Intelligence."""

import argparse
from importlib.resources import files
from pathlib import Path

from nagi.brain import Brain
from nagi.code import Turn
from nagi.evals import Report, evaluate

ASSETS = files("nagi") / "assets"
MEMORY = Path.home() / ".nagi" / "memory.json"


def bundled():
    """Bundled files, tier by tier: t0, t1, ..."""
    tiers = sorted(ASSETS.iterdir(), key=lambda t: int(t.name[1:]))
    return [a for tier in tiers for a in sorted(tier.iterdir(), key=lambda a: a.name)]


def curriculum():
    """Bundled teaching assets, in the order they are taught."""
    return [a for a in bundled() if not a.name.endswith(".eval.jsonl")]


def evals():
    """Bundled eval sets, never taught."""
    return [a for a in bundled() if a.name.endswith(".eval.jsonl")]


def report(results: list[tuple[str, Report]], min_accuracy: float, max_false_accepts: float) -> bool:
    """Print each eval's failures and the totals; whether the totals pass."""
    total = Report()
    for name, result in results:
        print(f"{name}: {result.passed}/{result.total}")
        for case in result.failed:
            print(f"  ✗ {case.prompt!r}: expected {case.expect or 'nothing'}, got {case.got or 'nothing'}")
        total += result
    print(
        f"accuracy {total.accuracy:.1%}, false accepts {total.false_accept_rate:.1%}, "
        f"false rejects {len(total.false_rejects)}"
    )
    return total.accuracy >= min_accuracy and total.false_accept_rate <= max_false_accepts


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
    check = commands.add_parser("eval", help="check what Nagi would do (default: bundled evals)")
    check.add_argument("evals", nargs="*", type=Path)
    check.add_argument("--min-accuracy", type=float, default=0.95)
    check.add_argument("--max-false-accepts", type=float, default=0.02)
    chat = commands.add_parser("chat", help="talk until EOF")
    for command in (respond, chat):
        command.add_argument("--think", action="store_true", help="show the chain of thought")
    args = parser.parse_args(argv)

    try:
        brain = Brain.load(args.memory)
        if args.command == "learn":
            for asset in args.assets or curriculum():
                print(f"learned {brain.learn(asset.read_text())} records from {asset.name}")
            brain.save(args.memory)
        elif args.command == "eval":
            results = [(e.name, evaluate(brain, e.read_text())) for e in args.evals or evals()]
            if not report(results, args.min_accuracy, args.max_false_accepts):
                parser.exit(1)
        elif args.command == "respond":
            show(brain.respond(" ".join(args.words)), args.think)
        else:
            while True:
                show(brain.respond(input("> ")), args.think)
    except (EOFError, KeyboardInterrupt):
        print()
    except ValueError as error:
        parser.exit(1, f"nagi: {error}\n")
