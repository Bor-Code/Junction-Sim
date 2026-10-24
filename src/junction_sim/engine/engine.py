from collections.abc import Iterator

from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.domain.crosswalk import PedestrianSignalState
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.pedestrian import Pedestrian
from junction_sim.domain.signal import SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.arrival import (
    ArrivalGenerator,
    DemandProfile,
    PedestrianArrivalGenerator,
    PedestrianDemandProfile,
)
from junction_sim.engine.clock import SimulationClock
from junction_sim.engine.pedestrian_queue import PedestrianQueue
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
        pedestrian_demands: tuple[PedestrianDemandProfile, ...] = (),
        controller: SignalController | None = None,
        seed: int | None = None,
        step_size: float = 1.0,
    ) -> None:
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")
        if controller is not None and not isinstance(controller, SignalController):
            raise ValidationError("controller must implement SignalController protocol")

        validate_signal_plan_against_intersection(signal_plan, intersection)

        self._intersection = intersection
        self._signal_plan = signal_plan
        self._controller = controller
        self._step_size = step_size
        self._clock = SimulationClock(start_time=0.0, step_size=step_size)
        self._rng = TrafficRNG(seed=seed)
        self._arrival_generator = ArrivalGenerator(
            intersection=intersection,
            demands=demands,
            rng=self._rng.spawn_child(),
        )
        self._pedestrian_demands = pedestrian_demands
        self._pedestrian_arrival_generator = PedestrianArrivalGenerator(
            intersection=intersection,
            demands=pedestrian_demands,
            rng=self._rng.spawn_child(),
        )

        self._queues: dict[str, LaneQueue] = {}
        for app in intersection.approaches:
            for lane in app.lanes:
                self._queues[lane.id] = LaneQueue(lane=lane)

        self._pedestrian_queues: dict[str, PedestrianQueue] = {}
        for cw in intersection.crosswalks:
            self._pedestrian_queues[cw.id] = PedestrianQueue(crosswalk=cw)

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
    def controller(self) -> SignalController | None:
        return self._controller

    @property
    def queues(self) -> dict[str, LaneQueue]:
        return self._queues

    @property
    def pedestrian_demands(self) -> tuple[PedestrianDemandProfile, ...]:
        return self._pedestrian_demands

    @property
    def pedestrian_queues(self) -> dict[str, PedestrianQueue]:
        return self._pedestrian_queues

    def get_pedestrian_queue(self, crosswalk_id: str) -> PedestrianQueue:
        if crosswalk_id not in self._pedestrian_queues:
            raise InvalidGeometryError(f"unknown crosswalk id '{crosswalk_id}'")
        return self._pedestrian_queues[crosswalk_id]

    def get_pedestrian_queue_length(self, crosswalk_id: str) -> int:
        return self.get_pedestrian_queue(crosswalk_id).length

    def get_queue(self, lane_id: str) -> LaneQueue:
        if lane_id not in self._queues:
            raise InvalidGeometryError(f"unknown lane id '{lane_id}'")
        return self._queues[lane_id]

    def get_queue_length(self, lane_id: str) -> int:
        return self.get_queue(lane_id).length

    def enqueue_vehicle(self, vehicle: Vehicle, lane_id: str) -> None:
        queue = self.get_queue(lane_id)
        queue.enqueue(vehicle)

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

        arrived_pedestrians = self._pedestrian_arrival_generator.generate_arrivals(
            current_time=step_time, step_size=self._step_size
        )
        for ped in arrived_pedestrians:
            self._pedestrian_queues[ped.crosswalk_id].enqueue(ped)

        decision: ControllerDecision | None = None
        if self._controller is not None:
            context = ControllerContext(
                current_time=step_time,
                active_phase_id=self._phase_tracker.current_phase_id,
                signal_state=self._phase_tracker.state,
                is_in_transition=self._phase_tracker.is_in_transition,
                queue_lengths={
                    lane_id: q.length for lane_id, q in self._queues.items()
                },
            )
            decision = self._controller.decide(context)
            if decision.should_change_phase:
                assert decision.target_phase_id is not None
                self.request_phase_change(decision.target_phase_id)

        step_phase_id = self._phase_tracker.current_phase_id
        step_signal_state = self._phase_tracker.state

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

        active_phase_obj = self._signal_plan.get_phase(
            self._phase_tracker.current_phase_id
        )
        is_green = self._phase_tracker.can_discharge
        elapsed_green = self._phase_tracker.elapsed_in_state

        pedestrian_signals: dict[str, PedestrianSignalState] = {}
        discharged_pedestrians: list[Pedestrian] = []
        for cw in self._intersection.crosswalks:
            if cw.id in active_phase_obj.pedestrian_crosswalk_ids:
                p_state = cw.get_signal_state(
                    elapsed_in_phase=elapsed_green,
                    is_phase_green=is_green,
                )
            else:
                p_state = PedestrianSignalState.DONT_WALK
            pedestrian_signals[cw.id] = p_state

            if p_state == PedestrianSignalState.WALK:
                released = self._pedestrian_queues[cw.id].discharge(
                    current_time=step_time
                )
                discharged_pedestrians.extend(released)

        current_phase = self._signal_plan.get_phase(
            self._phase_tracker.current_phase_id
        )
        self._phase_tracker = self._phase_tracker.step(self._step_size, current_phase)
        self._clock = self._clock.tick()
        queue_lengths = {lane_id: q.length for lane_id, q in self._queues.items()}
        ped_queue_lengths = {
            cw_id: q.length for cw_id, q in self._pedestrian_queues.items()
        }

        return StepResult(
            time=step_time,
            step_index=step_index,
            active_phase_id=step_phase_id,
            signal_state=step_signal_state,
            arrived_vehicles=arrived_vehicles,
            discharged_vehicles=tuple(discharged_vehicles),
            queue_lengths=queue_lengths,
            controller_decision=decision,
            arrived_pedestrians=arrived_pedestrians,
            discharged_pedestrians=tuple(discharged_pedestrians),
            pedestrian_queue_lengths=ped_queue_lengths,
            pedestrian_signals=pedestrian_signals,
        )

    def run_iter(self, duration: float) -> Iterator[StepResult]:
        if duration <= 0.0:
            raise ValidationError("duration must be greater than zero")

        steps = round(duration / self._step_size)
        if abs(steps * self._step_size - duration) > 1e-6:
            raise ValidationError(
                f"duration ({duration}) must be an integer multiple "
                f"of step_size ({self._step_size})"
            )

        def _generator() -> Iterator[StepResult]:
            for _ in range(int(steps)):
                yield self.step()

        return _generator()

    def run(self, duration: float) -> tuple[StepResult, ...]:
        return tuple(self.run_iter(duration))
