from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.signal import SignalState
from junction_sim.exceptions import ValidationError


class ControllerContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_time: float = Field(ge=0.0)
    active_phase_id: str = Field(min_length=1)
    signal_state: SignalState
    is_in_transition: bool
    queue_lengths: dict[str, int]

    @model_validator(mode="after")
    def validate_context(self) -> "ControllerContext":
        if not self.active_phase_id.strip():
            raise ValidationError("active_phase_id cannot be empty or blank")

        for lane_id, length in self.queue_lengths.items():
            if not lane_id.strip():
                raise ValidationError("lane_id in queue_lengths cannot be blank")
            if length < 0:
                raise ValidationError(
                    f"queue length for lane '{lane_id}' cannot be negative: {length}"
                )

        return self


class ControllerDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_phase_id: str | None = Field(default=None)
    reason: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_decision(self) -> "ControllerDecision":
        if self.target_phase_id is not None and not self.target_phase_id.strip():
            raise ValidationError("target_phase_id cannot be empty or blank")

        if self.reason is not None and not self.reason.strip():
            raise ValidationError("reason cannot be empty or blank")

        return self

    @property
    def should_change_phase(self) -> bool:
        return self.target_phase_id is not None


@runtime_checkable
class SignalController(Protocol):
    def decide(self, context: ControllerContext) -> ControllerDecision: ...

    def reset(self) -> None: ...
