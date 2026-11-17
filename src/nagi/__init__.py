"""Nagi is Not Artificial General Intelligence."""

import argparse
from pathlib import Path

from nagi import plugins
from nagi.brain import Brain
from nagi.code import Turn
from nagi.evals import Report, evaluate

MEMORY = Path.home() / ".nagi" / "memory.json"


def sources(names: list[str], pick) -> list:
    """Files for each name: an installed curriculum's (via pick), or a path."""
    found = []
    for name in names:
        found += pick(name) if name in plugins.curricula() else [Path(name)]
    return found


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
    learn = commands.add_parser("learn", help="learn curricula or asset files (default: nagi)")
    learn.add_argument("sources", nargs="*", default=["nagi"], metavar="CURRICULUM_OR_FILE")
    respond = commands.add_parser("respond", help="respond to what you say")
    respond.add_argument("words", nargs="+")
    check = commands.add_parser("eval", help="check curricula or eval files (default: nagi)")
    check.add_argument("sources", nargs="*", default=["nagi"], metavar="CURRICULUM_OR_FILE")
    check.add_argument("--min-accuracy", type=float, default=0.95)
    check.add_argument("--max-false-accepts", type=float, default=0.02)
    chat = commands.add_parser("chat", help="talk until EOF")
    commands.add_parser("plugins", help="list installed modules and curricula")
    for command in (respond, chat):
        command.add_argument("--think", action="store_true", help="show the chain of thought")
    args = parser.parse_args(argv)

    try:
        if args.command == "plugins":
            for kind, registered in (("module", plugins.modules()), ("curriculum", plugins.curricula())):
                for name, path in sorted(registered.items()):
                    print(f"{kind:10} {name:12} {path}")
            return
        brain = Brain.load(args.memory)
        if args.command == "learn":
            for asset in sources(args.sources, plugins.curriculum):
                print(f"learned {brain.learn(asset.read_text())} records from {asset.name}")
            brain.save(args.memory)
        elif args.command == "eval":
            results = [(e.name, evaluate(brain, e.read_text())) for e in sources(args.sources, plugins.evals)]
            if not report(results, args.min_accuracy, args.max_false_accepts):
                parser.exit(1)
        elif args.command == "respond":
            show(brain.respond(" ".join(args.words)), args.think)
        else:
            while True:
                show(brain.respond(input("> ")), args.think)
    except (EOFError, KeyboardInterrupt):
        print()
    except (ValueError, OSError) as error:
        parser.exit(1, f"nagi: {error}\n")
