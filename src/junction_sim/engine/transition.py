from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.signal import SignalPhase
from junction_sim.exceptions import InvalidStateError, ValidationError


class SignalState(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    ALL_RED = "all_red"


class PhaseTracker(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_phase_id: str = Field(min_length=1)
    state: SignalState = Field(default=SignalState.GREEN)
    elapsed_in_state: float = Field(default=0.0, ge=0.0)
    target_phase_id: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_tracker(self) -> "PhaseTracker":
        if not self.current_phase_id.strip():
            raise ValidationError("current_phase_id cannot be empty or blank")

        if self.target_phase_id is not None and not self.target_phase_id.strip():
            raise ValidationError("target_phase_id cannot be empty or blank")

        if (
            self.state in (SignalState.YELLOW, SignalState.ALL_RED)
            and self.target_phase_id is None
        ):
            raise InvalidStateError(
                "target_phase_id must be provided when in transition state"
            )

        if self.state == SignalState.GREEN and self.target_phase_id is not None:
            raise InvalidStateError("target_phase_id must be None when in green state")

        return self

    @property
    def is_green(self) -> bool:
        return self.state == SignalState.GREEN

    @property
    def is_yellow(self) -> bool:
        return self.state == SignalState.YELLOW

    @property
    def is_all_red(self) -> bool:
        return self.state == SignalState.ALL_RED

    @property
    def is_in_transition(self) -> bool:
        return self.state != SignalState.GREEN

    @property
    def can_discharge(self) -> bool:
        return self.state == SignalState.GREEN

    def request_phase_change(self, target_phase_id: str) -> "PhaseTracker":
        if not target_phase_id.strip():
            raise ValidationError("target_phase_id cannot be empty or blank")

        if self.is_in_transition:
            raise InvalidStateError("cannot change phase while already in transition")

        if target_phase_id == self.current_phase_id:
            return self

        return self.model_copy(
            update={
                "state": SignalState.YELLOW,
                "elapsed_in_state": 0.0,
                "target_phase_id": target_phase_id,
            }
        )

    def step(self, step_size: float, current_phase: SignalPhase) -> "PhaseTracker":
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")
        if current_phase.id != self.current_phase_id:
            raise ValidationError(
                f"current_phase id '{current_phase.id}' "
                f"does not match tracker phase '{self.current_phase_id}'"
            )

        new_elapsed = round(self.elapsed_in_state + step_size, 9)

        if self.state == SignalState.GREEN:
            return self.model_copy(update={"elapsed_in_state": new_elapsed})

        if self.state == SignalState.YELLOW:
            if new_elapsed >= current_phase.yellow_duration:
                if current_phase.all_red_duration > 0.0:
                    return self.model_copy(
                        update={
                            "state": SignalState.ALL_RED,
                            "elapsed_in_state": 0.0,
                        }
                    )
                assert self.target_phase_id is not None
                return self.model_copy(
                    update={
                        "current_phase_id": self.target_phase_id,
                        "state": SignalState.GREEN,
                        "elapsed_in_state": 0.0,
                        "target_phase_id": None,
                    }
                )
            return self.model_copy(update={"elapsed_in_state": new_elapsed})

        if new_elapsed >= current_phase.all_red_duration:
            assert self.target_phase_id is not None
            return self.model_copy(
                update={
                    "current_phase_id": self.target_phase_id,
                    "state": SignalState.GREEN,
                    "elapsed_in_state": 0.0,
                    "target_phase_id": None,
                }
            )
        return self.model_copy(update={"elapsed_in_state": new_elapsed})
