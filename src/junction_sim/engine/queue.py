from collections import deque

from junction_sim.domain.lane import Lane
from junction_sim.domain.vehicle import Vehicle
from junction_sim.exceptions import InvalidStateError, ValidationError


class LaneQueue:
    def __init__(self, lane: Lane) -> None:
        self._lane = lane
        self._vehicles: deque[Vehicle] = deque()
        self._discharge_credit = 0.0

    @property
    def lane(self) -> Lane:
        return self._lane

    @property
    def discharge_credit(self) -> float:
        return self._discharge_credit

    @property
    def length(self) -> int:
        return len(self._vehicles)

    @property
    def is_empty(self) -> bool:
        return len(self._vehicles) == 0

    @property
    def is_full(self) -> bool:
        return len(self._vehicles) >= self._lane.max_capacity

    def peek(self) -> Vehicle | None:
        if not self._vehicles:
            return None
        return self._vehicles[0]

    def enqueue(self, vehicle: Vehicle) -> None:
        if self.is_full:
            raise InvalidStateError(
                f"queue on lane '{self._lane.id}' is full "
                f"(capacity: {self._lane.max_capacity})"
            )
        if (
            vehicle.target_lane_id is not None
            and vehicle.target_lane_id != self._lane.id
        ):
            raise ValidationError(
                f"vehicle target lane '{vehicle.target_lane_id}' "
                f"does not match queue lane '{self._lane.id}'"
            )
        self._vehicles.append(vehicle)

    def discharge(
        self,
        current_time: float,
        step_size: float,
        saturation_flow_rate: float,
    ) -> tuple[Vehicle, ...]:
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")
        if saturation_flow_rate <= 0.0:
            raise ValidationError("saturation_flow_rate must be greater than zero")
        if current_time < 0.0:
            raise ValidationError("current_time cannot be negative")

        if self.is_empty:
            self._discharge_credit = 0.0
            return ()

        self._discharge_credit += saturation_flow_rate * (step_size / 3600.0)
        discharged: list[Vehicle] = []

        while self._discharge_credit >= 1.0 and len(self._vehicles) > 0:
            veh = self._vehicles.popleft()
            departed_veh = veh.with_departure(current_time)
            discharged.append(departed_veh)
            self._discharge_credit -= 1.0

        if self.is_empty:
            self._discharge_credit = 0.0

        return tuple(discharged)

    def reset_credit(self) -> None:
        self._discharge_credit = 0.0
