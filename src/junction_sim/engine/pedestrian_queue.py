from collections import deque

from junction_sim.domain.crosswalk import Crosswalk
from junction_sim.domain.pedestrian import Pedestrian
from junction_sim.exceptions import InvalidStateError, ValidationError


class PedestrianQueue:
    def __init__(self, crosswalk: Crosswalk, max_capacity: int = 100) -> None:
        if max_capacity <= 0:
            raise ValidationError("max_capacity must be greater than zero")
        self._crosswalk = crosswalk
        self._max_capacity = max_capacity
        self._pedestrians: deque[Pedestrian] = deque()

    @property
    def crosswalk(self) -> Crosswalk:
        return self._crosswalk

    @property
    def max_capacity(self) -> int:
        return self._max_capacity

    @property
    def length(self) -> int:
        return len(self._pedestrians)

    @property
    def is_empty(self) -> bool:
        return len(self._pedestrians) == 0

    @property
    def is_full(self) -> bool:
        return len(self._pedestrians) >= self._max_capacity

    def peek(self) -> Pedestrian | None:
        if not self._pedestrians:
            return None
        return self._pedestrians[0]

    def enqueue(self, pedestrian: Pedestrian) -> None:
        if self.is_full:
            raise InvalidStateError(
                f"pedestrian queue on crosswalk '{self._crosswalk.id}' is full "
                f"(capacity: {self._max_capacity})"
            )
        if pedestrian.crosswalk_id != self._crosswalk.id:
            raise ValidationError(
                f"pedestrian crosswalk '{pedestrian.crosswalk_id}' "
                f"does not match queue crosswalk '{self._crosswalk.id}'"
            )
        self._pedestrians.append(pedestrian)

    def discharge(
        self, current_time: float, max_count: int | None = None
    ) -> tuple[Pedestrian, ...]:
        if current_time < 0.0:
            raise ValidationError("current_time cannot be negative")

        count = (
            len(self._pedestrians)
            if max_count is None
            else min(len(self._pedestrians), max(0, max_count))
        )
        discharged: list[Pedestrian] = []
        completion_time = round(
            current_time + self._crosswalk.effective_clearance_duration, 3
        )
        for _ in range(count):
            ped = self._pedestrians.popleft()
            updated = ped.model_copy(
                update={
                    "crossing_start_time": current_time,
                    "crossing_completion_time": completion_time,
                }
            )
            discharged.append(updated)

        return tuple(discharged)
