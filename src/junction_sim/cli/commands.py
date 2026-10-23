import argparse
import sys
import webbrowser
from pathlib import Path
from typing import TextIO

from junction_sim.benchmarks.harness import BenchmarkHarness
from junction_sim.config.loader import load_scenario_from_file
from junction_sim.config.schema import ScenarioConfig
from junction_sim.controllers.actuated import ActuatedController
from junction_sim.controllers.dual_ring import DualRingController
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.controllers.protocol import SignalController
from junction_sim.domain.dual_ring import build_nema_eight_phase_structure
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.engine.engine import SimulationEngine
from junction_sim.exceptions import ConfigurationError
from junction_sim.presets import get_preset, list_presets_info
from junction_sim.reporting.csv_reporter import (
    export_benchmark_to_csv,
    export_multi_seed_benchmark_to_csv,
    export_step_results_to_csv,
)
from junction_sim.reporting.json_reporter import (
    export_benchmark_to_json,
    export_multi_seed_benchmark_to_json,
    export_step_results_to_json,
)
from junction_sim.visualization import (
    export_3d_html_visualizer,
    export_blender_script,
    export_interactive_html,
    render_step_dashboard,
)


def instantiate_controller(
    name: str, signal_plan: SignalPlan, intersection: Intersection
) -> SignalController:
    if name == "fixed-time":
        return FixedTimeController(signal_plan=signal_plan)
    if name == "actuated":
        return ActuatedController(signal_plan=signal_plan, intersection=intersection)
    if name == "max-pressure":
        return MaxPressureController(signal_plan=signal_plan, intersection=intersection)
    if name == "dual-ring":
        try:
            structure = build_nema_eight_phase_structure(intersection)
        except Exception as exc:
            raise ConfigurationError(
                f"intersection '{intersection.id}' is incompatible with "
                f"dual-ring controller: {exc}"
            ) from exc
        return DualRingController(
            dual_ring=structure, signal_plan=signal_plan, intersection=intersection
        )
    raise ConfigurationError(
        f"unknown controller '{name}', expected one of: "
        "fixed-time, actuated, max-pressure, dual-ring"
    )


def load_scenario_from_args(args: argparse.Namespace) -> ScenarioConfig:
    preset_name = getattr(args, "preset", None)
    if preset_name is not None:
        return get_preset(preset_name)
    return load_scenario_from_file(args.config)


