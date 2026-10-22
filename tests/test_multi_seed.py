import io
import json
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from junction_sim.benchmarks.harness import BenchmarkHarness
from junction_sim.benchmarks.metrics import BenchmarkMetrics
from junction_sim.benchmarks.multi_seed import (
    MultiSeedBenchmarkResult,
    MultiSeedMetrics,
    aggregate_seed_metrics,
)
from junction_sim.cli import main
from junction_sim.cli.commands import handle_benchmark
from junction_sim.cli.parser import create_parser
from junction_sim.controllers.actuated import ActuatedController
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.exceptions import ConfigurationError, ValidationError
from junction_sim.reporting.csv_reporter import export_multi_seed_benchmark_to_csv
from junction_sim.reporting.json_reporter import export_multi_seed_benchmark_to_json


def create_test_setup() -> tuple[Intersection, SignalPlan, tuple[DemandProfile, ...]]:
    mov_n = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_s = Movement(
        id="S_T",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    lane_n = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))

    intersection = Intersection(
        id="ms_int",
        approaches=(app_n, app_s),
        movements=(mov_n, mov_s),
        conflicting_movement_pairs=frozenset(),
    )

    p1 = SignalPhase(id="P1", green_movement_ids=("N_T",), green_duration=10.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("S_T",), green_duration=10.0)
    signal_plan = SignalPlan(id="ms_plan", phases=(p1, p2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=500.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=500.0),
    )
    return intersection, signal_plan, demands


def test_aggregate_seed_metrics_empty() -> None:
    with pytest.raises(ValidationError, match="runs_metrics cannot be empty"):
        aggregate_seed_metrics("ctrl", [])


def test_aggregate_seed_metrics_single_run() -> None:
    m = BenchmarkMetrics(
        controller_name="fixed-time",
        total_arrivals=20,
        total_discharges=18,
        completion_rate=90.0,
        average_delay=5.5,
        max_delay=12.0,
        average_queue=3.0,
        max_queue=6,
        phase_switch_count=2,
        wasted_green_time=1.0,
    )
    agg = aggregate_seed_metrics("fixed-time", [m])
    assert agg.controller_name == "fixed-time"
    assert agg.runs == 1
    assert agg.mean_delay == 5.5
    assert agg.std_delay == 0.0
    assert agg.ci95_delay_lower == 5.5
    assert agg.ci95_delay_upper == 5.5
    assert agg.mean_discharges == 18.0
    assert agg.std_discharges == 0.0
    assert agg.mean_completion_rate == 90.0
    assert agg.mean_max_queue == 6.0
    assert agg.mean_wasted_green == 1.0


def test_aggregate_seed_metrics_multiple_runs() -> None:
    m1 = BenchmarkMetrics(
        controller_name="test",
        total_arrivals=20,
        total_discharges=15,
        completion_rate=75.0,
        average_delay=4.0,
        max_delay=8.0,
        average_queue=2.0,
        max_queue=4,
        phase_switch_count=2,
        wasted_green_time=0.5,
    )
    m2 = BenchmarkMetrics(
        controller_name="test",
        total_arrivals=20,
        total_discharges=17,
        completion_rate=85.0,
        average_delay=6.0,
        max_delay=10.0,
        average_queue=3.0,
        max_queue=6,
        phase_switch_count=3,
        wasted_green_time=1.5,
    )
    agg = aggregate_seed_metrics("test", [m1, m2])
    assert agg.runs == 2
    assert agg.mean_delay == 5.0
    assert agg.std_delay > 0.0
    assert agg.ci95_delay_lower < 5.0
    assert agg.ci95_delay_upper > 5.0
    assert agg.mean_discharges == 16.0
    assert agg.std_discharges > 0.0
    assert agg.mean_completion_rate == 80.0
    assert agg.mean_max_queue == 5.0
    assert agg.mean_wasted_green == 1.0


