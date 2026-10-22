from collections.abc import Sequence
from typing import Any

from junction_sim.config.schema import ScenarioConfig
from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan, SignalState
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.exceptions import ConfigurationError, ValidationError


class RLController(SignalController):
    def __init__(self, signal_plan: SignalPlan) -> None:
        self._signal_plan = signal_plan
        self._target_phase_id: str | None = None

    def set_target_phase_id(self, target_phase_id: str | None) -> None:
        self._target_phase_id = target_phase_id

    def reset(self) -> None:
        self._target_phase_id = None

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if context.is_in_transition:
            return ControllerDecision(
                target_phase_id=None,
                reason="in_transition",
            )
        return ControllerDecision(
            target_phase_id=self._target_phase_id,
            reason="rl_action",
        )


class JunctionEnv:
    def __init__(
        self,
        scenario: ScenarioConfig,
        reward_type: str = "queue_penalty",
        duration: float | None = None,
    ) -> None:
        if reward_type not in ("queue_penalty", "delay_penalty", "throughput"):
            raise ConfigurationError(
                f"unsupported reward_type '{reward_type}', expected one of: "
                "queue_penalty, delay_penalty, throughput"
            )

        self._scenario = scenario
        self._reward_type = reward_type

        inter, plan, demands, sim_cfg = scenario.build_scenario()
        self._intersection: Intersection = inter
        self._signal_plan: SignalPlan = plan
        self._demands: Sequence[DemandProfile] = demands
        self._duration: float = duration if duration is not None else sim_cfg.duration
        self._step_size: float = sim_cfg.step_size
        self._default_seed: int | None = sim_cfg.seed

        lane_ids: list[str] = []
        for app in inter.approaches:
            for lane in app.lanes:
                lane_ids.append(lane.id)
        self._lane_ids: tuple[str, ...] = tuple(sorted(lane_ids))
        self._phase_ids: tuple[str, ...] = tuple(p.id for p in plan.phases)

        self._controller = RLController(signal_plan=self._signal_plan)
        self._engine: SimulationEngine | None = None

    @property
    def observation_size(self) -> int:
        return len(self._lane_ids) + len(self._phase_ids) + 2

    @property
    def action_size(self) -> int:
        return len(self._phase_ids)

    @property
    def lane_ids(self) -> tuple[str, ...]:
        return self._lane_ids

    @property
    def phase_ids(self) -> tuple[str, ...]:
        return self._phase_ids

    @property
    def current_time(self) -> float:
        if self._engine is None:
            return 0.0
        return self._engine.current_time

    def _get_observation(self) -> list[float]:
        if self._engine is None:
            return [0.0] * self.observation_size

        obs: list[float] = [
            float(self._engine.get_queue_length(lane_id)) for lane_id in self._lane_ids
        ]

        active_id = self._engine.active_phase_id
        for phase_id in self._phase_ids:
            obs.append(1.0 if phase_id == active_id else 0.0)

        state = self._engine.signal_state
        if state == SignalState.GREEN:
            state_val = 1.0
        elif state == SignalState.YELLOW:
            state_val = 0.5
        else:
            state_val = 0.0
        obs.append(state_val)

        elapsed_norm = min(self._engine.current_time / max(self._duration, 1.0), 1.0)
        obs.append(elapsed_norm)

        return obs

    def reset(self, seed: int | None = None) -> tuple[list[float], dict[str, Any]]:
        target_seed = seed if seed is not None else self._default_seed

        inter, plan, demands, _ = self._scenario.build_scenario()
        self._intersection = inter
        self._signal_plan = plan
        self._demands = demands

        self._controller = RLController(signal_plan=self._signal_plan)
        self._engine = SimulationEngine(
            intersection=self._intersection,
            signal_plan=self._signal_plan,
            demands=self._demands,
            controller=self._controller,
            step_size=self._step_size,
            seed=target_seed,
        )

        obs = self._get_observation()
        info: dict[str, Any] = {
            "step_index": 0,
            "current_time": 0.0,
            "active_phase_id": self._engine.active_phase_id,
            "signal_state": self._engine.signal_state.value,
        }
        return obs, info

    def step(
        self, action: int
    ) -> tuple[list[float], float, bool, bool, dict[str, Any]]:
        if self._engine is None:
            self.reset()
            assert self._engine is not None

        if not (0 <= action < len(self._phase_ids)):
            max_act = len(self._phase_ids) - 1
            raise ValidationError(
                f"invalid action '{action}', must be between 0 and {max_act}"
            )

        target_phase = self._phase_ids[action]
        self._controller.set_target_phase_id(target_phase)

        step_result = self._engine.step()

        if self._reward_type == "queue_penalty":
            total_q = sum(step_result.queue_lengths.values())
            reward = -float(total_q)
        elif self._reward_type == "delay_penalty":
            delays = [
                v.waiting_time(step_result.time)
                for v in step_result.discharged_vehicles
            ]
            reward = -float(sum(delays)) if delays else 0.0
        else:
            reward = float(len(step_result.discharged_vehicles))

        terminated = False
        truncated = self._engine.current_time >= self._duration

        obs = self._get_observation()
        info: dict[str, Any] = {
            "step_index": step_result.step_index,
            "current_time": step_result.time,
            "active_phase_id": step_result.active_phase_id,
            "signal_state": step_result.signal_state.value,
            "total_queue": sum(step_result.queue_lengths.values()),
            "arrived": len(step_result.arrived_vehicles),
            "discharged": len(step_result.discharged_vehicles),
        }

        return obs, reward, terminated, truncated, info
