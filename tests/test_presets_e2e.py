import io
from pathlib import Path

import pytest

from junction_sim.benchmarks.harness import BenchmarkHarness
from junction_sim.cli import main
from junction_sim.controllers.actuated import ActuatedController
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.controllers.protocol import SignalController
from junction_sim.engine.engine import SimulationEngine
from junction_sim.presets import (
    build_arterial_corridor_preset,
    build_bottleneck_spillback_preset,
    build_peak_hour_surge_preset,
    build_webster_four_way_preset,
    get_preset,
    list_presets,
)


@pytest.mark.parametrize("preset_name", list_presets())
def test_e2e_all_presets_harness_benchmark(preset_name: str) -> None:
    scenario = get_preset(preset_name)
    inter, plan, demands, sim_cfg = scenario.build_scenario()

    controllers: dict[str, SignalController] = {
        "fixed-time": FixedTimeController(signal_plan=plan),
        "actuated": ActuatedController(signal_plan=plan, intersection=inter),
        "max-pressure": MaxPressureController(signal_plan=plan, intersection=inter),
    }

    harness = BenchmarkHarness(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )

    result = harness.run_benchmark(controllers=controllers, duration=60.0)

    assert set(result.metrics.keys()) == {
        "fixed-time",
        "actuated",
        "max-pressure",
    }
    for m in result.metrics.values():
        assert m.average_delay >= 0.0
        assert m.completion_rate >= 0.0
        assert m.max_queue >= 0
        assert m.wasted_green_time >= 0.0

    assert result.best_by_delay in controllers
    assert result.best_by_throughput in controllers


def test_e2e_seed_determinism_preset() -> None:
    scenario = build_webster_four_way_preset()
    inter1, plan1, demands1, _ = scenario.build_scenario()
    inter2, plan2, demands2, _ = scenario.build_scenario()

    engine1 = SimulationEngine(
        intersection=inter1,
        signal_plan=plan1,
        demands=demands1,
        controller=MaxPressureController(signal_plan=plan1, intersection=inter1),
        step_size=1.0,
        seed=999,
    )
    engine2 = SimulationEngine(
        intersection=inter2,
        signal_plan=plan2,
        demands=demands2,
        controller=MaxPressureController(signal_plan=plan2, intersection=inter2),
        step_size=1.0,
        seed=999,
    )

    results1 = engine1.run(60.0)
    results2 = engine2.run(60.0)

    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2, strict=True):
        assert r1.step_index == r2.step_index
        assert r1.active_phase_id == r2.active_phase_id
        assert r1.signal_state == r2.signal_state
        assert len(r1.arrived_vehicles) == len(r2.arrived_vehicles)
        assert len(r1.discharged_vehicles) == len(r2.discharged_vehicles)
        assert r1.queue_lengths == r2.queue_lengths


def test_e2e_arterial_corridor_dynamics() -> None:
    scenario = build_arterial_corridor_preset()
    inter, plan, demands, sim_cfg = scenario.build_scenario()

    ctrl_fixed = FixedTimeController(signal_plan=plan)
    ctrl_actuated = ActuatedController(signal_plan=plan, intersection=inter)

    harness = BenchmarkHarness(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )

    res = harness.run_benchmark(
        controllers={"fixed-time": ctrl_fixed, "actuated": ctrl_actuated},
        duration=120.0,
    )

    m_fixed = res.metrics["fixed-time"]
    m_actuated = res.metrics["actuated"]

    assert m_fixed.total_arrivals == m_actuated.total_arrivals
    assert m_fixed.total_discharges > 0
    assert m_actuated.total_discharges > 0


def test_e2e_peak_hour_surge_congestion() -> None:
    scenario = build_peak_hour_surge_preset()
    inter, plan, demands, sim_cfg = scenario.build_scenario()

    ctrl_mp = MaxPressureController(signal_plan=plan, intersection=inter)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl_mp,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )

    results = engine.run(90.0)
    queues = [sum(r.queue_lengths.values()) for r in results]
    assert max(queues) > 0


def test_e2e_bottleneck_spillback_storage_bounds() -> None:
    scenario = build_bottleneck_spillback_preset()
    inter, plan, demands, sim_cfg = scenario.build_scenario()

    ctrl_fixed = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl_fixed,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )

    results = engine.run(60.0)
    for r in results:
        for lane_id, count in r.queue_lengths.items():
            lane = inter.get_lane(lane_id)
            assert count <= lane.max_capacity


def test_cli_e2e_full_workflow(tmp_path: Path) -> None:
    csv_file = tmp_path / "step_output.csv"
    json_file = tmp_path / "step_output.json"
    stdout_run = io.StringIO()

    ret_run = main(
        [
            "run",
            "-p",
            "arterial_corridor",
            "--controller",
            "max-pressure",
            "-d",
            "30.0",
            "--dashboard",
            "--out-csv",
            str(csv_file),
            "--out-json",
            str(json_file),
        ],
        stdout=stdout_run,
    )
    assert ret_run == 0
    assert csv_file.exists()
    assert json_file.exists()
    run_output = stdout_run.getvalue()
    assert "Simulation Execution Summary" in run_output
    assert "QUEUE LENGTHS:" in run_output
    assert "INTERSECTION LAYOUT:" in run_output

    bench_csv = tmp_path / "bench_output.csv"
    bench_json = tmp_path / "bench_output.json"
    stdout_bench = io.StringIO()

    ret_bench = main(
        [
            "benchmark",
            "-p",
            "bottleneck_spillback",
            "--controllers",
            "fixed-time,actuated,max-pressure",
            "-d",
            "30.0",
            "--out-csv",
            str(bench_csv),
            "--out-json",
            str(bench_json),
        ],
        stdout=stdout_bench,
    )
    assert ret_bench == 0
    assert bench_csv.exists()
    assert bench_json.exists()
    bench_output = stdout_bench.getvalue()
    assert "Signal Controller Benchmark Results" in bench_output
    assert "Best by Delay:" in bench_output
