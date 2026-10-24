import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import ValidationError


class ReservationStatus(StrEnum):
    GRANTED = "granted"
    REJECTED = "rejected"


class ReservationTile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    grid_x: int
    grid_y: int
    time_index: int


class ReservationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vehicle_id: str = Field(min_length=1)
    movement_id: str = Field(min_length=1)
    arrival_time: float = Field(ge=0.0)
    traversal_duration: float = Field(gt=0.0)
    cells: tuple[tuple[int, int], ...]

    @model_validator(mode="after")
    def validate_cells(self) -> "ReservationRequest":
        if not self.cells:
            raise ValidationError("cells sequence cannot be empty")
        return self


class ReservationRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vehicle_id: str
    movement_id: str
    start_time: float
    end_time: float
    reserved_cells: tuple[tuple[int, int, int], ...]


class ReservationGrid:
    def __init__(
        self,
        cell_size_m: float = 4.0,
        time_step_s: float = 0.5,
        grid_width_m: float = 40.0,
        grid_height_m: float = 40.0,
    ) -> None:
        if cell_size_m <= 0.0 or time_step_s <= 0.0:
            raise ValidationError("cell_size_m and time_step_s must be positive")
        if grid_width_m <= 0.0 or grid_height_m <= 0.0:
            raise ValidationError("grid dimensions must be positive")

        self.cell_size_m = cell_size_m
        self.time_step_s = time_step_s
        self.cols = int(math.ceil(grid_width_m / cell_size_m))
        self.rows = int(math.ceil(grid_height_m / cell_size_m))
        self._table: dict[tuple[int, int, int], str] = {}
        self._records: list[ReservationRecord] = []
        self._granted_count = 0
        self._rejected_count = 0

    @property
    def granted_count(self) -> int:
        return self._granted_count

    @property
    def rejected_count(self) -> int:
        return self._rejected_count

    @property
    def total_reservations(self) -> int:
        return len(self._records)

    def time_to_index(self, time_s: float) -> int:
        return int(math.floor(time_s / self.time_step_s))

    def is_available(self, gx: int, gy: int, t_idx: int) -> bool:
        return (gx, gy, t_idx) not in self._table

    def request_reservation(
        self,
        request: ReservationRequest,
    ) -> ReservationStatus:
        start_t_idx = self.time_to_index(request.arrival_time)
        steps = max(1, int(math.ceil(request.traversal_duration / self.time_step_s)))
        needed_slots: list[tuple[int, int, int]] = []

        for step_offset in range(steps):
            t_idx = start_t_idx + step_offset
            for gx, gy in request.cells:
                if not (0 <= gx < self.cols and 0 <= gy < self.rows):
                    raise ValidationError(
                        f"cell ({gx}, {gy}) outside grid bounds "
                        f"({self.cols}, {self.rows})"
                    )
                if not self.is_available(gx, gy, t_idx):
                    self._rejected_count += 1
                    return ReservationStatus.REJECTED
                needed_slots.append((gx, gy, t_idx))

        for slot in needed_slots:
            self._table[slot] = request.vehicle_id

        record = ReservationRecord(
            vehicle_id=request.vehicle_id,
            movement_id=request.movement_id,
            start_time=request.arrival_time,
            end_time=request.arrival_time + request.traversal_duration,
            reserved_cells=tuple(needed_slots),
        )
        self._records.append(record)
        self._granted_count += 1
        return ReservationStatus.GRANTED

    def clean_expired(self, current_time: float) -> int:
        cur_t_idx = self.time_to_index(current_time)
        to_del = [key for key in self._table if key[2] < cur_t_idx]
        for key in to_del:
            del self._table[key]
        return len(to_del)

    def clear(self) -> None:
        self._table.clear()
        self._records.clear()
        self._granted_count = 0
        self._rejected_count = 0


class ReservationController(SignalController):
    def __init__(
        self,
        signal_plan: SignalPlan,
        intersection: Intersection,
        grid: ReservationGrid | None = None,
        min_green: float = 5.0,
    ) -> None:
        self._signal_plan = signal_plan
        self._intersection = intersection
        self._grid = grid if grid is not None else ReservationGrid()
        self._min_green = min_green
        self._phase_ids = tuple(p.id for p in signal_plan.phases)
        self._last_change_time = 0.0
        self._request_seq = 0

    @property
    def grid(self) -> ReservationGrid:
        return self._grid

    def reset(self) -> None:
        self._grid.clear()
        self._last_change_time = 0.0
        self._request_seq = 0

    def _synthesize_trajectory_cells(
        self, phase_index: int
    ) -> tuple[tuple[int, int], ...]:
        base_x = (phase_index * 2) % self._grid.cols
        base_y = (phase_index * 2) % self._grid.rows
        return ((base_x, base_y), ((base_x + 1) % self._grid.cols, base_y))

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if context.is_in_transition:
            return ControllerDecision(target_phase_id=None, reason="in_transition")

        self._grid.clean_expired(context.current_time)

        time_in_phase = context.current_time - self._last_change_time
        if time_in_phase < self._min_green:
            return ControllerDecision(target_phase_id=None, reason="min_green_enforced")

        candidate_phases: list[tuple[int, str, int]] = []
        for idx, pid in enumerate(self._phase_ids):
            if pid == context.active_phase_id:
                continue
            phase_obj = self._signal_plan.get_phase(pid)
            demand_score = 0
            for mov_id in phase_obj.green_movement_ids:
                demand_score += sum(
                    context.queue_lengths.get(lane.id, 0)
                    for app in self._intersection.approaches
                    for lane in app.lanes
                    if lane.allows_movement(mov_id)
                )
            candidate_phases.append((demand_score, pid, idx))

        candidate_phases.sort(key=lambda item: item[0], reverse=True)

        for score, pid, p_idx in candidate_phases:
            if score <= 0:
                continue

            self._request_seq += 1
            cells = self._synthesize_trajectory_cells(p_idx)
            req = ReservationRequest(
                vehicle_id=f"cav_{self._request_seq}",
                movement_id=pid,
                arrival_time=context.current_time,
                traversal_duration=5.0,
                cells=cells,
            )
            status = self._grid.request_reservation(req)
            if status == ReservationStatus.GRANTED:
                self._last_change_time = context.current_time
                return ControllerDecision(
                    target_phase_id=pid,
                    reason=f"reservation_granted_{pid}",
                )

        return ControllerDecision(
            target_phase_id=None,
            reason="reservation_hold_phase",
        )
