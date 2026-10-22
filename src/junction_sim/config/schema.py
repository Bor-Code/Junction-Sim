from pydantic import BaseModel, ConfigDict, Field

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.engine.arrival import DemandProfile
from junction_sim.exceptions import ConfigurationError


class LaneConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    approach_id: str
    allowed_movement_ids: list[str] = Field(min_length=1)
    max_capacity: int = Field(default=50, ge=1)

    def build_domain(self) -> Lane:
        return Lane(
            id=self.id,
            approach_id=self.approach_id,
            allowed_movement_ids=tuple(self.allowed_movement_ids),
            max_capacity=self.max_capacity,
        )


class ApproachConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    direction: Direction
    lanes: list[LaneConfig] = Field(min_length=1)

    def build_domain(self) -> Approach:
        return Approach(
            id=self.id,
            direction=self.direction,
            lanes=tuple(lane.build_domain() for lane in self.lanes),
        )


class MovementConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    origin: str
    destination: str
    turn_type: TurnType
    saturation_flow_rate: float = Field(default=1800.0, gt=0.0)

    def build_domain(self) -> Movement:
        return Movement(
            id=self.id,
            origin=self.origin,
            destination=self.destination,
            turn_type=self.turn_type,
            saturation_flow_rate=self.saturation_flow_rate,
        )


class IntersectionConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    approaches: list[ApproachConfig] = Field(min_length=1)
    movements: list[MovementConfig] = Field(min_length=1)
    conflicting_movement_pairs: list[list[str]] = Field(default_factory=list)

    def build_domain(self) -> Intersection:
        conflicts = frozenset(
            frozenset(pair) for pair in self.conflicting_movement_pairs
        )
        return Intersection(
            id=self.id,
            approaches=tuple(a.build_domain() for a in self.approaches),
            movements=tuple(m.build_domain() for m in self.movements),
            conflicting_movement_pairs=conflicts,
        )


class SignalPhaseConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    green_movement_ids: list[str] = Field(min_length=1)
    green_duration: float = Field(gt=0.0)
    yellow_duration: float = Field(default=3.0, ge=0.0)
    all_red_duration: float = Field(default=1.0, ge=0.0)
    min_green: float = Field(default=5.0, ge=0.0)
    max_green: float = Field(default=60.0, ge=0.0)

    def build_domain(self) -> SignalPhase:
        return SignalPhase(
            id=self.id,
            green_movement_ids=tuple(self.green_movement_ids),
            green_duration=self.green_duration,
            yellow_duration=self.yellow_duration,
            all_red_duration=self.all_red_duration,
            min_green=self.min_green,
            max_green=self.max_green,
        )


class SignalPlanConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    phases: list[SignalPhaseConfig] = Field(min_length=2)

    def build_domain(self) -> SignalPlan:
        return SignalPlan(
            id=self.id,
            phases=tuple(p.build_domain() for p in self.phases),
        )


class DemandProfileConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    movement_id: str
    flow_rate_vph: float = Field(ge=0.0)

    def build_domain(self) -> DemandProfile:
        return DemandProfile(
            movement_id=self.movement_id,
            flow_rate_vph=self.flow_rate_vph,
        )


class SimulationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    duration: float = Field(default=300.0, gt=0.0)
    step_size: float = Field(default=1.0, gt=0.0)
    seed: int | None = Field(default=42)


class ScenarioConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intersection: IntersectionConfig
    signal_plan: SignalPlanConfig
    demands: list[DemandProfileConfig]
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)

    def build_scenario(
        self,
    ) -> tuple[Intersection, SignalPlan, tuple[DemandProfile, ...], SimulationConfig]:
        inter = self.intersection.build_domain()
        plan = self.signal_plan.build_domain()
        demands = tuple(d.build_domain() for d in self.demands)

        try:
            validate_signal_plan_against_intersection(plan, inter)
        except Exception as exc:
            raise ConfigurationError(str(exc)) from exc

        movement_ids = {m.id for m in inter.movements}
        for d in demands:
            if d.movement_id not in movement_ids:
                raise ConfigurationError(
                    f"demand references unknown movement '{d.movement_id}'"
                )

        return inter, plan, demands, self.simulation
