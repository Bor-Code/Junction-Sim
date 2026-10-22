from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.exceptions import (
    InvalidSignalPlanError,
    InvalidStateError,
)


class MaxPressureController:
    def __init__(self, signal_plan: SignalPlan, intersection: Intersection) -> None:
        validate_signal_plan_against_intersection(signal_plan, intersection)

        self._signal_plan = signal_plan
        self._intersection = intersection
        self._phase_ids = tuple(p.id for p in signal_plan.phases)

        self._phase_to_lanes: dict[str, tuple[str, ...]] = {}
        for phase in signal_plan.phases:
            lanes: list[str] = []
            for m_id in phase.green_movement_ids:
                mov = intersection.get_movement(m_id)
                approach = intersection.get_approach(mov.origin)
                for lane in approach.get_lanes_for_movement(m_id):
                    lanes.append(lane.id)
            self._phase_to_lanes[phase.id] = tuple(sorted(set(lanes)))

        self._current_phase_index: int = 0
        self._elapsed_green: float = 0.0
        self._last_time: float | None = None
        self._was_in_transition: bool = False

    @property
    def signal_plan(self) -> SignalPlan:
        return self._signal_plan

    @property
    def intersection(self) -> Intersection:
        return self._intersection

    @property
    def current_phase_index(self) -> int:
        return self._current_phase_index

    @property
    def elapsed_green(self) -> float:
        return self._elapsed_green

    def get_phase_pressure(self, phase_id: str, queue_lengths: dict[str, int]) -> int:
        if phase_id not in self._phase_to_lanes:
            raise InvalidSignalPlanError(f"phase '{phase_id}' not found in signal plan")
        lanes = self._phase_to_lanes[phase_id]
        return sum(queue_lengths.get(lid, 0) for lid in lanes)

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
        pressures = {
            pid: self.get_phase_pressure(pid, context.queue_lengths)
            for pid in self._phase_ids
        }
        current_pressure = pressures[current_phase.id]

        best_phase_id = current_phase.id
        highest_alternative_p = current_pressure
        for offset in range(1, len(self._phase_ids)):
            cand_idx = (self._current_phase_index + offset) % len(self._phase_ids)
            cand_id = self._phase_ids[cand_idx]
            if pressures[cand_id] > highest_alternative_p:
                highest_alternative_p = pressures[cand_id]
                best_phase_id = cand_id

        if self._elapsed_green < current_phase.min_green:
            return ControllerDecision(reason="min_green_hold")

        if self._elapsed_green >= current_phase.max_green:
            target_phase_id: str | None = None
            highest_comp_p = 0
            for offset in range(1, len(self._phase_ids)):
                cand_idx = (self._current_phase_index + offset) % len(self._phase_ids)
                cand_id = self._phase_ids[cand_idx]
                if pressures[cand_id] > highest_comp_p:
                    highest_comp_p = pressures[cand_id]
                    target_phase_id = cand_id

            if target_phase_id is not None:
                self._current_phase_index = self._phase_ids.index(target_phase_id)
                self._elapsed_green = 0.0
                return ControllerDecision(
                    target_phase_id=target_phase_id, reason="max_green"
                )
            return ControllerDecision(reason="max_pressure_hold")

        if best_phase_id != current_phase.id:
            self._current_phase_index = self._phase_ids.index(best_phase_id)
            self._elapsed_green = 0.0
            return ControllerDecision(
                target_phase_id=best_phase_id, reason="max_pressure_switch"
            )

        return ControllerDecision(reason="max_pressure_hold")
