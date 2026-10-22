import sys
from collections.abc import Sequence
from typing import TextIO

from junction_sim.cli.commands import handle_benchmark, handle_run
from junction_sim.cli.parser import create_parser
from junction_sim.exceptions import JunctionSimError


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = create_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0

    if not args.command:
        parser.print_help(stdout)
        return 0

    try:
        if args.command == "run":
            return handle_run(args, stdout=stdout)
        return handle_benchmark(args, stdout=stdout)
    except JunctionSimError as exc:
        stderr.write(f"Error: {exc}\n")
        return 1
