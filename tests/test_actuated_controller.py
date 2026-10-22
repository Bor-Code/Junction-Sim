import pytest

from junction_sim.controllers.actuated import ActuatedController
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
        id="act_int",
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
    signal_plan = SignalPlan(id="act_plan", phases=(phase_1, phase_2))

    return intersection, signal_plan


def test_actuated_controller_initialization() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    assert controller.signal_plan == plan
    assert controller.intersection == inter
    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 0.0
    assert isinstance(controller, SignalController)


def test_actuated_controller_min_green_enforcement() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    ctx_0 = ControllerContext(
        current_time=0.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 0, "lane_s_0": 0, "lane_e_0": 5, "lane_w_0": 5},
    )
    dec_0 = controller.decide(ctx_0)
    assert dec_0.target_phase_id is None
    assert dec_0.reason == "min_green_hold"

    for t in (1.0, 2.0, 3.0, 4.0):
        ctx = ControllerContext(
            current_time=t,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 0, "lane_s_0": 0, "lane_e_0": 5, "lane_w_0": 5},
        )
        dec = controller.decide(ctx)
        assert dec.target_phase_id is None
        assert dec.reason == "min_green_hold"


def test_actuated_controller_gap_out() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    for t in range(5):
        controller.decide(
            ControllerContext(
                current_time=float(t),
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={"lane_n_0": 2, "lane_e_0": 3},
            )
        )

    ctx_gap = ControllerContext(
        current_time=5.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 0, "lane_s_0": 0, "lane_e_0": 3, "lane_w_0": 0},
    )
    dec_gap = controller.decide(ctx_gap)
    assert dec_gap.target_phase_id == "P2"
    assert dec_gap.reason == "gap_out"
    assert controller.current_phase_index == 1
    assert controller.elapsed_green == 0.0


def test_actuated_controller_green_extension() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    for t in range(6):
        controller.decide(
            ControllerContext(
                current_time=float(t),
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={"lane_n_0": 5, "lane_e_0": 2},
            )
        )

    ctx_ext = ControllerContext(
        current_time=6.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 3, "lane_s_0": 0, "lane_e_0": 2, "lane_w_0": 0},
    )
    dec_ext = controller.decide(ctx_ext)
    assert dec_ext.target_phase_id is None
    assert dec_ext.reason == "green_extension"
    assert controller.current_phase_index == 0


def test_actuated_controller_max_green() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    for t in range(30):
        controller.decide(
            ControllerContext(
                current_time=float(t),
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={"lane_n_0": 5, "lane_e_0": 3},
            )
        )

    ctx_max = ControllerContext(
        current_time=30.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 5, "lane_e_0": 3},
    )
    dec_max = controller.decide(ctx_max)
    assert dec_max.target_phase_id == "P2"
    assert dec_max.reason == "max_green"
    assert controller.current_phase_index == 1


def test_actuated_controller_rest_in_green_when_no_calls() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    for t in range(6):
        controller.decide(
            ControllerContext(
                current_time=float(t),
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={"lane_n_0": 0, "lane_e_0": 0},
            )
        )

    ctx_rest = ControllerContext(
        current_time=6.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 0, "lane_s_0": 0, "lane_e_0": 0, "lane_w_0": 0},
    )
    dec_rest = controller.decide(ctx_rest)
    assert dec_rest.target_phase_id is None
    assert dec_rest.reason == "rest_in_green"

    for t in range(7, 30):
        controller.decide(
            ControllerContext(
                current_time=float(t),
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )

    ctx_max_rest = ControllerContext(
        current_time=30.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_max_rest = controller.decide(ctx_max_rest)
    assert dec_max_rest.target_phase_id is None
    assert dec_max_rest.reason == "rest_in_green"


def test_actuated_controller_transition_and_reset() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_n_0": 5},
        )
    )

    ctx_trans = ControllerContext(
        current_time=1.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={"lane_n_0": 5},
    )
    dec_trans = controller.decide(ctx_trans)
    assert dec_trans.target_phase_id is None
    assert dec_trans.reason == "in_transition"

    ctx_green = ControllerContext(
        current_time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 5},
    )
    dec_green = controller.decide(ctx_green)
    assert dec_green.reason == "min_green_hold"
    assert controller.elapsed_green == 0.0

    controller.reset()
    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 0.0


def test_actuated_controller_guards_and_external_override() -> None:
    inter, plan = create_sample_setup()
    controller = ActuatedController(signal_plan=plan, intersection=inter)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )

    with pytest.raises(InvalidSignalPlanError):
        controller.decide(
            ControllerContext(
                current_time=1.0,
                active_phase_id="INVALID_PHASE",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )

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

    ctx_override = ControllerContext(
        current_time=2.0,
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
        ActuatedController(signal_plan=plan_mismatch, intersection=inter)
