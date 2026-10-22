import csv
import io
import json
from pathlib import Path

from junction_sim.benchmarks.metrics import BenchmarkMetrics, BenchmarkResult
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.step_result import StepResult
from junction_sim.reporting.csv_reporter import (
    export_benchmark_to_csv,
    export_step_results_to_csv,
)
from junction_sim.reporting.json_reporter import (
    export_benchmark_to_json,
    export_step_results_to_json,
)


def create_sample_results() -> tuple[StepResult, ...]:
    mov_n_t = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_s_t = Movement(
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

    inter = Intersection(
        id="rep_int",
        approaches=(app_n, app_s),
        movements=(mov_n_t, mov_s_t),
        conflicting_movement_pairs=frozenset(),
    )

    p1 = SignalPhase(id="P1", green_movement_ids=("N_T",), green_duration=10.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("S_T",), green_duration=10.0)
    plan = SignalPlan(id="rep_plan", phases=(p1, p2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=600.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=300.0),
    )

    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=FixedTimeController(plan),
        seed=42,
        step_size=1.0,
    )

    return engine.run(15.0)


def create_sample_benchmark_result() -> BenchmarkResult:
    m1 = BenchmarkMetrics(
        controller_name="fixed_time",
        total_arrivals=50,
        total_discharges=45,
        completion_rate=90.0,
        average_delay=14.25,
        max_delay=28.5,
        average_queue=3.5,
        max_queue=8,
        phase_switch_count=3,
        wasted_green_time=5.0,
    )
    m2 = BenchmarkMetrics(
        controller_name="actuated",
        total_arrivals=50,
        total_discharges=48,
        completion_rate=96.0,
        average_delay=8.1,
        max_delay=16.2,
        average_queue=1.8,
        max_queue=4,
        phase_switch_count=4,
        wasted_green_time=0.5,
    )
    return BenchmarkResult(
        metrics={"fixed_time": m1, "actuated": m2},
        duration=100.0,
        step_size=1.0,
        seed=101,
    )


def test_export_step_results_to_csv_string_and_streams(tmp_path: Path) -> None:
    results = create_sample_results()

    csv_str = export_step_results_to_csv(results)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)

    assert len(rows) == len(results)
    assert "time" in rows[0]
    assert "step_index" in rows[0]
    assert "active_phase" in rows[0]
    assert "signal_state" in rows[0]
    assert "arrived_count" in rows[0]
    assert "discharged_count" in rows[0]
    assert "total_queue" in rows[0]
    assert "controller_reason" in rows[0]
    assert "queue_lane_n_0" in rows[0]
    assert "queue_lane_s_0" in rows[0]

    out_file = tmp_path / "sub" / "steps.csv"
    file_content = export_step_results_to_csv(results, destination=out_file)
    assert out_file.exists()
    assert file_content == csv_str

    stream = io.StringIO()
    ret = export_step_results_to_csv(results, destination=stream)
    assert ret == ""
    assert stream.getvalue() == csv_str


def test_export_step_results_to_csv_empty() -> None:
    csv_str = export_step_results_to_csv([])
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 0
    assert "time" in reader.fieldnames  # type: ignore[operator]


def test_export_benchmark_to_csv_string_and_streams(tmp_path: Path) -> None:
    b_res = create_sample_benchmark_result()

    csv_str = export_benchmark_to_csv(b_res)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["controller"] == "fixed_time"
    assert rows[0]["completion_rate_pct"] == "90.00"
    assert rows[0]["average_delay_s"] == "14.250"
    assert rows[1]["controller"] == "actuated"
    assert rows[1]["completion_rate_pct"] == "96.00"
    assert rows[1]["average_delay_s"] == "8.100"

    out_file = tmp_path / "bench.csv"
    file_content = export_benchmark_to_csv(b_res, destination=out_file)
    assert out_file.exists()
    assert file_content == csv_str

    stream = io.StringIO()
    ret = export_benchmark_to_csv(b_res, destination=stream)
    assert ret == ""
    assert stream.getvalue() == csv_str


def test_export_step_results_to_json_string_and_streams(tmp_path: Path) -> None:
    results = create_sample_results()

    json_str = export_step_results_to_json(results)
    data = json.loads(json_str)

    assert isinstance(data, list)
    assert len(data) == len(results)
    assert data[0]["step_index"] == 0
    assert "arrived_vehicle_ids" in data[0]
    assert "discharged_vehicles" in data[0]
    assert "queue_lengths" in data[0]

    out_file = tmp_path / "sub" / "steps.json"
    file_content = export_step_results_to_json(results, destination=out_file)
    assert out_file.exists()
    assert file_content == json_str

    stream = io.StringIO()
    ret = export_step_results_to_json(results, destination=stream)
    assert ret == ""
    assert stream.getvalue() == json_str


def test_export_step_results_to_json_empty() -> None:
    json_str = export_step_results_to_json([])
    assert json.loads(json_str) == []


def test_export_benchmark_to_json_string_and_streams(tmp_path: Path) -> None:
    b_res = create_sample_benchmark_result()

    json_str = export_benchmark_to_json(b_res)
    data = json.loads(json_str)

    assert data["duration"] == 100.0
    assert data["step_size"] == 1.0
    assert data["seed"] == 101
    assert data["best_by_delay"] == "actuated"
    assert data["best_by_throughput"] == "actuated"
    assert "fixed_time" in data["metrics"]
    assert "actuated" in data["metrics"]
    assert data["metrics"]["fixed_time"]["average_delay"] == 14.25

    out_file = tmp_path / "bench.json"
    file_content = export_benchmark_to_json(b_res, destination=out_file)
    assert out_file.exists()
    assert file_content == json_str

    stream = io.StringIO()
    ret = export_benchmark_to_json(b_res, destination=stream)
    assert ret == ""
    assert stream.getvalue() == json_str


def test_export_benchmark_to_json_empty_metrics() -> None:
    empty_res = BenchmarkResult(metrics={}, duration=50.0, step_size=1.0)
    json_str = export_benchmark_to_json(empty_res)
    data = json.loads(json_str)
    assert data["best_by_delay"] is None
    assert data["best_by_throughput"] is None
    assert data["metrics"] == {}