def test_multi_seed_benchmark_result_properties() -> None:
    m1 = MultiSeedMetrics(
        controller_name="c1",
        runs=3,
        mean_delay=10.0,
        std_delay=1.0,
        ci95_delay_lower=8.0,
        ci95_delay_upper=12.0,
        mean_discharges=50.0,
        std_discharges=2.0,
        mean_completion_rate=85.0,
        mean_max_queue=5.0,
        mean_wasted_green=2.0,
    )
    m2 = MultiSeedMetrics(
        controller_name="c2",
        runs=3,
        mean_delay=5.0,
        std_delay=0.5,
        ci95_delay_lower=4.0,
        ci95_delay_upper=6.0,
        mean_discharges=80.0,
        std_discharges=3.0,
        mean_completion_rate=95.0,
        mean_max_queue=3.0,
        mean_wasted_green=1.0,
    )
    res = MultiSeedBenchmarkResult(
        controller_metrics={"c1": m1, "c2": m2},
        seeds=(1, 2, 3),
        duration=60.0,
        step_size=1.0,
    )
    assert res.best_by_delay == "c2"
    assert res.best_by_throughput == "c2"

    with pytest.raises(PydanticValidationError):
        res.duration = 100.0


def test_multi_seed_benchmark_result_empty_metrics() -> None:
    res = MultiSeedBenchmarkResult(
        controller_metrics={},
        seeds=(42,),
        duration=10.0,
        step_size=1.0,
    )
    with pytest.raises(ValidationError, match="no metrics available"):
        _ = res.best_by_delay
    with pytest.raises(ValidationError, match="no metrics available"):
        _ = res.best_by_throughput


def test_harness_evaluate_multi_seed_validation() -> None:
    inter, plan, demands = create_test_setup()
    harness = BenchmarkHarness(inter, plan, demands, step_size=1.0)
    ctrl = FixedTimeController(signal_plan=plan)

    with pytest.raises(ValidationError, match="seeds sequence cannot be empty"):
        harness.evaluate_controller_multi_seed(ctrl, "ft", [], duration=10.0)

    with pytest.raises(ValidationError, match="controllers mapping cannot be empty"):
        harness.run_multi_seed_benchmark({}, seeds=[1, 2], duration=10.0)

    with pytest.raises(ValidationError, match="seeds sequence cannot be empty"):
        harness.run_multi_seed_benchmark({"ft": ctrl}, seeds=[], duration=10.0)


def test_harness_run_multi_seed_benchmark() -> None:
    inter, plan, demands = create_test_setup()
    harness = BenchmarkHarness(inter, plan, demands, step_size=1.0)
    c1 = FixedTimeController(signal_plan=plan)
    c2 = ActuatedController(signal_plan=plan, intersection=inter)

    res = harness.run_multi_seed_benchmark(
        controllers={"fixed-time": c1, "actuated": c2},
        seeds=[10, 20],
        duration=30.0,
    )
    assert len(res.controller_metrics) == 2
    assert "fixed-time" in res.controller_metrics
    assert "actuated" in res.controller_metrics
    assert res.seeds == (10, 20)
    assert res.controller_metrics["fixed-time"].runs == 2
    assert res.best_by_delay in ["fixed-time", "actuated"]
    assert res.best_by_throughput in ["fixed-time", "actuated"]


def test_export_multi_seed_csv(tmp_path: Path) -> None:
    m = MultiSeedMetrics(
        controller_name="ctrl",
        runs=2,
        mean_delay=8.5,
        std_delay=0.5,
        ci95_delay_lower=7.8,
        ci95_delay_upper=9.2,
        mean_discharges=30.0,
        std_discharges=1.5,
        mean_completion_rate=92.0,
        mean_max_queue=4.0,
        mean_wasted_green=2.5,
    )
    res = MultiSeedBenchmarkResult(
        controller_metrics={"ctrl": m},
        seeds=(10, 20),
        duration=60.0,
        step_size=1.0,
    )

    csv_str = export_multi_seed_benchmark_to_csv(res)
    assert "controller,runs,mean_delay_s" in csv_str
    assert "ctrl,2,8.500,0.500,7.800,9.200,30.00,1.50,92.00,4.00,2.500" in csv_str

    out_file = tmp_path / "sub" / "out.csv"
    saved = export_multi_seed_benchmark_to_csv(res, destination=out_file)
    assert saved == csv_str
    assert out_file.read_text(encoding="utf-8") == csv_str

    buf = io.StringIO()
    ret = export_multi_seed_benchmark_to_csv(res, destination=buf)
    assert ret == ""
    assert buf.getvalue() == csv_str


