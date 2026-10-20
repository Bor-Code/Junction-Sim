from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.exceptions import ValidationError


class Lane(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    approach_id: str = Field(min_length=1)
    allowed_movement_ids: tuple[str, ...]
    length_meters: float = Field(default=150.0, gt=0.0)
    max_capacity: int = Field(default=20, gt=0)
    speed_limit_mps: float = Field(default=13.89, gt=0.0)

    @model_validator(mode="after")
    def validate_lane(self) -> "Lane":
        if not self.id.strip():
            raise ValidationError("lane id cannot be empty or blank")
        if not self.approach_id.strip():
            raise ValidationError("approach id cannot be empty or blank")
        if not self.allowed_movement_ids:
            raise ValidationError("lane must allow at least one movement")
        for m_id in self.allowed_movement_ids:
            if not m_id.strip():
                raise ValidationError("movement id cannot be empty or blank")
        if len(self.allowed_movement_ids) != len(set(self.allowed_movement_ids)):
            raise ValidationError("duplicate allowed movement ids found on lane")
        return self

    def allows_movement(self, movement_id: str) -> bool:
        return movement_id in self.allowed_movement_ids
