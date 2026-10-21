import pytest

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.step_result import StepResult
from junction_sim.exceptions import ValidationError


def create_sample_setup() -> tuple[Intersection, SignalPlan, tuple[DemandProfile, ...]]:
    mov_n_t = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=3600.0,
    )
    mov_s_t = Movement(
        id="S_T",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=3600.0,
    )
    mov_e_t = Movement(
        id="E_T",
        origin="east",
        destination="west",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=3600.0,
    )
    mov_w_t = Movement(
        id="W_T",
        origin="west",
        destination="east",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=3600.0,
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
        id="int_01",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )

    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=20.0,
        yellow_duration=2.0,
        all_red_duration=1.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=2.0,
        all_red_duration=1.0,
    )
    signal_plan = SignalPlan(id="plan_01", phases=(phase_1, phase_2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=3600.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=3600.0),
        DemandProfile(movement_id="E_T", flow_rate_vph=3600.0),
        DemandProfile(movement_id="W_T", flow_rate_vph=3600.0),
    )

    return intersection, signal_plan, demands


def test_engine_run_matching_single_steps() -> None:
    inter, plan, demands = create_sample_setup()
    engine_run = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=101,
        step_size=1.0,
    )
    engine_step = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=101,
        step_size=1.0,
    )

    results_run = engine_run.run(10.0)
    results_step = tuple(engine_step.step() for _ in range(10))

    assert len(results_run) == 10
    assert results_run == results_step
    assert engine_run.current_time == 10.0
    assert engine_run.step_count == 10


def test_engine_run_iter_streaming() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=202,
        step_size=1.0,
    )

    streamed: list[StepResult] = []
    for i, res in enumerate(engine.run_iter(5.0)):
        assert res.step_index == i
        assert res.time == float(i)
        streamed.append(res)

    assert len(streamed) == 5
    assert engine.current_time == 5.0
    assert engine.step_count == 5


def test_engine_run_iter_early_break() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=303,
        step_size=1.0,
    )

    for i, _ in enumerate(engine.run_iter(10.0)):
        if i == 2:
            break

    assert engine.step_count == 3
    assert engine.current_time == 3.0


def test_engine_consecutive_runs() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=404,
        step_size=1.0,
    )

    batch_1 = engine.run(4.0)
    assert len(batch_1) == 4
    assert batch_1[0].time == 0.0
    assert batch_1[-1].time == 3.0
    assert engine.current_time == 4.0
    assert engine.step_count == 4

    batch_2 = engine.run(4.0)
    assert len(batch_2) == 4
    assert batch_2[0].time == 4.0
    assert batch_2[-1].time == 7.0
    assert engine.current_time == 8.0
    assert engine.step_count == 8


def test_engine_run_with_custom_step_size() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=505,
        step_size=0.5,
    )

    results = engine.run(3.0)
    assert len(results) == 6
    assert results[0].time == 0.0
    assert results[1].time == 0.5
    assert results[-1].time == 2.5
    assert engine.current_time == 3.0
    assert engine.step_count == 6


def test_engine_run_validation_errors() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=606,
        step_size=1.0,
    )

    with pytest.raises(ValidationError):
        engine.run(0.0)

    with pytest.raises(ValidationError):
        engine.run(-5.0)

    with pytest.raises(ValidationError):
        engine.run_iter(0.0)

    with pytest.raises(ValidationError):
        engine.run_iter(-5.0)

    with pytest.raises(ValidationError):
        engine.run(2.5)

    with pytest.raises(ValidationError):
        engine.run_iter(2.5)
