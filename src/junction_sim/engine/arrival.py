from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.rng import TrafficRNG
from junction_sim.exceptions import InvalidGeometryError, ValidationError


class DemandProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    movement_id: str = Field(min_length=1)
    flow_rate_vph: float = Field(ge=0.0)

    @model_validator(mode="after")
    def validate_demand(self) -> "DemandProfile":
        if not self.movement_id.strip():
            raise ValidationError("movement id cannot be empty or blank")
        return self


class ArrivalGenerator:
    def __init__(
        self,
        intersection: Intersection,
        demands: tuple[DemandProfile, ...],
        rng: TrafficRNG,
    ) -> None:
        self._intersection = intersection
        self._rng = rng
        self._vehicle_counter = 0

        demand_movement_ids = [d.movement_id for d in demands]
        if len(demand_movement_ids) != len(set(demand_movement_ids)):
            raise ValidationError("duplicate demand profiles found for movement")

        intersection_movement_ids = {m.id for m in intersection.movements}
        self._lanes_per_movement: dict[str, tuple[Lane, ...]] = {}

        for d in demands:
            if d.movement_id not in intersection_movement_ids:
                raise InvalidGeometryError(
                    f"unknown movement id '{d.movement_id}' in demand profile"
                )
            movement = intersection.get_movement(d.movement_id)
            approach = intersection.get_approach(movement.origin)
            lanes = approach.get_lanes_for_movement(d.movement_id)
            if not lanes:
                raise InvalidGeometryError(
                    f"no lane allows movement '{d.movement_id}' "
                    f"in approach '{approach.id}'"
                )
            self._lanes_per_movement[d.movement_id] = lanes

        self._demands = demands

    @property
    def demands(self) -> tuple[DemandProfile, ...]:
        return self._demands

    @property
    def vehicle_counter(self) -> int:
        return self._vehicle_counter

    def generate_arrivals(
        self, current_time: float, step_size: float
    ) -> tuple[Vehicle, ...]:
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")
        if current_time < 0.0:
            raise ValidationError("current_time cannot be negative")

        new_vehicles: list[Vehicle] = []
        for demand in self._demands:
            if demand.flow_rate_vph == 0.0:
                continue

            lam = demand.flow_rate_vph * (step_size / 3600.0)
            count = self._rng.poisson(lam)
            movement = self._intersection.get_movement(demand.movement_id)
            candidate_lanes = self._lanes_per_movement[demand.movement_id]

            for _ in range(count):
                self._vehicle_counter += 1
                vehicle_id = f"{demand.movement_id}_{self._vehicle_counter}"
                chosen_lane = (
                    candidate_lanes[0]
                    if len(candidate_lanes) == 1
                    else self._rng.choice(candidate_lanes)
                )
                vehicle = Vehicle(
                    id=vehicle_id,
                    origin=movement.origin,
                    destination=movement.destination,
                    arrival_time=current_time,
                    target_lane_id=chosen_lane.id,
                )
                new_vehicles.append(vehicle)

        return tuple(new_vehicles)
