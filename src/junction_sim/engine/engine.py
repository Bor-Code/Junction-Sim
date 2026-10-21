from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.arrival import ArrivalGenerator, DemandProfile
from junction_sim.engine.clock import SimulationClock
from junction_sim.engine.queue import LaneQueue
from junction_sim.engine.rng import TrafficRNG
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.transition import PhaseTracker, SignalState
from junction_sim.exceptions import InvalidGeometryError, ValidationError


class SimulationEngine:
    def __init__(
        self,
        intersection: Intersection,
        signal_plan: SignalPlan,
        demands: tuple[DemandProfile, ...],
        seed: int | None = None,
        step_size: float = 1.0,
    ) -> None:
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")

        validate_signal_plan_against_intersection(signal_plan, intersection)

        self._intersection = intersection
        self._signal_plan = signal_plan
        self._step_size = step_size
        self._clock = SimulationClock(start_time=0.0, step_size=step_size)
        self._rng = TrafficRNG(seed=seed)
        self._arrival_generator = ArrivalGenerator(
            intersection=intersection,
            demands=demands,
            rng=self._rng.spawn_child(),
        )

        self._queues: dict[str, LaneQueue] = {}
        for app in intersection.approaches:
            for lane in app.lanes:
                self._queues[lane.id] = LaneQueue(lane=lane)

        initial_phase = signal_plan.phases[0]
        self._phase_tracker = PhaseTracker(current_phase_id=initial_phase.id)

    @property
    def current_time(self) -> float:
        return self._clock.current_time

    @property
    def step_count(self) -> int:
        return self._clock.step_count

    @property
    def active_phase_id(self) -> str:
        return self._phase_tracker.current_phase_id

    @property
    def signal_state(self) -> SignalState:
        return self._phase_tracker.state

    @property
    def is_in_transition(self) -> bool:
        return self._phase_tracker.is_in_transition

    @property
    def intersection(self) -> Intersection:
        return self._intersection

    @property
    def signal_plan(self) -> SignalPlan:
        return self._signal_plan

    @property
    def queues(self) -> dict[str, LaneQueue]:
        return self._queues

    def get_queue(self, lane_id: str) -> LaneQueue:
        if lane_id not in self._queues:
            raise InvalidGeometryError(f"unknown lane id '{lane_id}'")
        return self._queues[lane_id]

    def get_queue_length(self, lane_id: str) -> int:
        return self.get_queue(lane_id).length

    def request_phase_change(self, target_phase_id: str) -> None:
        self._signal_plan.get_phase(target_phase_id)
        if (
            not self._phase_tracker.is_in_transition
            and target_phase_id == self._phase_tracker.current_phase_id
        ):
            return
        if (
            self._phase_tracker.is_in_transition
            and target_phase_id == self._phase_tracker.target_phase_id
        ):
            return

        self._phase_tracker = self._phase_tracker.request_phase_change(target_phase_id)
        for queue in self._queues.values():
            queue.reset_credit()

    def step(self) -> StepResult:
        step_time = self._clock.current_time
        step_index = self._clock.step_count

        arrived_vehicles = self._arrival_generator.generate_arrivals(
            current_time=step_time, step_size=self._step_size
        )
        for veh in arrived_vehicles:
            assert veh.target_lane_id is not None
            self._queues[veh.target_lane_id].enqueue(veh)

        current_phase = self._signal_plan.get_phase(
            self._phase_tracker.current_phase_id
        )
        self._phase_tracker = self._phase_tracker.step(self._step_size, current_phase)

        discharged_vehicles: list[Vehicle] = []
        if self._phase_tracker.can_discharge:
            active_phase = self._signal_plan.get_phase(
                self._phase_tracker.current_phase_id
            )
            for m_id in active_phase.green_movement_ids:
                mov = self._intersection.get_movement(m_id)
                approach = self._intersection.get_approach(mov.origin)
                lanes = approach.get_lanes_for_movement(m_id)
                for lane in lanes:
                    departed = self._queues[lane.id].discharge(
                        current_time=step_time,
                        step_size=self._step_size,
                        saturation_flow_rate=mov.saturation_flow_rate,
                    )
                    discharged_vehicles.extend(departed)

        self._clock = self._clock.tick()
        queue_lengths = {lane_id: q.length for lane_id, q in self._queues.items()}

        return StepResult(
            time=step_time,
            step_index=step_index,
            active_phase_id=self._phase_tracker.current_phase_id,
            signal_state=self._phase_tracker.state,
            arrived_vehicles=arrived_vehicles,
            discharged_vehicles=tuple(discharged_vehicles),
            queue_lengths=queue_lengths,
        )