def test_export_multi_seed_json(tmp_path: Path) -> None:
    m = MultiSeedMetrics(
        controller_name="ctrl",
        runs=2,
        mean_delay=8.5,
        std_delay=0.5,
        ci95_delay_lower=7.8,
        ci95_delay_upper=9.2,
        mean_discharges=30.0,
        std_discharges=1.5,
        mean_completion_rate=92.0,
        mean_max_queue=4.0,
        mean_wasted_green=2.5,
    )
    res = MultiSeedBenchmarkResult(
        controller_metrics={"ctrl": m},
        seeds=(10, 20),
        duration=60.0,
        step_size=1.0,
    )

    json_str = export_multi_seed_benchmark_to_json(res)
    parsed = json.loads(json_str)
    assert parsed["seeds"] == [10, 20]
    assert parsed["controller_metrics"]["ctrl"]["runs"] == 2

    out_file = tmp_path / "sub" / "out.json"
    saved = export_multi_seed_benchmark_to_json(res, destination=out_file)
    assert saved == json_str
    assert out_file.read_text(encoding="utf-8") == json_str

    buf = io.StringIO()
    ret = export_multi_seed_benchmark_to_json(res, destination=buf)
    assert ret == ""
    assert buf.getvalue() == json_str


def test_cli_benchmark_multi_seed_num_seeds(tmp_path: Path) -> None:
    csv_file = tmp_path / "bench.csv"
    json_file = tmp_path / "bench.json"
    buf = io.StringIO()

    exit_code = main(
        [
            "benchmark",
            "-p",
            "webster_four_way",
            "--controllers",
            "fixed-time,actuated",
            "--duration",
            "20",
            "--num-seeds",
            "3",
            "--out-csv",
            str(csv_file),
            "--out-json",
            str(json_file),
        ],
        stdout=buf,
    )
    assert exit_code == 0
    output = buf.getvalue()
    assert "Multi-Seed Signal Controller Benchmark (3 runs)" in output
    assert "Best by Delay:" in output
    assert "Best by Throughput:" in output
    assert csv_file.exists()
    assert json_file.exists()


def test_cli_benchmark_multi_seed_explicit_seeds(tmp_path: Path) -> None:
    buf = io.StringIO()
    exit_code = main(
        [
            "benchmark",
            "-p",
            "webster_four_way",
            "--controllers",
            "fixed-time",
            "--duration",
            "10",
            "--seeds",
            "101, 102",
        ],
        stdout=buf,
    )
    assert exit_code == 0
    output = buf.getvalue()
    assert "Multi-Seed Signal Controller Benchmark (2 runs)" in output


def test_cli_benchmark_multi_seed_invalid_inputs() -> None:
    parser = create_parser()

    args = parser.parse_args(
        [
            "benchmark",
            "-p",
            "webster_four_way",
            "--num-seeds",
            "0",
        ]
    )
    with pytest.raises(ConfigurationError, match="greater than zero"):
        handle_benchmark(args)

    args_invalid_seed = parser.parse_args(
        [
            "benchmark",
            "-p",
            "webster_four_way",
            "--seeds",
            "abc,def",
        ]
    )
    with pytest.raises(ConfigurationError, match="invalid integer seed"):
        handle_benchmark(args_invalid_seed)

    args_empty_seeds = parser.parse_args(
        [
            "benchmark",
            "-p",
            "webster_four_way",
            "--seeds",
            ",,,",
        ]
    )
    with pytest.raises(ConfigurationError, match="no valid seeds specified"):
        handle_benchmark(args_empty_seeds)
