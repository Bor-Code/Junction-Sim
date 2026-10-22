import pytest

from junction_sim.benchmarks.harness import BenchmarkHarness
from junction_sim.benchmarks.metrics import BenchmarkMetrics, BenchmarkResult
from junction_sim.controllers.actuated import ActuatedController
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.exceptions import ValidationError


def create_sample_setup(
    demand_n: float = 600.0,
    demand_s: float = 600.0,
    demand_e: float = 100.0,
    demand_w: float = 100.0,
) -> tuple[Intersection, SignalPlan, tuple[DemandProfile, ...]]:
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
    mov_e_t = Movement(
        id="E_T",
        origin="east",
        destination="west",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_w_t = Movement(
        id="W_T",
        origin="west",
        destination="east",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )

    lane_n = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))
    lane_e = Lane(id="lane_e_0", approach_id="east", allowed_movement_ids=("E_T",))
    lane_w = Lane(id="lane_w_0", approach_id="west", allowed_movement_ids=("W_T",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    app_e = Approach(id="east", direction=Direction.EAST, lanes=(lane_e,))
    app_w = Approach(id="west", direction=Direction.WEST, lanes=(lane_w,))

    conflicts = frozenset(
        {
            frozenset({"N_T", "E_T"}),
            frozenset({"N_T", "W_T"}),
            frozenset({"S_T", "E_T"}),
            frozenset({"S_T", "W_T"}),
        }
    )

    intersection = Intersection(
        id="harness_int",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )

    p1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
        min_green=5.0,
        max_green=35.0,
    )
    p2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
        min_green=5.0,
        max_green=35.0,
    )
    signal_plan = SignalPlan(id="harness_plan", phases=(p1, p2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=demand_n),
        DemandProfile(movement_id="S_T", flow_rate_vph=demand_s),
        DemandProfile(movement_id="E_T", flow_rate_vph=demand_e),
        DemandProfile(movement_id="W_T", flow_rate_vph=demand_w),
    )

    return intersection, signal_plan, demands


def test_benchmark_harness_initialization_and_properties() -> None:
    inter, plan, demands = create_sample_setup()
    harness = BenchmarkHarness(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=0.5,
        seed=123,
    )

    assert harness.intersection == inter
    assert harness.signal_plan == plan
    assert harness.demands == demands
    assert harness.step_size == 0.5
    assert harness.seed == 123


def test_benchmark_harness_guards() -> None:
    inter, plan, demands = create_sample_setup()

    with pytest.raises(ValidationError):
        BenchmarkHarness(
            intersection=inter,
            signal_plan=plan,
            demands=demands,
            step_size=0.0,
        )

    with pytest.raises(ValidationError):
        BenchmarkHarness(
            intersection=inter,
            signal_plan=plan,
            demands=demands,
            step_size=-1.0,
        )

    invalid_plan = SignalPlan(
        id="inv_plan",
        phases=(
            SignalPhase(id="PX", green_movement_ids=("UNKNOWN",), green_duration=10.0),
            SignalPhase(id="PY", green_movement_ids=("N_T",), green_duration=10.0),
        ),
    )
    with pytest.raises(ValidationError):
        BenchmarkHarness(
            intersection=inter,
            signal_plan=invalid_plan,
            demands=demands,
        )

    harness = BenchmarkHarness(intersection=inter, signal_plan=plan, demands=demands)

    with pytest.raises(ValidationError):
        harness.evaluate_controller(FixedTimeController(plan), "fixed", duration=0.0)

    with pytest.raises(ValidationError):
        harness.evaluate_controller(FixedTimeController(plan), "fixed", duration=-5.0)

    with pytest.raises(ValidationError):
        harness.evaluate_controller("not_a_controller", "dummy", duration=10.0)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        harness.run_benchmark(controllers={}, duration=10.0)


