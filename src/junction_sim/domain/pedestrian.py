from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.exceptions import ValidationError


class Pedestrian(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    crosswalk_id: str = Field(min_length=1)
    arrival_time: float = Field(ge=0.0)
    crossing_start_time: float | None = Field(default=None, ge=0.0)
    crossing_completion_time: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_pedestrian(self) -> "Pedestrian":
        if not self.id.strip():
            raise ValidationError("pedestrian id cannot be empty or blank")
        if not self.crosswalk_id.strip():
            raise ValidationError("crosswalk_id cannot be empty or blank")
        if (
            self.crossing_start_time is not None
            and self.crossing_start_time < self.arrival_time
        ):
            raise ValidationError(
                "crossing_start_time cannot be earlier than arrival_time"
            )
        if (
            self.crossing_completion_time is not None
            and self.crossing_start_time is None
        ):
            raise ValidationError(
                "crossing_start_time must be set if crossing_completion_time is set"
            )
        if (
            self.crossing_completion_time is not None
            and self.crossing_start_time is not None
            and self.crossing_completion_time < self.crossing_start_time
        ):
            raise ValidationError(
                "crossing_completion_time cannot be earlier than crossing_start_time"
            )
        return self

    def waiting_time(self, current_time: float) -> float:
        if self.crossing_start_time is not None:
            return round(self.crossing_start_time - self.arrival_time, 3)
        if current_time < self.arrival_time:
            raise ValidationError("current_time cannot be earlier than arrival_time")
        return round(current_time - self.arrival_time, 3)
