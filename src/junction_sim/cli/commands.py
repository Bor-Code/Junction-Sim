import argparse
import sys
from typing import TextIO

from junction_sim.benchmarks.harness import BenchmarkHarness
from junction_sim.config.loader import load_scenario_from_file
from junction_sim.controllers.actuated import ActuatedController
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.controllers.protocol import SignalController
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.engine.engine import SimulationEngine
from junction_sim.exceptions import ConfigurationError
from junction_sim.reporting.csv_reporter import (
    export_benchmark_to_csv,
    export_step_results_to_csv,
)
from junction_sim.reporting.json_reporter import (
    export_benchmark_to_json,
    export_step_results_to_json,
)
from junction_sim.visualization import render_step_dashboard


def instantiate_controller(
    name: str, signal_plan: SignalPlan, intersection: Intersection
) -> SignalController:
    if name == "fixed-time":
        return FixedTimeController(signal_plan=signal_plan)
    if name == "actuated":
        return ActuatedController(signal_plan=signal_plan, intersection=intersection)
    if name == "max-pressure":
        return MaxPressureController(signal_plan=signal_plan, intersection=intersection)
    raise ConfigurationError(
        f"unknown controller '{name}', expected one of: "
        "fixed-time, actuated, max-pressure"
    )


def handle_run(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    scenario = load_scenario_from_file(args.config)
    duration = (
        args.duration if args.duration is not None else scenario.simulation.duration
    )
    seed = args.seed if args.seed is not None else scenario.simulation.seed

    intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()
    controller = instantiate_controller(args.controller, signal_plan, intersection)

    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=signal_plan,
        demands=demands,
        controller=controller,
        step_size=sim_cfg.step_size,
        seed=seed,
    )

    results = engine.run(duration)

    total_arrivals = sum(len(r.arrived_vehicles) for r in results)
    total_discharges = sum(len(r.discharged_vehicles) for r in results)
    delays = [v.waiting_time(r.time) for r in results for v in r.discharged_vehicles]
    avg_delay = sum(delays) / len(delays) if delays else 0.0
    max_delay = max(delays) if delays else 0.0
    step_queues = [sum(r.queue_lengths.values()) for r in results]
    avg_queue = sum(step_queues) / len(step_queues) if step_queues else 0.0
    max_queue = max(step_queues) if step_queues else 0

    stdout.write("Simulation Execution Summary\n")
    stdout.write(f"Controller:      {args.controller}\n")
    stdout.write(f"Duration:        {duration:.1f} s\n")
    stdout.write(f"Steps Executed:  {len(results)}\n")
    stdout.write(f"Total Arrivals:  {total_arrivals}\n")
    stdout.write(f"Total Served:    {total_discharges}\n")
    stdout.write(f"Average Delay:   {avg_delay:.3f} s\n")
    stdout.write(f"Max Delay:       {max_delay:.3f} s\n")
    stdout.write(f"Average Queue:   {avg_queue:.3f} veh\n")
    stdout.write(f"Max Queue:       {max_queue} veh\n")

    if args.out_csv:
        export_step_results_to_csv(results, destination=args.out_csv)
        stdout.write(f"Exported CSV:    {args.out_csv}\n")

    if args.out_json:
        export_step_results_to_json(results, destination=args.out_json)
        stdout.write(f"Exported JSON:   {args.out_json}\n")

    if getattr(args, "dashboard", False):
        stdout.write("\n" + render_step_dashboard(results[-1], plan=signal_plan) + "\n")

    return 0


def handle_benchmark(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    scenario = load_scenario_from_file(args.config)
    duration = (
        args.duration if args.duration is not None else scenario.simulation.duration
    )
    seed = args.seed if args.seed is not None else scenario.simulation.seed

    raw_names = [c.strip() for c in args.controllers.split(",") if c.strip()]
    if not raw_names:
        raise ConfigurationError("no valid controllers specified for benchmark")

    intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()

    controllers: dict[str, SignalController] = {}
    for name in raw_names:
        controllers[name] = instantiate_controller(name, signal_plan, intersection)

    harness = BenchmarkHarness(
        intersection=intersection,
        signal_plan=signal_plan,
        demands=demands,
        step_size=sim_cfg.step_size,
        seed=seed,
    )

    benchmark_result = harness.run_benchmark(controllers=controllers, duration=duration)

    stdout.write("Signal Controller Benchmark Results\n")
    stdout.write(
        f"{'Controller':<15} {'Served':<8} {'Compl %':<10} "
        f"{'Avg Delay(s)':<14} {'Max Queue':<11} {'Wasted Green(s)':<16}\n"
    )
    stdout.write("-" * 76 + "\n")
    for m in benchmark_result.metrics.values():
        stdout.write(
            f"{m.controller_name:<15} {m.total_discharges:<8} "
            f"{m.completion_rate:<10.2f} {m.average_delay:<14.3f} "
            f"{m.max_queue:<11} {m.wasted_green_time:<16.3f}\n"
        )
    stdout.write("-" * 76 + "\n")
    stdout.write(f"Best by Delay:      {benchmark_result.best_by_delay}\n")
    stdout.write(f"Best by Throughput: {benchmark_result.best_by_throughput}\n")

    if args.out_csv:
        export_benchmark_to_csv(benchmark_result, destination=args.out_csv)
        stdout.write(f"Exported CSV:       {args.out_csv}\n")

    if args.out_json:
        export_benchmark_to_json(benchmark_result, destination=args.out_json)
        stdout.write(f"Exported JSON:      {args.out_json}\n")

    return 0