def test_benchmark_metrics_and_result_properties() -> None:
    m1 = BenchmarkMetrics(
        controller_name="ctrl_1",
        total_arrivals=100,
        total_discharges=90,
        completion_rate=90.0,
        average_delay=12.5,
        max_delay=25.0,
        average_queue=3.2,
        max_queue=7,
        phase_switch_count=4,
        wasted_green_time=6.0,
    )
    m2 = BenchmarkMetrics(
        controller_name="ctrl_2",
        total_arrivals=100,
        total_discharges=95,
        completion_rate=95.0,
        average_delay=8.0,
        max_delay=18.0,
        average_queue=2.1,
        max_queue=5,
        phase_switch_count=6,
        wasted_green_time=1.0,
    )

    res = BenchmarkResult(
        metrics={"ctrl_1": m1, "ctrl_2": m2},
        duration=100.0,
        step_size=1.0,
        seed=42,
    )

    assert res.best_by_delay == "ctrl_2"
    assert res.best_by_throughput == "ctrl_2"
    assert res.delay_reduction_pct("ctrl_1", "ctrl_2") == 36.0

    with pytest.raises(ValidationError):
        res.delay_reduction_pct("unknown", "ctrl_2")

    with pytest.raises(ValidationError):
        res.delay_reduction_pct("ctrl_1", "unknown")

    empty_res = BenchmarkResult(metrics={}, duration=50.0, step_size=1.0)
    with pytest.raises(ValidationError):
        _ = empty_res.best_by_delay

    with pytest.raises(ValidationError):
        _ = empty_res.best_by_throughput


def test_benchmark_harness_single_controller_evaluation() -> None:
    inter, plan, demands = create_sample_setup(600.0, 600.0, 200.0, 200.0)
    harness = BenchmarkHarness(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=42,
    )

    metrics = harness.evaluate_controller(
        FixedTimeController(plan), name="fixed", duration=80.0
    )

    assert metrics.controller_name == "fixed"
    assert metrics.total_arrivals > 10
    assert metrics.total_discharges > 0
    assert metrics.completion_rate > 0.0
    assert metrics.average_delay > 0.0
    assert metrics.max_delay >= metrics.average_delay
    assert metrics.average_queue > 0.0
    assert metrics.max_queue >= 1
    assert metrics.phase_switch_count >= 1
    assert metrics.wasted_green_time >= 0.0


def test_benchmark_harness_multi_controller_comparison() -> None:
    inter, plan, demands = create_sample_setup(
        demand_n=800.0,
        demand_s=800.0,
        demand_e=60.0,
        demand_w=60.0,
    )
    harness = BenchmarkHarness(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=100,
    )

    fixed = FixedTimeController(plan)
    actuated = ActuatedController(plan, inter)
    max_pressure = MaxPressureController(plan, inter)

    result = harness.run_benchmark(
        {
            "fixed_time": fixed,
            "actuated": actuated,
            "max_pressure": max_pressure,
        },
        duration=180.0,
    )

    assert len(result.metrics) == 3
    assert "fixed_time" in result.metrics
    assert "actuated" in result.metrics
    assert "max_pressure" in result.metrics

    m_fixed = result.metrics["fixed_time"]
    m_actuated = result.metrics["actuated"]
    m_mp = result.metrics["max_pressure"]

    assert m_actuated.wasted_green_time < m_fixed.wasted_green_time
    assert m_mp.wasted_green_time < m_fixed.wasted_green_time

    assert m_actuated.total_discharges >= m_fixed.total_discharges
    assert m_mp.total_discharges >= m_fixed.total_discharges

    assert result.delay_reduction_pct("fixed_time", "actuated") > 0.0
    assert result.best_by_delay in ("actuated", "max_pressure")


def test_benchmark_harness_zero_demand_edge_case() -> None:
    inter, plan, demands = create_sample_setup(0.0, 0.0, 0.0, 0.0)
    harness = BenchmarkHarness(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=1,
    )

    ctrl = FixedTimeController(plan)
    metrics = harness.evaluate_controller(ctrl, "empty", duration=40.0)

    assert metrics.total_arrivals == 0
    assert metrics.total_discharges == 0
    assert metrics.completion_rate == 100.0
    assert metrics.average_delay == 0.0
    assert metrics.max_delay == 0.0
    assert metrics.average_queue == 0.0
    assert metrics.max_queue == 0

    res = BenchmarkResult(
        metrics={"empty_1": metrics, "empty_2": metrics},
        duration=40.0,
        step_size=1.0,
    )
    assert res.delay_reduction_pct("empty_1", "empty_2") == 0.0
