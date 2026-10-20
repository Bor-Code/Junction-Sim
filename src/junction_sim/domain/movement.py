from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.exceptions import InvalidGeometryError, ValidationError


class TurnType(StrEnum):
    LEFT = "left"
    THROUGH = "through"
    RIGHT = "right"
    U_TURN = "u_turn"


class Movement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    turn_type: TurnType
    saturation_flow_rate: float = Field(default=1800.0, gt=0.0)

    @model_validator(mode="after")
    def validate_movement(self) -> "Movement":
        if not self.id.strip():
            raise ValidationError("movement id cannot be empty or blank")
        if not self.origin.strip():
            raise ValidationError("origin cannot be empty or blank")
        if not self.destination.strip():
            raise ValidationError("destination cannot be empty or blank")
        if self.turn_type != TurnType.U_TURN and self.origin == self.destination:
            raise InvalidGeometryError(
                "origin and destination cannot be identical unless turn_type is u_turn"
            )
        if self.turn_type == TurnType.U_TURN and self.origin != self.destination:
            raise InvalidGeometryError(
                "origin and destination must be identical for u_turn"
            )
        return self

    @property
    def discharge_rate_per_second(self) -> float:
        return self.saturation_flow_rate / 3600.0
