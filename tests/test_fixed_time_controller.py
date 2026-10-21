import pytest

from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.protocol import (
    ControllerContext,
    SignalController,
)
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import (
    InvalidSignalPlanError,
    InvalidStateError,
    ValidationError,
)


def create_sample_plan() -> SignalPlan:
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=10.0,
        yellow_duration=3.0,
        all_red_duration=2.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=15.0,
        yellow_duration=3.0,
        all_red_duration=2.0,
    )
    return SignalPlan(id="plan_01", phases=(phase_1, phase_2))


def test_fixed_time_controller_initialization() -> None:
    plan = create_sample_plan()
    controller = FixedTimeController(signal_plan=plan, offset=5.0)

    assert controller.signal_plan == plan
    assert controller.offset == 5.0
    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 0.0
    assert isinstance(controller, SignalController)


def test_fixed_time_controller_negative_offset_raises() -> None:
    plan = create_sample_plan()
    with pytest.raises(ValidationError):
        FixedTimeController(signal_plan=plan, offset=-1.0)


def test_fixed_time_controller_single_cycle_progression() -> None:
    plan = create_sample_plan()
    controller = FixedTimeController(signal_plan=plan)

    ctx_0 = ControllerContext(
        current_time=0.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_0 = controller.decide(ctx_0)
    assert dec_0.target_phase_id is None
    assert dec_0.reason == "green_hold"
    assert controller.elapsed_green == 0.0

    for t in range(1, 10):
        ctx = ControllerContext(
            current_time=float(t),
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
        dec = controller.decide(ctx)
        assert dec.target_phase_id is None
        assert dec.reason == "green_hold"
        assert controller.elapsed_green == float(t)

    ctx_10 = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_10 = controller.decide(ctx_10)
    assert dec_10.target_phase_id == "P2"
    assert dec_10.reason == "fixed_time_split"
    assert controller.elapsed_green == 0.0
    assert controller.current_phase_index == 1

    for t in range(11, 15):
        ctx_trans = ControllerContext(
            current_time=float(t),
            active_phase_id="P1",
            signal_state=SignalState.YELLOW,
            is_in_transition=True,
            queue_lengths={},
        )
        dec_trans = controller.decide(ctx_trans)
        assert dec_trans.target_phase_id is None
        assert dec_trans.reason == "in_transition"

    ctx_p2_onset = ControllerContext(
        current_time=15.0,
        active_phase_id="P2",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_p2_onset = controller.decide(ctx_p2_onset)
    assert dec_p2_onset.target_phase_id is None
    assert dec_p2_onset.reason == "green_hold"
    assert controller.elapsed_green == 0.0

    for t in range(16, 30):
        ctx = ControllerContext(
            current_time=float(t),
            active_phase_id="P2",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
        dec = controller.decide(ctx)
        assert dec.target_phase_id is None
        assert dec.reason == "green_hold"
        assert controller.elapsed_green == float(t - 15)

    ctx_p2_end = ControllerContext(
        current_time=30.0,
        active_phase_id="P2",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_p2_end = controller.decide(ctx_p2_end)
    assert dec_p2_end.target_phase_id == "P1"
    assert dec_p2_end.reason == "fixed_time_split"
    assert controller.current_phase_index == 0


def test_fixed_time_controller_reset() -> None:
    plan = create_sample_plan()
    controller = FixedTimeController(signal_plan=plan)

    for t in range(5):
        controller.decide(
            ControllerContext(
                current_time=float(t),
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )

    assert controller.elapsed_green == 4.0
    controller.reset()

    assert controller.current_phase_index == 0
    assert controller.elapsed_green == 0.0

    dec = controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )
    assert dec.reason == "green_hold"


def test_fixed_time_controller_external_phase_override() -> None:
    plan = create_sample_plan()
    controller = FixedTimeController(signal_plan=plan)

    controller.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )
    assert controller.current_phase_index == 0

    controller.decide(
        ControllerContext(
            current_time=1.0,
            active_phase_id="P2",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )
    assert controller.current_phase_index == 1
    assert controller.elapsed_green == 0.0


def test_fixed_time_controller_unknown_phase_raises() -> None:
    plan = create_sample_plan()
    controller = FixedTimeController(signal_plan=plan)

    with pytest.raises(InvalidSignalPlanError):
        controller.decide(
            ControllerContext(
                current_time=0.0,
                active_phase_id="UNKNOWN_PHASE",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )


def test_fixed_time_controller_time_decrease_raises() -> None:
    plan = create_sample_plan()
    controller = FixedTimeController(signal_plan=plan)

    controller.decide(
        ControllerContext(
            current_time=10.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )

    with pytest.raises(InvalidStateError):
        controller.decide(
            ControllerContext(
                current_time=5.0,
                active_phase_id="P1",
                signal_state=SignalState.GREEN,
                is_in_transition=False,
                queue_lengths={},
            )
        )
