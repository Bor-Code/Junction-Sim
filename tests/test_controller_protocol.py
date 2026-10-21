import pytest
from pydantic import ValidationError as PydanticValidationError

from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import ValidationError


class DummyController:
    def __init__(self) -> None:
        self.reset_count = 0

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if context.is_in_transition:
            return ControllerDecision()
        if context.queue_lengths.get("lane_1", 0) > 5:
            return ControllerDecision(target_phase_id="P2", reason="queue_threshold")
        return ControllerDecision()

    def reset(self) -> None:
        self.reset_count += 1


class IncompleteControllerMissingReset:
    def decide(self, context: ControllerContext) -> ControllerDecision:
        return ControllerDecision()


class IncompleteControllerMissingDecide:
    def reset(self) -> None:
        pass


def test_controller_context_valid() -> None:
    ctx = ControllerContext(
        current_time=12.5,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_1": 3, "lane_2": 0},
    )

    assert ctx.current_time == 12.5
    assert ctx.active_phase_id == "P1"
    assert ctx.signal_state == SignalState.GREEN
    assert not ctx.is_in_transition
    assert ctx.queue_lengths == {"lane_1": 3, "lane_2": 0}


def test_controller_context_immutability() -> None:
    ctx = ControllerContext(
        current_time=0.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )

    attr_time = "current_time"
    with pytest.raises(PydanticValidationError):
        setattr(ctx, attr_time, 1.0)

    with pytest.raises(PydanticValidationError):
        ControllerContext.model_validate(
            {
                "current_time": 0.0,
                "active_phase_id": "P1",
                "signal_state": SignalState.GREEN,
                "is_in_transition": False,
                "queue_lengths": {},
                "extra_field": "invalid",
            }
        )


def test_controller_context_validation_guards() -> None:
    with pytest.raises(PydanticValidationError):
        ControllerContext(
            current_time=-1.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )

    with pytest.raises(ValidationError):
        ControllerContext(
            current_time=0.0,
            active_phase_id="   ",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )

    with pytest.raises(ValidationError):
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"lane_1": -2},
        )

    with pytest.raises(ValidationError):
        ControllerContext(
            current_time=0.0,
            active_phase_id="P1",
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={"  ": 3},
        )


def test_controller_decision_valid_and_defaults() -> None:
    default_decision = ControllerDecision()
    assert default_decision.target_phase_id is None
    assert default_decision.reason is None
    assert not default_decision.should_change_phase

    switch_decision = ControllerDecision(target_phase_id="P2", reason="max_green")
    assert switch_decision.target_phase_id == "P2"
    assert switch_decision.reason == "max_green"
    assert switch_decision.should_change_phase


def test_controller_decision_immutability() -> None:
    dec = ControllerDecision(target_phase_id="P1")

    attr_target = "target_phase_id"
    with pytest.raises(PydanticValidationError):
        setattr(dec, attr_target, "P2")

    with pytest.raises(PydanticValidationError):
        ControllerDecision.model_validate({"extra_param": 123})


def test_controller_decision_validation_guards() -> None:
    with pytest.raises(ValidationError):
        ControllerDecision(target_phase_id="   ")

    with pytest.raises(ValidationError):
        ControllerDecision(reason="   ")


def test_signal_controller_protocol_conformance() -> None:
    controller = DummyController()
    assert isinstance(controller, SignalController)

    assert not isinstance(IncompleteControllerMissingReset(), SignalController)
    assert not isinstance(IncompleteControllerMissingDecide(), SignalController)

    ctx_hold = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_1": 2},
    )
    dec_hold = controller.decide(ctx_hold)
    assert dec_hold.target_phase_id is None
    assert not dec_hold.should_change_phase

    ctx_switch = ControllerContext(
        current_time=11.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_1": 8},
    )
    dec_switch = controller.decide(ctx_switch)
    assert dec_switch.target_phase_id == "P2"
    assert dec_switch.reason == "queue_threshold"
    assert dec_switch.should_change_phase

    ctx_trans = ControllerContext(
        current_time=12.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={"lane_1": 8},
    )
    dec_trans = controller.decide(ctx_trans)
    assert dec_trans.target_phase_id is None

    assert controller.reset_count == 0
    controller.reset()
    assert controller.reset_count == 1
