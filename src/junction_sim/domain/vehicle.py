from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.exceptions import (
    InvalidGeometryError,
    InvalidStateError,
    ValidationError,
)


class Vehicle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    arrival_time: float = Field(ge=0.0)
    departure_time: float | None = Field(default=None)
    target_lane_id: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_vehicle(self) -> "Vehicle":
        if not self.id.strip():
            raise ValidationError("vehicle id cannot be empty or blank")
        if not self.origin.strip():
            raise ValidationError("origin cannot be empty or blank")
        if not self.destination.strip():
            raise ValidationError("destination cannot be empty or blank")
        if self.origin == self.destination:
            raise InvalidGeometryError("origin and destination cannot be identical")
        if self.departure_time is not None and self.departure_time < self.arrival_time:
            raise ValidationError("departure_time cannot be earlier than arrival_time")
        return self

    @property
    def is_completed(self) -> bool:
        return self.departure_time is not None

    def waiting_time(self, current_time: float) -> float:
        if current_time < self.arrival_time:
            raise InvalidStateError("current_time cannot be earlier than arrival_time")
        if self.departure_time is not None:
            return self.departure_time - self.arrival_time
        return current_time - self.arrival_time

    def with_departure(self, departure_time: float) -> "Vehicle":
        if self.departure_time is not None:
            raise InvalidStateError("vehicle has already departed")
        if departure_time < self.arrival_time:
            raise InvalidStateError(
                "departure_time cannot be earlier than arrival_time"
            )
        return self.model_copy(update={"departure_time": departure_time})
