from pydantic import BaseModel, ConfigDict, Field

from junction_sim.exceptions import InvalidStateError, ValidationError


class SimulationClock(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    start_time: float = Field(default=0.0, ge=0.0)
    step_size: float = Field(default=1.0, gt=0.0)
    step_count: int = Field(default=0, ge=0)

    @property
    def current_time(self) -> float:
        return round(self.start_time + (self.step_count * self.step_size), 9)

    def tick(self) -> "SimulationClock":
        return self.advance(1)

    def advance(self, steps: int = 1) -> "SimulationClock":
        if steps <= 0:
            raise InvalidStateError("steps must be greater than zero")
        return self.model_copy(update={"step_count": self.step_count + steps})

    def is_finished(self, duration: float) -> bool:
        if duration < 0.0:
            raise ValidationError("duration cannot be negative")
        return self.current_time >= round(self.start_time + duration, 9)
