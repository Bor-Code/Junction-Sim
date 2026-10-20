from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.direction import Direction
from junction_sim.domain.lane import Lane
from junction_sim.exceptions import InvalidGeometryError, ValidationError


class Approach(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    direction: Direction
    lanes: tuple[Lane, ...]

    @model_validator(mode="after")
    def validate_approach(self) -> "Approach":
        if not self.id.strip():
            raise ValidationError("approach id cannot be empty or blank")
        if not self.lanes:
            raise ValidationError("approach must contain at least one lane")
        lane_ids = [lane.id for lane in self.lanes]
        if len(lane_ids) != len(set(lane_ids)):
            raise InvalidGeometryError("duplicate lane ids found in approach")
        for lane in self.lanes:
            if lane.approach_id != self.id:
                raise InvalidGeometryError(
                    f"lane {lane.id} approach_id '{lane.approach_id}' "
                    f"does not match approach id '{self.id}'"
                )
        return self

    def get_lane(self, lane_id: str) -> Lane:
        for lane in self.lanes:
            if lane.id == lane_id:
                return lane
        raise InvalidGeometryError(
            f"lane '{lane_id}' not found in approach '{self.id}'"
        )

    def get_lanes_for_movement(self, movement_id: str) -> tuple[Lane, ...]:
        return tuple(lane for lane in self.lanes if lane.allows_movement(movement_id))
