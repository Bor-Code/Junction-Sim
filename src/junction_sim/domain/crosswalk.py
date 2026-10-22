from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.exceptions import ValidationError


class PedestrianSignalState(StrEnum):
    DONT_WALK = "dont_walk"
    WALK = "walk"
    FLASHING_DONT_WALK = "flashing_dont_walk"


class Crosswalk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    approach_id: str = Field(min_length=1)
    length_meters: float = Field(default=12.0, gt=0.0)
    pedestrian_speed_mps: float = Field(default=1.2, gt=0.0)
    walk_duration: float = Field(default=7.0, ge=4.0)
    clearance_duration: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_crosswalk(self) -> "Crosswalk":
        if not self.id.strip():
            raise ValidationError("crosswalk id cannot be empty or blank")
        if not self.approach_id.strip():
            raise ValidationError("crosswalk approach_id cannot be empty or blank")
        return self

    @property
    def effective_clearance_duration(self) -> float:
        if self.clearance_duration is not None:
            return self.clearance_duration
        return round(self.length_meters / self.pedestrian_speed_mps, 1)

    @property
    def total_pedestrian_time(self) -> float:
        return round(self.walk_duration + self.effective_clearance_duration, 1)

    def get_signal_state(
        self, elapsed_in_phase: float, is_phase_green: bool
    ) -> PedestrianSignalState:
        if not is_phase_green:
            return PedestrianSignalState.DONT_WALK
        if elapsed_in_phase < self.walk_duration:
            return PedestrianSignalState.WALK
        if elapsed_in_phase < self.total_pedestrian_time:
            return PedestrianSignalState.FLASHING_DONT_WALK
        return PedestrianSignalState.DONT_WALK
