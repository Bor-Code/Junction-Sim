from typing import cast

import pytest

from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.protocol import SignalController
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.transition import SignalState
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
        green_duration=10.0,
        yellow_duration=2.0,
        all_red_duration=1.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=10.0,
        yellow_duration=2.0,
        all_red_duration=1.0,
    )
    signal_plan = SignalPlan(id="plan_01", phases=(phase_1, phase_2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="E_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="W_T", flow_rate_vph=1800.0),
    )

    return intersection, signal_plan, demands


def test_engine_with_fixed_time_controller_autonomous_cycle() -> None:
    inter, plan, demands = create_sample_setup()
    controller = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=controller,
        seed=42,
        step_size=1.0,
    )

    assert engine.controller is controller

    results = engine.run(30.0)
    assert len(results) == 30

    res_0 = results[0]
    assert res_0.active_phase_id == "P1"
    assert res_0.signal_state == SignalState.GREEN
    assert res_0.controller_decision is not None
    assert res_0.controller_decision.reason == "green_hold"

    res_10 = results[10]
    assert res_10.active_phase_id == "P1"
    assert res_10.controller_decision is not None
    assert res_10.controller_decision.target_phase_id == "P2"
    assert res_10.controller_decision.reason == "fixed_time_split"

    res_11 = results[11]
    assert res_11.signal_state == SignalState.YELLOW
    assert res_11.controller_decision is not None
    assert res_11.controller_decision.reason == "in_transition"

    res_12 = results[12]
    assert res_12.signal_state == SignalState.ALL_RED
    assert res_12.controller_decision is not None
    assert res_12.controller_decision.reason == "in_transition"

    res_13 = results[13]
    assert res_13.active_phase_id == "P2"
    assert res_13.signal_state == SignalState.GREEN
    assert res_13.controller_decision is not None
    assert res_13.controller_decision.reason == "green_hold"

    res_23 = results[23]
    assert res_23.active_phase_id == "P2"
    assert res_23.controller_decision is not None
    assert res_23.controller_decision.target_phase_id == "P1"
    assert res_23.controller_decision.reason == "fixed_time_split"

    res_26 = results[26]
    assert res_26.active_phase_id == "P1"
    assert res_26.signal_state == SignalState.GREEN


def test_engine_without_controller_backward_compatible() -> None:
    inter, plan, demands = create_sample_setup()
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        seed=101,
        step_size=1.0,
    )

    assert engine.controller is None
    res = engine.step()
    assert res.controller_decision is None
    assert res.active_phase_id == "P1"


def test_engine_invalid_controller_raises() -> None:
    inter, plan, demands = create_sample_setup()

    class InvalidController:
        pass

    with pytest.raises(ValidationError):
        SimulationEngine(
            intersection=inter,
            signal_plan=plan,
            demands=demands,
            controller=cast(SignalController, InvalidController()),
        )
