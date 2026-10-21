from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.exceptions import InvalidSignalPlanError


class SignalPhase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    green_movement_ids: tuple[str, ...]
    green_duration: float = Field(gt=0.0)
    yellow_duration: float = Field(default=3.0, ge=0.0)
    all_red_duration: float = Field(default=2.0, ge=0.0)
    min_green: float = Field(default=5.0, gt=0.0)
    max_green: float = Field(default=60.0, gt=0.0)

    @model_validator(mode="after")
    def validate_phase(self) -> "SignalPhase":
        if not self.id.strip():
            raise InvalidSignalPlanError("phase id cannot be empty or blank")

        if not self.green_movement_ids:
            raise InvalidSignalPlanError(
                "phase must contain at least one green movement"
            )

        for m_id in self.green_movement_ids:
            if not m_id.strip():
                raise InvalidSignalPlanError("movement id cannot be empty or blank")

        if len(self.green_movement_ids) != len(set(self.green_movement_ids)):
            raise InvalidSignalPlanError("duplicate movement ids found in phase")

        if self.max_green < self.min_green:
            raise InvalidSignalPlanError("max_green cannot be less than min_green")

        if self.green_duration < self.min_green:
            raise InvalidSignalPlanError("green_duration cannot be less than min_green")

        if self.green_duration > self.max_green:
            raise InvalidSignalPlanError("green_duration cannot exceed max_green")

        return self

    @property
    def total_duration(self) -> float:
        return self.green_duration + self.yellow_duration + self.all_red_duration


class SignalPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    phases: tuple[SignalPhase, ...]

    @model_validator(mode="after")
    def validate_plan(self) -> "SignalPlan":
        if not self.id.strip():
            raise InvalidSignalPlanError("signal plan id cannot be empty or blank")

        if len(self.phases) < 2:
            raise InvalidSignalPlanError("signal plan must contain at least two phases")

        phase_ids = [p.id for p in self.phases]
        if len(phase_ids) != len(set(phase_ids)):
            raise InvalidSignalPlanError("duplicate phase ids found in signal plan")

        return self

    @property
    def cycle_length(self) -> float:
        return sum(p.total_duration for p in self.phases)

    def get_phase(self, phase_id: str) -> SignalPhase:
        for p in self.phases:
            if p.id == phase_id:
                return p
        raise InvalidSignalPlanError(
            f"phase '{phase_id}' not found in signal plan '{self.id}'"
        )
