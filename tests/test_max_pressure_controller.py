import pytest

from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.controllers.protocol import (
    ControllerContext,
    SignalController,
)
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import (
    InvalidSignalPlanError,
    InvalidStateError,
    ValidationError,
)


def create_sample_setup() -> tuple[Intersection, SignalPlan]:
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
        id="mp_int",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )

    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
        min_green=5.0,
        max_green=30.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
        min_green=5.0,
        max_green=30.0,
    )
    signal_plan = SignalPlan(id="mp_plan", phases=(phase_1, phase_2))

    return intersection, signal_plan


def test_max_pressure_controller_protocol_and_properties() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    assert isinstance(controller, SignalController)
    assert controller.signal_plan == plan
    assert controller.intersection == inter
    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 0.0


def test_max_pressure_calculation_and_guards() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    queues = {
        "lane_n_0": 4,
        "lane_s_0": 6,
        "lane_e_0": 2,
        "lane_w_0": 3,
    }
    assert controller.get_phase_pressure("P1", queues) == 10
    assert controller.get_phase_pressure("P2", queues) == 5

    with pytest.raises(InvalidSignalPlanError):
        controller.get_phase_pressure("UNKNOWN_P", queues)


def test_max_pressure_min_green_hold() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    ctx_0 = ControllerContext(
        current_time=0.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_e_0": 50, "lane_w_0": 50, "lane_n_0": 0, "lane_s_0": 0},
    )
    dec_0 = controller.decide(ctx_0)
    assert not dec_0.should_change_phase
    assert dec_0.reason == "min_green_hold"

    ctx_1 = ControllerContext(
        current_time=4.9,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_e_0": 50, "lane_w_0": 50, "lane_n_0": 0, "lane_s_0": 0},
    )
    dec_1 = controller.decide(ctx_1)
    assert not dec_1.should_change_phase
    assert dec_1.reason == "min_green_hold"
    assert controller.elapsed_green == 4.9


def test_max_pressure_switch_to_higher_pressure_phase() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 5, "lane_s_0": 5, "lane_e_0": 1, "lane_w_0": 1},
        )
    )

    ctx_switch = ControllerContext(
        current_time=5.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 1, "lane_s_0": 0, "lane_e_0": 8, "lane_w_0": 4},
    )
    dec_switch = controller.decide(ctx_switch)

    assert dec_switch.should_change_phase
    assert dec_switch.target_phase_id == "P2"
    assert dec_switch.reason == "max_pressure_switch"
    assert controller.current_phase_index == 1
    assert controller.elapsed_green == 0.0


def test_max_pressure_hold_when_current_phase_dominates() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 10, "lane_s_0": 10},
        )
    )

    ctx_hold = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 8, "lane_s_0": 7, "lane_e_0": 2, "lane_w_0": 1},
    )
    dec_hold = controller.decide(ctx_hold)

    assert not dec_hold.should_change_phase
    assert dec_hold.reason == "max_pressure_hold"
    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 10.0


def test_max_pressure_tie_breaking_hysteresis() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 5, "lane_e_0": 5},
        )
    )

    ctx_tie = ControllerContext(
        current_time=6.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 5, "lane_e_0": 5},
    )
    dec_tie = controller.decide(ctx_tie)
    assert not dec_tie.should_change_phase
    assert dec_tie.reason == "max_pressure_hold"

    ctx_zero = ControllerContext(
        current_time=8.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_zero = controller.decide(ctx_zero)
    assert not dec_zero.should_change_phase
    assert dec_zero.reason == "max_pressure_hold"


def test_max_pressure_three_phase_tie_breaking() -> None:
    mov_1 = Movement(
        id="M1",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_2 = Movement(
        id="M2",
        origin="east",
        destination="west",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_3 = Movement(
        id="M3",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )

    lane_1 = Lane(id="L1", approach_id="north", allowed_movement_ids=("M1",))
    lane_2 = Lane(id="L2", approach_id="east", allowed_movement_ids=("M2",))
    lane_3 = Lane(id="L3", approach_id="south", allowed_movement_ids=("M3",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_1,))
    app_e = Approach(id="east", direction=Direction.EAST, lanes=(lane_2,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_3,))

    inter = Intersection(
        id="three_p_int",
        approaches=(app_n, app_e, app_s),
        movements=(mov_1, mov_2, mov_3),
        conflicting_movement_pairs=frozenset(
            {frozenset({"M1", "M2"}), frozenset({"M2", "M3"})}
        ),
    )

    p1 = SignalPhase(
        id="P1",
        green_movement_ids=("M1",),
        green_duration=10.0,
        min_green=5.0,
        max_green=20.0,
    )
    p2 = SignalPhase(
        id="P2",
        green_movement_ids=("M2",),
        green_duration=10.0,
        min_green=5.0,
        max_green=20.0,
    )
    p3 = SignalPhase(
        id="P3",
        green_movement_ids=("M3",),
        green_duration=10.0,
        min_green=5.0,
        max_green=20.0,
    )
    plan = SignalPlan(id="three_p_plan", phases=(p1, p2, p3))

    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"L1": 0, "L2": 10, "L3": 10},
        )
    )

    ctx_3p = ControllerContext(
        current_time=6.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"L1": 0, "L2": 10, "L3": 10},
    )
    dec_3p = controller.decide(ctx_3p)
    assert dec_3p.should_change_phase
    assert dec_3p.target_phase_id == "P2"
    assert dec_3p.reason == "max_pressure_switch"


