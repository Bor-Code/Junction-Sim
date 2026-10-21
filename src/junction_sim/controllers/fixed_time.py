from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
)
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import (
    InvalidSignalPlanError,
    InvalidStateError,
    ValidationError,
)


class FixedTimeController:
    def __init__(self, signal_plan: SignalPlan, offset: float = 0.0) -> None:
        if offset < 0.0:
            raise ValidationError("offset must be non-negative")

        self._signal_plan = signal_plan
        self._offset = offset
        self._phase_ids = tuple(p.id for p in signal_plan.phases)
        self._current_phase_index: int = 0
        self._elapsed_green: float = 0.0
        self._last_time: float | None = None
        self._was_in_transition: bool = False

    @property
    def signal_plan(self) -> SignalPlan:
        return self._signal_plan

    @property
    def offset(self) -> float:
        return self._offset

    @property
    def current_phase_index(self) -> int:
        return self._current_phase_index

    @property
    def elapsed_green(self) -> float:
        return self._elapsed_green

    def reset(self) -> None:
        self._current_phase_index = 0
        self._elapsed_green = 0.0
        self._last_time = None
        self._was_in_transition = False

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if self._last_time is not None and context.current_time < self._last_time:
            raise InvalidStateError("current_time cannot decrease without reset")

        if self._last_time is None:
            dt = 0.0
        else:
            dt = round(context.current_time - self._last_time, 9)
        self._last_time = context.current_time

        if context.is_in_transition:
            self._was_in_transition = True
            return ControllerDecision(reason="in_transition")

        if context.active_phase_id not in self._phase_ids:
            raise InvalidSignalPlanError(
                f"active phase '{context.active_phase_id}' not found in signal plan"
            )

        expected_phase_id = self._phase_ids[self._current_phase_index]
        if context.active_phase_id != expected_phase_id:
            self._current_phase_index = self._phase_ids.index(context.active_phase_id)
            self._elapsed_green = 0.0
            self._was_in_transition = False
        elif self._was_in_transition:
            self._elapsed_green = 0.0
            self._was_in_transition = False
        else:
            self._elapsed_green = round(self._elapsed_green + dt, 9)

        current_phase = self._signal_plan.phases[self._current_phase_index]
        if self._elapsed_green >= current_phase.green_duration:
            next_index = (self._current_phase_index + 1) % len(self._phase_ids)
            target_phase_id = self._phase_ids[next_index]
            self._current_phase_index = next_index
            self._elapsed_green = 0.0
            return ControllerDecision(
                target_phase_id=target_phase_id, reason="fixed_time_split"
            )

        return ControllerDecision(reason="green_hold")
