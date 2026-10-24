from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import ValidationError


class CorridorNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intersection_id: str
    distance_from_origin_m: float = Field(ge=0.0)
    cycle_length: float = Field(gt=0.0)
    offset_seconds: float = Field(default=0.0, ge=0.0)
    coordinated_phase_id: str = "P1"


def compute_green_wave_offsets(
    distances_m: Sequence[float],
    progression_speed_mps: float = 13.89,
    cycle_length: float = 60.0,
) -> tuple[float, ...]:
    if progression_speed_mps <= 0.0:
        raise ValidationError("progression_speed_mps must be positive")
    if cycle_length <= 0.0:
        raise ValidationError("cycle_length must be positive")

    offsets: list[float] = []
    for d in distances_m:
        if d < 0.0:
            raise ValidationError("distance cannot be negative")
        travel_time = d / progression_speed_mps
        offset = round(travel_time % cycle_length, 3)
        offsets.append(offset)
    return tuple(offsets)


def compute_progression_bandwidth(
    green_durations: Sequence[float],
    offsets: Sequence[float],
    travel_times: Sequence[float],
    cycle_length: float = 60.0,
) -> float:
    if not green_durations:
        return 0.0
    if len(green_durations) != len(offsets) or len(offsets) != len(travel_times):
        raise ValidationError(
            "lengths of green_durations, offsets, and travel_times must match"
        )
    if cycle_length <= 0.0:
        raise ValidationError("cycle_length must be positive")

    arrival_windows: list[tuple[float, float]] = []
    for g, off, t in zip(green_durations, offsets, travel_times, strict=True):
        if g <= 0.0:
            return 0.0
        green_start = (off - t) % cycle_length
        green_end = green_start + min(g, cycle_length)
        arrival_windows.append((green_start, green_end))

    latest_start = max(w[0] for w in arrival_windows)
    earliest_end = min(w[1] for w in arrival_windows)
    bandwidth = max(0.0, earliest_end - latest_start)
    return round(bandwidth, 3)


class CoordinatedSignalController(SignalController):
    def __init__(
        self,
        signal_plan: SignalPlan,
        cycle_length: float = 60.0,
        offset: float = 0.0,
        coordinated_phase_id: str = "P1",
    ) -> None:
        if cycle_length <= 0.0:
            raise ValidationError("cycle_length must be positive")
        if offset < 0.0:
            raise ValidationError("offset cannot be negative")

        phase_ids = [p.id for p in signal_plan.phases]
        if coordinated_phase_id not in phase_ids:
            raise ValidationError(
                f"coordinated_phase_id '{coordinated_phase_id}' "
                "not found in signal plan"
            )

        self._signal_plan = signal_plan
        self._cycle_length = cycle_length
        self._offset = offset % cycle_length
        self._coordinated_phase_id = coordinated_phase_id

        coord_phase = signal_plan.get_phase(coordinated_phase_id)
        self._coord_green = coord_phase.green_duration

        other_phases = [pid for pid in phase_ids if pid != coordinated_phase_id]
        self._cross_phase_id = other_phases[0]
        self._last_phase_id: str | None = None

    @property
    def cycle_length(self) -> float:
        return self._cycle_length

    @property
    def offset(self) -> float:
        return self._offset

    @property
    def coordinated_phase_id(self) -> str:
        return self._coordinated_phase_id

    def reset(self) -> None:
        self._last_phase_id = None

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if context.is_in_transition:
            return ControllerDecision(target_phase_id=None, reason="in_transition")

        t = context.current_time
        cycle_pos = (t - self._offset) % self._cycle_length

        if cycle_pos < self._coord_green:
            desired_phase = self._coordinated_phase_id
            reason = "green_wave_coordinated_progression"
        else:
            desired_phase = self._cross_phase_id
            reason = "cross_street_allocation"

        if desired_phase != context.active_phase_id:
            self._last_phase_id = desired_phase
            return ControllerDecision(target_phase_id=desired_phase, reason=reason)

        return ControllerDecision(target_phase_id=None, reason="holding_phase")