def test_max_pressure_max_green_starvation_prevention() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 50, "lane_e_0": 2},
        )
    )

    ctx_max = ControllerContext(
        current_time=30.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 50, "lane_e_0": 2},
    )
    dec_max = controller.decide(ctx_max)
    assert dec_max.should_change_phase
    assert dec_max.target_phase_id == "P2"
    assert dec_max.reason == "max_green"
    assert controller.current_phase_index == 1
    assert controller.elapsed_green == 0.0

    controller.reset()
    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 50, "lane_e_0": 0, "lane_w_0": 0},
        )
    )
    ctx_max_empty = ControllerContext(
        current_time=30.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 50, "lane_e_0": 0, "lane_w_0": 0},
    )
    dec_max_empty = controller.decide(ctx_max_empty)
    assert not dec_max_empty.should_change_phase
    assert dec_max_empty.reason == "max_pressure_hold"


def test_max_pressure_transition_lifecycle() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 1, "lane_e_0": 10},
        )
    )
    dec_switch = controller.decide(
        ControllerContext(
            current_time=5.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 0, "lane_e_0": 10},
        )
    )
    assert dec_switch.should_change_phase

    dec_trans_yellow = controller.decide(
        ControllerContext(
            current_time=6.0,
            active_phase_id="P1",
            signal_state=SignalState.YELLOW,
            is_in_transition=True,
            queue_lengths={"lane_e_0": 10},
        )
    )
    assert not dec_trans_yellow.should_change_phase
    assert dec_trans_yellow.reason == "in_transition"

    dec_trans_red = controller.decide(
        ControllerContext(
            current_time=9.0,
            active_phase_id="P1",
            signal_state=SignalState.ALL_RED,
            is_in_transition=True,
            queue_lengths={"lane_e_0": 10},
        )
    )
    assert not dec_trans_red.should_change_phase
    assert dec_trans_red.reason == "in_transition"

    dec_p2_start = controller.decide(
        ControllerContext(
            current_time=10.0,
            active_phase_id="P2",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_e_0": 10},
        )
    )
    assert controller.current_phase_index == 1
    assert controller.elapsed_green == 0.0
    assert dec_p2_start.reason == "min_green_hold"


def test_max_pressure_guards_and_external_override() -> None:
    inter, plan = create_sample_setup()
    controller = MaxPressureController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=1.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )

    with pytest.raises(InvalidStateError):
        controller.decide(
            ControllerContext(
                current_time=0.5,
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )

    with pytest.raises(InvalidSignalPlanError):
        controller.decide(
            ControllerContext(
                current_time=2.0,
                active_phase_id="NON_EXISTENT",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )

    ctx_override = ControllerContext(
        current_time=3.0,
        active_phase_id="P2",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_override = controller.decide(ctx_override)
    assert controller.current_phase_index == 1
    assert controller.elapsed_green == 0.0
    assert dec_override.reason == "min_green_hold"

    plan_mismatch = SignalPlan(
        id="mismatch_plan",
        phases=(
            SignalPhase(
                id="PX",
                green_movement_ids=("UNKNOWN_MOV",),
                green_duration=10.0,
            ),
            SignalPhase(
                id="PY",
                green_movement_ids=("N_T",),
                green_duration=10.0,
            ),
        ),
    )
    with pytest.raises(ValidationError):
        MaxPressureController(signal_plan=plan_mismatch, intersection=inter)

    controller.reset()
    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 0.0
