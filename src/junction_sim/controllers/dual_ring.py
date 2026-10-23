from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
)
from junction_sim.domain.dual_ring import DualRingStructure
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.exceptions import InvalidSignalPlanError, InvalidStateError


class DualRingController:
    def __init__(
        self,
        dual_ring: DualRingStructure,
        signal_plan: SignalPlan,
        intersection: Intersection,
    ) -> None:
        validate_signal_plan_against_intersection(signal_plan, intersection)

        self._dual_ring = dual_ring
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
    def dual_ring(self) -> DualRingStructure:
        return self._dual_ring

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

    def reset(self) -> None:
        self._current_phase_index = 0
        self._elapsed_green = 0.0
        self._last_time = None
        self._was_in_transition = False

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if self._last_time is not None and context.current_time < self._last_time:
            raise InvalidStateError("simulation time cannot go backwards")

        if context.active_phase_id not in self._phase_ids:
            raise InvalidSignalPlanError(
                f"unknown active phase '{context.active_phase_id}'"
            )

        if context.is_in_transition:
            self._was_in_transition = True
            self._last_time = context.current_time
            return ControllerDecision(reason="signal in transition")

        if self._was_in_transition:
            self._was_in_transition = False
            self._elapsed_green = 0.0
            self._current_phase_index = self._phase_ids.index(context.active_phase_id)
        elif self._last_time is not None:
            self._elapsed_green += context.current_time - self._last_time

        self._last_time = context.current_time

        current_phase = self._signal_plan.phases[self._current_phase_index]
        if self._elapsed_green < current_phase.min_green:
            return ControllerDecision(
                reason=f"min_green {current_phase.min_green:.1f}s not reached"
            )

        next_index = (self._current_phase_index + 1) % len(self._phase_ids)
        target_phase = self._phase_ids[next_index]

        if self._elapsed_green >= current_phase.max_green:
            self._current_phase_index = next_index
            self._elapsed_green = 0.0
            return ControllerDecision(
                target_phase_id=target_phase,
                reason=f"max_green {current_phase.max_green:.1f}s reached",
            )

        current_lanes = self._phase_to_lanes[current_phase.id]
        active_queue = sum(context.queue_lengths.get(lid, 0) for lid in current_lanes)

        all_lanes = set(context.queue_lengths.keys())
        competing_lanes = all_lanes - set(current_lanes)
        competing_queue = sum(
            context.queue_lengths.get(lid, 0) for lid in competing_lanes
        )

        if active_queue == 0 and competing_queue > 0:
            self._current_phase_index = next_index
            self._elapsed_green = 0.0
            return ControllerDecision(
                target_phase_id=target_phase,
                reason="gap out on active phase",
            )

        return ControllerDecision(reason="holding dual-ring phase green")
