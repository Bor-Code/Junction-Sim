import argparse

from junction_sim import __version__
from junction_sim.presets import list_presets


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
    run_cfg_group = run_parser.add_mutually_exclusive_group(required=True)
    run_cfg_group.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to scenario JSON configuration file",
    )
    run_cfg_group.add_argument(
        "--preset",
        "-p",
        type=str,
        choices=list_presets(),
        help="Name of built-in scenario preset to execute",
    )
    run_parser.add_argument(
        "--controller",
        choices=["fixed-time", "actuated", "max-pressure", "dual-ring", "q-learning"],
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
        "--out-html",
        type=str,
        default=None,
        help="Destination path to export interactive HTML visualizer",
    )
    run_parser.add_argument(
        "--out-html-3d",
        type=str,
        default=None,
        help="Destination path to export photorealistic 3D WebGL visualizer",
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
    bench_cfg_group = bench_parser.add_mutually_exclusive_group(required=True)
    bench_cfg_group.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to scenario JSON configuration file",
    )
    bench_cfg_group.add_argument(
        "--preset",
        "-p",
        type=str,
        choices=list_presets(),
        help="Name of built-in scenario preset to benchmark",
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
        "--num-seeds",
        type=int,
        default=None,
        help="Execute multi-seed evaluation across N consecutive seeds",
    )
    bench_parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated list of RNG seeds for multi-seed evaluation",
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

    presets_parser = subparsers.add_parser(
        "presets",
        help="Inspect and export built-in scenario presets",
    )
    presets_subparsers = presets_parser.add_subparsers(
        dest="preset_action",
        help="Preset action",
    )
    presets_subparsers.add_parser("list", help="List all available scenario presets")
    export_parser = presets_subparsers.add_parser(
        "export", help="Export a scenario preset to JSON file"
    )
    export_parser.add_argument(
        "--preset",
        "-p",
        required=True,
        choices=list_presets(),
        help="Name of scenario preset to export",
    )
    export_parser.add_argument(
        "--out",
        "-o",
        required=True,
        type=str,
        help="Target JSON file path",
    )

    vis_parser = subparsers.add_parser(
        "visualize",
        help="Run simulation and export or open interactive HTML visualizer",
    )
    vis_cfg_group = vis_parser.add_mutually_exclusive_group(required=True)
    vis_cfg_group.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to scenario JSON configuration file",
    )
    vis_cfg_group.add_argument(
        "--preset",
        "-p",
        type=str,
        choices=list_presets(),
        help="Name of built-in scenario preset to visualize",
    )
    vis_parser.add_argument(
        "--controller",
        choices=["fixed-time", "actuated", "max-pressure", "dual-ring", "q-learning"],
        default="fixed-time",
        help="Signal control policy to execute (default: fixed-time)",
    )
    vis_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        help="Override simulation duration in seconds",
    )
    vis_parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=None,
        help="Override random number generator seed",
    )
    vis_parser.add_argument(
        "--out-html",
        "-o",
        type=str,
        default="visualizer.html",
        help="Target HTML output path (default: visualizer.html)",
    )
    vis_parser.add_argument(
        "--3d",
        dest="three_d",
        action="store_true",
        help="Generate photorealistic 3D WebGL visualizer with Three.js",
    )
    vis_parser.add_argument(
        "--mode",
        choices=["2d", "3d"],
        default="3d",
        help=(
            "Visualization rendering mode: 2d (canvas) or 3d (photorealistic WebGL) "
            "(default: 3d)"
        ),
    )
    vis_parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open generated visualizer in web browser",
    )

    train_parser = subparsers.add_parser(
        "train", help="Train a Q-learning reinforcement learning controller"
    )
    train_cfg_group = train_parser.add_mutually_exclusive_group(required=True)
    train_cfg_group.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to scenario JSON configuration file",
    )
    train_cfg_group.add_argument(
        "--preset",
        "-p",
        type=str,
        choices=list_presets(),
        help="Name of built-in scenario preset to train on",
    )
    train_parser.add_argument(
        "--episodes",
        "-e",
        type=int,
        default=10,
        help="Number of training episodes (default: 10)",
    )
    train_parser.add_argument(
        "--reward-type",
        choices=["queue_penalty", "delay_penalty", "throughput"],
        default="queue_penalty",
        help="Reward function formulation (default: queue_penalty)",
    )
    train_parser.add_argument(
        "--out-model",
        "-o",
        type=str,
        default=None,
        help="Destination path to save trained Q-table JSON policy",
    )

    return parser
