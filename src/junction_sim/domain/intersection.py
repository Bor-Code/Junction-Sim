from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.approach import Approach
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement
from junction_sim.exceptions import InvalidGeometryError, ValidationError


class Intersection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    approaches: tuple[Approach, ...]
    movements: tuple[Movement, ...]
    conflicting_movement_pairs: frozenset[frozenset[str]] = Field(
        default_factory=frozenset
    )

    @model_validator(mode="after")
    def validate_intersection(self) -> "Intersection":
        if not self.id.strip():
            raise ValidationError("intersection id cannot be empty or blank")

        if len(self.approaches) < 2:
            raise ValidationError("intersection must contain at least two approaches")

        approach_ids = [app.id for app in self.approaches]
        if len(approach_ids) != len(set(approach_ids)):
            raise InvalidGeometryError("duplicate approach ids found in intersection")

        approach_directions = [app.direction for app in self.approaches]
        if len(approach_directions) != len(set(approach_directions)):
            raise InvalidGeometryError(
                "duplicate approach directions found in intersection"
            )

        if not self.movements:
            raise ValidationError("intersection must contain at least one movement")

        movement_ids = {m.id for m in self.movements}
        if len(movement_ids) != len(self.movements):
            raise InvalidGeometryError("duplicate movement ids found in intersection")

        approach_id_set = set(approach_ids)
        for m in self.movements:
            if m.origin not in approach_id_set:
                raise InvalidGeometryError(
                    f"movement '{m.id}' origin '{m.origin}' does not match any approach"
                )

        all_lane_ids: set[str] = set()
        for app in self.approaches:
            for lane in app.lanes:
                if lane.id in all_lane_ids:
                    raise InvalidGeometryError(
                        f"duplicate lane id '{lane.id}' across approaches"
                    )
                all_lane_ids.add(lane.id)
                for allowed_m_id in lane.allowed_movement_ids:
                    if allowed_m_id not in movement_ids:
                        raise InvalidGeometryError(
                            f"lane '{lane.id}' allows unknown movement '{allowed_m_id}'"
                        )

        for pair in self.conflicting_movement_pairs:
            if len(pair) != 2:
                raise InvalidGeometryError(
                    "conflicting movement pair must contain exactly two movements"
                )
            for m_id in pair:
                if m_id not in movement_ids:
                    raise InvalidGeometryError(
                        f"unknown movement id '{m_id}' in conflicting movement pairs"
                    )

        return self

    def get_approach(self, approach_id: str) -> Approach:
        for app in self.approaches:
            if app.id == approach_id:
                return app
        raise InvalidGeometryError(
            f"approach '{approach_id}' not found in intersection '{self.id}'"
        )

    def get_movement(self, movement_id: str) -> Movement:
        for m in self.movements:
            if m.id == movement_id:
                return m
        raise InvalidGeometryError(
            f"movement '{movement_id}' not found in intersection '{self.id}'"
        )

    def get_lane(self, lane_id: str) -> Lane:
        for app in self.approaches:
            for lane in app.lanes:
                if lane.id == lane_id:
                    return lane
        raise InvalidGeometryError(
            f"lane '{lane_id}' not found in intersection '{self.id}'"
        )

    def are_conflicting(self, movement_id_a: str, movement_id_b: str) -> bool:
        if movement_id_a == movement_id_b:
            return False
        return (
            frozenset({movement_id_a, movement_id_b}) in self.conflicting_movement_pairs
        )