def handle_run(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    scenario = load_scenario_from_args(args)
    duration = (
        args.duration if args.duration is not None else scenario.simulation.duration
    )
    seed = args.seed if args.seed is not None else scenario.simulation.seed

    intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()
    controller = instantiate_controller(args.controller, signal_plan, intersection)
    ped_demands = scenario.build_pedestrian_demands()

    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=signal_plan,
        demands=demands,
        pedestrian_demands=ped_demands,
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

    if intersection.crosswalks:
        ped_arrivals = sum(len(r.arrived_pedestrians) for r in results)
        ped_served = sum(len(r.discharged_pedestrians) for r in results)
        stdout.write(f"Ped Arrivals:    {ped_arrivals}\n")
        stdout.write(f"Ped Served:      {ped_served}\n")

    if args.out_csv:
        export_step_results_to_csv(results, destination=args.out_csv)
        stdout.write(f"Exported CSV:    {args.out_csv}\n")

    if args.out_json:
        export_step_results_to_json(results, destination=args.out_json)
        stdout.write(f"Exported JSON:   {args.out_json}\n")

    if getattr(args, "out_html", None):
        preset_or_name = getattr(args, "preset", None) or "custom"
        export_interactive_html(
            results=results,
            intersection=intersection,
            signal_plan=signal_plan,
            destination=args.out_html,
            controller_name=args.controller,
            scenario_name=preset_or_name,
            seed=seed,
            step_size=sim_cfg.step_size,
        )
        stdout.write(f"Exported HTML:   {args.out_html}\n")

    if getattr(args, "out_html_3d", None):
        preset_or_name = getattr(args, "preset", None) or "custom"
        export_3d_html_visualizer(
            results=results,
            intersection=intersection,
            signal_plan=signal_plan,
            destination=args.out_html_3d,
            controller_name=args.controller,
            scenario_name=preset_or_name,
            seed=seed,
            step_size=sim_cfg.step_size,
        )
        stdout.write(f"Exported 3D HTML:{args.out_html_3d}\n")

    if getattr(args, "export_blender", None):
        preset_or_name = getattr(args, "preset", None) or "custom"
        export_blender_script(
            results=results,
            intersection=intersection,
            signal_plan=signal_plan,
            destination=args.export_blender,
            controller_name=args.controller,
            scenario_name=preset_or_name,
            seed=seed,
        )
        stdout.write(f"Exported Blender:{args.export_blender}\n")

    if getattr(args, "dashboard", False):
        stdout.write("\n" + render_step_dashboard(results[-1], plan=signal_plan) + "\n")

    return 0


def handle_benchmark(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    scenario = load_scenario_from_args(args)
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

    num_seeds: int | None = getattr(args, "num_seeds", None)
    seeds_arg: str | None = getattr(args, "seeds", None)

    if num_seeds is not None or seeds_arg is not None:
        if seeds_arg is not None:
            try:
                seeds = [int(s.strip()) for s in seeds_arg.split(",") if s.strip()]
            except ValueError as err:
                raise ConfigurationError(
                    f"invalid integer seed in seeds list: {seeds_arg}"
                ) from err
            if not seeds:
                raise ConfigurationError("no valid seeds specified in --seeds")
        else:
            assert num_seeds is not None
            if num_seeds <= 0:
                raise ConfigurationError("num_seeds must be greater than zero")
            base_seed = seed if seed is not None else 42
            seeds = [base_seed + i for i in range(num_seeds)]

        multi_result = harness.run_multi_seed_benchmark(
            controllers=controllers, seeds=seeds, duration=duration
        )

        stdout.write(f"Multi-Seed Signal Controller Benchmark ({len(seeds)} runs)\n")
        stdout.write(
            f"{'Controller':<15} {'Runs':<6} {'Delay (s)':<18} {'95% CI (s)':<18} "
            f"{'Discharges':<14} {'Compl %':<10}\n"
        )
        stdout.write("-" * 85 + "\n")
        for ms_metric in multi_result.controller_metrics.values():
            delay_str = f"{ms_metric.mean_delay:.2f} \u00b1 {ms_metric.std_delay:.2f}"
            ci_str = (
                f"[{ms_metric.ci95_delay_lower:.2f}, {ms_metric.ci95_delay_upper:.2f}]"
            )
            dis_str = (
                f"{ms_metric.mean_discharges:.1f} \u00b1 {ms_metric.std_discharges:.1f}"
            )
            stdout.write(
                f"{ms_metric.controller_name:<15} {ms_metric.runs:<6} "
                f"{delay_str:<18} {ci_str:<18} "
                f"{dis_str:<14} {ms_metric.mean_completion_rate:<10.2f}\n"
            )
        stdout.write("-" * 85 + "\n")
        stdout.write(f"Best by Delay:      {multi_result.best_by_delay}\n")
        stdout.write(f"Best by Throughput: {multi_result.best_by_throughput}\n")

        if args.out_csv:
            export_multi_seed_benchmark_to_csv(multi_result, destination=args.out_csv)
            stdout.write(f"Exported CSV:       {args.out_csv}\n")

        if args.out_json:
            export_multi_seed_benchmark_to_json(multi_result, destination=args.out_json)
            stdout.write(f"Exported JSON:      {args.out_json}\n")

        return 0

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


def handle_presets(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    action = getattr(args, "preset_action", None)
    if action == "export":
        cfg = get_preset(args.preset)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
        stdout.write(f"Exported preset '{args.preset}' to {out_path}\n")
        return 0

    stdout.write("Available Scenario Presets\n")
    stdout.write(f"{'Preset Name':<24} {'Description'}\n")
    stdout.write("-" * 76 + "\n")
    for info in list_presets_info():
        stdout.write(f"{info.name:<24} {info.description}\n")
    return 0


def handle_visualize(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    scenario = load_scenario_from_args(args)
    duration = (
        args.duration if args.duration is not None else scenario.simulation.duration
    )
    seed = args.seed if args.seed is not None else scenario.simulation.seed

    intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()
    controller = instantiate_controller(args.controller, signal_plan, intersection)
    ped_demands = scenario.build_pedestrian_demands()

    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=signal_plan,
        demands=demands,
        pedestrian_demands=ped_demands,
        controller=controller,
        step_size=sim_cfg.step_size,
        seed=seed,
    )

    results = engine.run(duration)
    preset_or_name = getattr(args, "preset", None) or "custom"
    out_html = getattr(args, "out_html", "visualizer.html")

    use_3d = getattr(args, "three_d", False) or getattr(args, "mode", "3d") == "3d"

    if use_3d:
        export_3d_html_visualizer(
            results=results,
            intersection=intersection,
            signal_plan=signal_plan,
            destination=out_html,
            controller_name=args.controller,
            scenario_name=preset_or_name,
            seed=seed,
            step_size=sim_cfg.step_size,
        )
    else:
        export_interactive_html(
            results=results,
            intersection=intersection,
            signal_plan=signal_plan,
            destination=out_html,
            controller_name=args.controller,
            scenario_name=preset_or_name,
            seed=seed,
            step_size=sim_cfg.step_size,
        )

    vis_label = "3D Photorealistic WebGL" if use_3d else "2D Interactive Canvas"
    stdout.write(f"Visualization Generated Successfully ({vis_label})\n")
    stdout.write(f"Controller:      {args.controller}\n")
    stdout.write(f"Duration:        {duration:.1f} s\n")
    stdout.write(f"Steps:           {len(results)}\n")
    stdout.write(f"Exported HTML:   {out_html}\n")

    if getattr(args, "open", False):
        resolved_uri = Path(out_html).resolve().as_uri()
        webbrowser.open(resolved_uri)
        stdout.write(f"Opened visualizer in browser: {resolved_uri}\n")

    return 0


def handle_export_blender(args: argparse.Namespace, stdout: TextIO = sys.stdout) -> int:
    scenario = load_scenario_from_args(args)
    duration = (
        args.duration if args.duration is not None else scenario.simulation.duration
    )
    seed = args.seed if args.seed is not None else scenario.simulation.seed

    intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()
    controller = instantiate_controller(args.controller, signal_plan, intersection)
    ped_demands = scenario.build_pedestrian_demands()

    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=signal_plan,
        demands=demands,
        pedestrian_demands=ped_demands,
        controller=controller,
        step_size=sim_cfg.step_size,
        seed=seed,
    )

    results = engine.run(duration)
    preset_or_name = getattr(args, "preset", None) or "custom"
    fps = getattr(args, "fps", 24)

    export_blender_script(
        results=results,
        intersection=intersection,
        signal_plan=signal_plan,
        destination=args.out,
        controller_name=args.controller,
        scenario_name=preset_or_name,
        seed=seed,
        fps=fps,
    )

    stdout.write("Blender Scene Script Generated Successfully\n")
    stdout.write(f"Controller:      {args.controller}\n")
    stdout.write(f"Duration:        {duration:.1f} s\n")
    stdout.write(f"FPS:             {fps}\n")
    stdout.write(f"Steps:           {len(results)}\n")
    stdout.write(f"Exported Script: {args.out}\n")
    return 0
