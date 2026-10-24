from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from junction_sim.domain.network import IntersectionNetwork, RoadLink
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.clock import SimulationClock
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.rng import TrafficRNG
from junction_sim.engine.step_result import StepResult
from junction_sim.exceptions import InvalidGeometryError, ValidationError


@dataclass(frozen=True)
class InTransitVehicle:
    vehicle: Vehicle
    entry_time: float
    exit_time: float
    link_id: str
    target_node_id: str
    target_lane_id: str


class NetworkStepResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    step_index: int = Field(ge=0)
    time: float = Field(ge=0.0)
    node_results: dict[str, StepResult]
    transit_vehicle_counts: dict[str, int]

    @property
    def total_network_arrivals(self) -> int:
        return sum(len(res.arrived_vehicles) for res in self.node_results.values())

    @property
    def total_network_discharges(self) -> int:
        return sum(len(res.discharged_vehicles) for res in self.node_results.values())

    @property
    def total_in_transit(self) -> int:
        return sum(self.transit_vehicle_counts.values())

    @property
    def network_max_queue(self) -> int:
        queues = [
            max(res.queue_lengths.values(), default=0)
            for res in self.node_results.values()
        ]
        return max(queues, default=0)


class NetworkSimulationEngine:
    def __init__(
        self,
        network: IntersectionNetwork,
        step_size: float = 1.0,
        seed: int | None = None,
    ) -> None:
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")

        self._network = network
        self._step_size = step_size
        self._clock = SimulationClock(start_time=0.0, step_size=step_size)
        self._rng = TrafficRNG(seed=seed)

        self._engines: dict[str, SimulationEngine] = {}
        for node in network.nodes.values():
            node_seed = self._rng.spawn_child().seed
            self._engines[node.id] = SimulationEngine(
                intersection=node.intersection,
                signal_plan=node.signal_plan,
                demands=node.demands,
                pedestrian_demands=node.pedestrian_demands,
                controller=node.controller,
                step_size=step_size,
                seed=node_seed,
            )

        self._transit: dict[str, list[InTransitVehicle]] = {
            link.id: [] for link in network.links
        }
        self._movement_links: dict[tuple[str, str], RoadLink] = {}
        for link in network.links:
            self._movement_links[(link.source_node_id, link.source_movement_id)] = link

    @property
    def network(self) -> IntersectionNetwork:
        return self._network

    @property
    def step_size(self) -> float:
        return self._step_size

    @property
    def current_time(self) -> float:
        return self._clock.current_time

    def get_engine(self, node_id: str) -> SimulationEngine:
        if node_id not in self._engines:
            raise InvalidGeometryError(f"unknown node id '{node_id}'")
        return self._engines[node_id]

    def get_transit_vehicles(self, link_id: str) -> tuple[InTransitVehicle, ...]:
        if link_id not in self._transit:
            raise InvalidGeometryError(f"unknown link id '{link_id}'")
        return tuple(self._transit[link_id])

    def step(self) -> NetworkStepResult:
        step_time = self._clock.current_time
        step_index = self._clock.step_count

        for link in self._network.links:
            remaining: list[InTransitVehicle] = []
            for tv in self._transit[link.id]:
                if tv.exit_time <= step_time:
                    self._engines[tv.target_node_id].enqueue_vehicle(
                        tv.vehicle, tv.target_lane_id
                    )
                else:
                    remaining.append(tv)
            self._transit[link.id] = remaining

        node_results: dict[str, StepResult] = {}
        for node_id, engine in self._engines.items():
            node_results[node_id] = engine.step()

        for node_id, res in node_results.items():
            inter = self._network.nodes[node_id].intersection
            for veh in res.discharged_vehicles:
                mov_id = None
                for m in inter.movements:
                    if m.origin == veh.origin and m.destination == veh.destination:
                        mov_id = m.id
                        break
                if mov_id is None:
                    continue
                target_link = self._movement_links.get((node_id, mov_id))
                if target_link is not None:
                    exit_time = step_time + target_link.travel_time
                    self._transit[target_link.id].append(
                        InTransitVehicle(
                            vehicle=veh,
                            entry_time=step_time,
                            exit_time=exit_time,
                            link_id=target_link.id,
                            target_node_id=target_link.target_node_id,
                            target_lane_id=target_link.target_lane_id,
                        )
                    )

        transit_counts = {
            link_id: len(vehicles) for link_id, vehicles in self._transit.items()
        }

        self._clock = self._clock.tick()

        return NetworkStepResult(
            step_index=step_index,
            time=step_time,
            node_results=node_results,
            transit_vehicle_counts=transit_counts,
        )

    def run(self, duration: float) -> list[NetworkStepResult]:
        if duration <= 0.0:
            raise ValidationError("duration must be greater than zero")
        step_count = int(duration / self._step_size)
        return [self.step() for _ in range(step_count)]
