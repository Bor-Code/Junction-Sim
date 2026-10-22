from junction_sim.benchmarks.metrics import BenchmarkMetrics, BenchmarkResult
from junction_sim.controllers.protocol import SignalController
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import ValidationError


class BenchmarkHarness:
    def __init__(
        self,
        intersection: Intersection,
        signal_plan: SignalPlan,
        demands: tuple[DemandProfile, ...],
        step_size: float = 1.0,
        seed: int | None = 42,
    ) -> None:
        if step_size <= 0.0:
            raise ValidationError("step_size must be greater than zero")
        validate_signal_plan_against_intersection(signal_plan, intersection)

        self._intersection = intersection
        self._signal_plan = signal_plan
        self._demands = demands
        self._step_size = step_size
        self._seed = seed

        self._phase_to_lanes: dict[str, tuple[str, ...]] = {}
        for phase in signal_plan.phases:
            lanes: list[str] = []
            for m_id in phase.green_movement_ids:
                mov = intersection.get_movement(m_id)
                approach = intersection.get_approach(mov.origin)
                for lane in approach.get_lanes_for_movement(m_id):
                    lanes.append(lane.id)
            self._phase_to_lanes[phase.id] = tuple(sorted(set(lanes)))

    @property
    def intersection(self) -> Intersection:
        return self._intersection

    @property
    def signal_plan(self) -> SignalPlan:
        return self._signal_plan

    @property
    def demands(self) -> tuple[DemandProfile, ...]:
        return self._demands

    @property
    def step_size(self) -> float:
        return self._step_size

    @property
    def seed(self) -> int | None:
        return self._seed

    def evaluate_controller(
        self, controller: SignalController, name: str, duration: float
    ) -> BenchmarkMetrics:
        if duration <= 0.0:
            raise ValidationError("duration must be greater than zero")
        if not isinstance(controller, SignalController):
            raise ValidationError(
                "controller must conform to SignalController protocol"
            )

        controller.reset()
        engine = SimulationEngine(
            intersection=self._intersection,
            signal_plan=self._signal_plan,
            demands=self._demands,
            controller=controller,
            step_size=self._step_size,
            seed=self._seed,
        )

        results = engine.run(duration)

        total_arrivals = sum(len(r.arrived_vehicles) for r in results)
        total_discharges = sum(len(r.discharged_vehicles) for r in results)

        if total_arrivals > 0:
            completion_rate = round((total_discharges / total_arrivals) * 100.0, 2)
        else:
            completion_rate = 100.0

        waiting_times = [
            v.waiting_time(r.time) for r in results for v in r.discharged_vehicles
        ]
        average_delay = (
            round(sum(waiting_times) / len(waiting_times), 3) if waiting_times else 0.0
        )
        max_delay = round(max(waiting_times), 3) if waiting_times else 0.0

        step_queues = [sum(r.queue_lengths.values()) for r in results]
        average_queue = (
            round(sum(step_queues) / len(step_queues), 3) if step_queues else 0.0
        )
        max_queue = max(step_queues) if step_queues else 0

        phase_switch_count = sum(
            1
            for r in results
            if r.controller_decision is not None
            and r.controller_decision.should_change_phase
        )

        wasted_steps = 0
        for r in results:
            if r.signal_state == SignalState.GREEN:
                phase_lanes = self._phase_to_lanes[r.active_phase_id]
                active_phase_queue = sum(r.queue_lengths[lid] for lid in phase_lanes)
                if active_phase_queue == 0 and len(r.discharged_vehicles) == 0:
                    wasted_steps += 1
        wasted_green_time = round(wasted_steps * self._step_size, 3)

        return BenchmarkMetrics(
            controller_name=name,
            total_arrivals=total_arrivals,
            total_discharges=total_discharges,
            completion_rate=completion_rate,
            average_delay=average_delay,
            max_delay=max_delay,
            average_queue=average_queue,
            max_queue=max_queue,
            phase_switch_count=phase_switch_count,
            wasted_green_time=wasted_green_time,
        )

    def run_benchmark(
        self, controllers: dict[str, SignalController], duration: float
    ) -> BenchmarkResult:
        if not controllers:
            raise ValidationError("controllers mapping cannot be empty")

        metrics: dict[str, BenchmarkMetrics] = {}
        for name, controller in controllers.items():
            metrics[name] = self.evaluate_controller(controller, name, duration)

        return BenchmarkResult(
            metrics=metrics,
            duration=duration,
            step_size=self._step_size,
            seed=self._seed,
        )
