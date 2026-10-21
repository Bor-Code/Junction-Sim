import pytest

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.validation import (
    validate_signal_plan_against_intersection,
    validate_vehicle_against_intersection,
)
from junction_sim.domain.vehicle import Vehicle
from junction_sim.exceptions import InvalidGeometryError, InvalidSignalPlanError


def create_test_intersection() -> Intersection:
    mov_n_t = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov_s_t = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )
    mov_e_t = Movement(
        id="E_T", origin="east", destination="west", turn_type=TurnType.THROUGH
    )
    mov_w_t = Movement(
        id="W_T", origin="west", destination="east", turn_type=TurnType.THROUGH
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

    return Intersection(
        id="int_valid",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )


def test_validate_signal_plan_valid() -> None:
    inter = create_test_intersection()
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=30.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
    )
    plan = SignalPlan(id="plan_valid", phases=(phase_1, phase_2))

    validate_signal_plan_against_intersection(plan, inter)


def test_validate_signal_plan_unknown_movement_raises() -> None:
    inter = create_test_intersection()
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "UNKNOWN"),
        green_duration=30.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
    )
    plan = SignalPlan(id="plan_invalid", phases=(phase_1, phase_2))

    with pytest.raises(InvalidSignalPlanError):
        validate_signal_plan_against_intersection(plan, inter)


def test_validate_signal_plan_conflicting_green_raises() -> None:
    inter = create_test_intersection()
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "E_T"),
        green_duration=30.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("S_T", "W_T"),
        green_duration=20.0,
    )
    plan = SignalPlan(id="plan_conflict", phases=(phase_1, phase_2))

    with pytest.raises(InvalidSignalPlanError):
        validate_signal_plan_against_intersection(plan, inter)


def test_validate_signal_plan_unserved_movements_raises() -> None:
    inter = create_test_intersection()
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=30.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T",),
        green_duration=20.0,
    )
    plan = SignalPlan(id="plan_unserved", phases=(phase_1, phase_2))

    with pytest.raises(InvalidSignalPlanError):
        validate_signal_plan_against_intersection(plan, inter)


def test_validate_vehicle_valid() -> None:
    inter = create_test_intersection()
    veh_without_lane = Vehicle(
        id="veh_01",
        origin="north",
        destination="south",
        arrival_time=10.0,
    )
    validate_vehicle_against_intersection(veh_without_lane, inter)

    veh_with_lane = Vehicle(
        id="veh_02",
        origin="north",
        destination="south",
        arrival_time=12.0,
        target_lane_id="lane_n_0",
    )
    validate_vehicle_against_intersection(veh_with_lane, inter)


def test_validate_vehicle_unknown_origin_raises() -> None:
    inter = create_test_intersection()
    veh = Vehicle(
        id="veh_01",
        origin="northwest",
        destination="south",
        arrival_time=10.0,
    )
    with pytest.raises(InvalidGeometryError):
        validate_vehicle_against_intersection(veh, inter)


def test_validate_vehicle_unknown_destination_raises() -> None:
    inter = create_test_intersection()
    veh = Vehicle(
        id="veh_01",
        origin="north",
        destination="southeast",
        arrival_time=10.0,
    )
    with pytest.raises(InvalidGeometryError):
        validate_vehicle_against_intersection(veh, inter)


def test_validate_vehicle_no_matching_movement_raises() -> None:
    inter = create_test_intersection()
    veh = Vehicle(
        id="veh_01",
        origin="north",
        destination="east",
        arrival_time=10.0,
    )
    with pytest.raises(InvalidGeometryError):
        validate_vehicle_against_intersection(veh, inter)


def test_validate_vehicle_lane_approach_mismatch_raises() -> None:
    inter = create_test_intersection()
    veh = Vehicle(
        id="veh_01",
        origin="north",
        destination="south",
        arrival_time=10.0,
        target_lane_id="lane_s_0",
    )
    with pytest.raises(InvalidGeometryError):
        validate_vehicle_against_intersection(veh, inter)


def test_validate_vehicle_lane_movement_disallowed_raises() -> None:
    inter = create_test_intersection()
    lane_n_right_only = Lane(
        id="lane_n_1",
        approach_id="north",
        allowed_movement_ids=("N_R",),
    )
    mov_n_r = Movement(
        id="N_R", origin="north", destination="west", turn_type=TurnType.RIGHT
    )

    app_n_new = Approach(
        id="north",
        direction=Direction.NORTH,
        lanes=(inter.approaches[0].lanes[0], lane_n_right_only),
    )
    inter_with_turn = Intersection(
        id="int_turn",
        approaches=(app_n_new, *inter.approaches[1:]),
        movements=(*inter.movements, mov_n_r),
        conflicting_movement_pairs=inter.conflicting_movement_pairs,
    )

    veh = Vehicle(
        id="veh_01",
        origin="north",
        destination="south",
        arrival_time=10.0,
        target_lane_id="lane_n_1",
    )
    with pytest.raises(InvalidGeometryError):
        validate_vehicle_against_intersection(veh, inter_with_turn)
