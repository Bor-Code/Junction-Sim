from pydantic import BaseModel, ConfigDict, Field

from junction_sim.controllers.protocol import ControllerDecision
from junction_sim.domain.crosswalk import PedestrianSignalState
from junction_sim.domain.pedestrian import Pedestrian
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.transition import SignalState


class StepResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    time: float
    step_index: int
    active_phase_id: str
    signal_state: SignalState
    arrived_vehicles: tuple[Vehicle, ...]
    discharged_vehicles: tuple[Vehicle, ...]
    queue_lengths: dict[str, int]
    controller_decision: ControllerDecision | None = Field(default=None)
    arrived_pedestrians: tuple[Pedestrian, ...] = Field(default_factory=tuple)
    discharged_pedestrians: tuple[Pedestrian, ...] = Field(default_factory=tuple)
    pedestrian_queue_lengths: dict[str, int] = Field(default_factory=dict)
    pedestrian_signals: dict[str, PedestrianSignalState] = Field(default_factory=dict)
