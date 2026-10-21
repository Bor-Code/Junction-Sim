import pytest

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import (
    InvalidGeometryError,
    InvalidSignalPlanError,
    InvalidStateError,
    ValidationError,
)


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


def test_engine_initialization() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=42,
        step_size=1.0,
    )

    assert engine.current_time == 0.0
    assert engine.step_count == 0
    assert engine.active_phase_id == "P1"
    assert engine.signal_state == SignalState.GREEN
    assert not engine.is_in_transition
    assert engine.intersection == inter
    assert engine.signal_plan == plan
    assert len(engine.queues) == 4
    assert engine.get_queue_length("lane_n_0") == 0


def test_engine_single_step_execution() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=42,
        step_size=1.0,
    )

    result = engine.step()

    assert result.time == 0.0
    assert result.step_index == 0
    assert result.active_phase_id == "P1"
    assert result.signal_state == SignalState.GREEN
    assert engine.current_time == 1.0
    assert engine.step_count == 1
    assert "lane_n_0" in result.queue_lengths


def test_engine_red_lanes_accumulate_without_discharge() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=123,
        step_size=1.0,
    )

    for _ in range(5):
        result = engine.step()
        for discharged_veh in result.discharged_vehicles:
            assert discharged_veh.target_lane_id in ("lane_n_0", "lane_s_0")

    assert engine.get_queue_length("lane_e_0") > 0
    assert engine.get_queue_length("lane_w_0") > 0


def test_engine_request_phase_change_lifecycle() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=42,
        step_size=1.0,
    )

    engine.step()
    first_state: SignalState = engine.signal_state
    assert first_state == SignalState.GREEN

    engine.request_phase_change("P1")
    assert engine.signal_state == SignalState.GREEN

    engine.request_phase_change("P2")
    yellow_state: SignalState = engine.signal_state
    assert yellow_state == SignalState.YELLOW
    assert engine.is_in_transition

    engine.request_phase_change("P2")

    with pytest.raises(InvalidStateError):
        engine.request_phase_change("P1")

    res_y1 = engine.step()
    assert res_y1.discharged_vehicles == ()
    assert res_y1.signal_state == SignalState.YELLOW

    res_y2 = engine.step()
    assert res_y2.discharged_vehicles == ()
    assert res_y2.signal_state == SignalState.ALL_RED

    res_green1 = engine.step()
    assert res_green1.signal_state == SignalState.GREEN
    assert res_green1.active_phase_id == "P2"
    assert not engine.is_in_transition
    assert len(res_green1.discharged_vehicles) > 0
    for discharged in res_green1.discharged_vehicles:
        assert discharged.target_lane_id in ("lane_e_0", "lane_w_0")

    res_green2 = engine.step()
    assert res_green2.signal_state == SignalState.GREEN
    assert res_green2.active_phase_id == "P2"


def test_engine_reproducibility() -> None:
    inter, plan, demands = create_sample_setup()

    engine1 = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=999,
        step_size=1.0,
    )
    engine2 = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=999,
        step_size=1.0,
    )

    for _ in range(15):
        res1 = engine1.step()
        res2 = engine2.step()
        assert res1 == res2


def test_engine_error_guards() -> None:
    inter, plan, demands = create_sample_setup()

    with pytest.raises(ValidationError):
        SimulationEngine(
            intersection=inter,
            signal_plan=plan,
            demands=demands,
            step_size=0.0,
        )

    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
    )

    with pytest.raises(InvalidGeometryError):
        engine.get_queue("non_existent_lane")

    with pytest.raises(InvalidSignalPlanError):
        engine.request_phase_change("UNKNOWN_PHASE")
