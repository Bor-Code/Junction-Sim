import argparse

from junction_sim import __version__


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="junction-sim",
        description=(
            "A discrete-event traffic simulation and benchmarking CLI "
            "for signalized intersections."
        ),
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"junction-sim {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available simulation subcommands"
    )

    run_parser = subparsers.add_parser(
        "run", help="Run a single-controller traffic simulation"
    )
    run_parser.add_argument(
        "--config",
        "-c",
        required=True,
        type=str,
        help="Path to scenario JSON configuration file",
    )
    run_parser.add_argument(
        "--controller",
        choices=["fixed-time", "actuated", "max-pressure"],
        default="fixed-time",
        help="Signal control policy to execute (default: fixed-time)",
    )
    run_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        help="Override simulation duration in seconds",
    )
    run_parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=None,
        help="Override random number generator seed",
    )
    run_parser.add_argument(
        "--out-csv",
        type=str,
        default=None,
        help="Destination path to export step-by-step CSV time series",
    )
    run_parser.add_argument(
        "--out-json",
        type=str,
        default=None,
        help="Destination path to export detailed JSON results",
    )
    run_parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Render terminal ASCII dashboard for the final simulation step",
    )

    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Run comparative benchmark across multiple signal controllers",
    )
    bench_parser.add_argument(
        "--config",
        "-c",
        required=True,
        type=str,
        help="Path to scenario JSON configuration file",
    )
    bench_parser.add_argument(
        "--controllers",
        type=str,
        default="fixed-time,actuated,max-pressure",
        help=(
            "Comma-separated list of controllers to benchmark "
            "(default: fixed-time,actuated,max-pressure)"
        ),
    )
    bench_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        help="Override simulation duration in seconds",
    )
    bench_parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=None,
        help="Override random number generator seed",
    )
    bench_parser.add_argument(
        "--out-csv",
        type=str,
        default=None,
        help="Destination path to export benchmark summary CSV",
    )
    bench_parser.add_argument(
        "--out-json",
        type=str,
        default=None,
        help="Destination path to export benchmark summary JSON",
    )

    return parser
