import json
import random
from collections.abc import Sequence
from pathlib import Path

from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import ValidationError
from junction_sim.rl.env import JunctionEnv


def discretize_observation(observation: Sequence[float]) -> tuple[int, ...]:
    buckets: list[int] = []
    for val in observation:
        if val <= 0.0:
            b = 0
        elif val <= 2.0:
            b = 1
        elif val <= 5.0:
            b = 2
        elif val <= 10.0:
            b = 3
        else:
            b = 4
        buckets.append(b)
    return tuple(buckets)


class QLearningAgent:
    def __init__(
        self,
        action_size: int,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        seed: int | None = None,
    ) -> None:
        if action_size <= 0:
            raise ValidationError("action_size must be positive")
        self.action_size = action_size
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table: dict[str, list[float]] = {}
        self._rng = random.Random(seed)

    def _state_key(self, state: tuple[int, ...]) -> str:
        return ",".join(str(x) for x in state)

    def get_q_values(self, state: tuple[int, ...]) -> list[float]:
        key = self._state_key(state)
        if key not in self.q_table:
            self.q_table[key] = [0.0] * self.action_size
        return self.q_table[key]

    def select_action(self, state: tuple[int, ...], evaluate: bool = False) -> int:
        if not evaluate and self._rng.random() < self.epsilon:
            return self._rng.randrange(self.action_size)
        q_vals = self.get_q_values(state)
        max_val = max(q_vals)
        best_actions = [i for i, v in enumerate(q_vals) if v == max_val]
        return self._rng.choice(best_actions)

    def update(
        self,
        state: tuple[int, ...],
        action: int,
        reward: float,
        next_state: tuple[int, ...],
        done: bool,
    ) -> float:
        if not (0 <= action < self.action_size):
            raise ValidationError(f"action {action} out of range")
        q_vals = self.get_q_values(state)
        current_q = q_vals[action]
        if done:
            target = reward
        else:
            next_q = max(self.get_q_values(next_state))
            target = reward + self.gamma * next_q
        td_error = target - current_q
        q_vals[action] = current_q + self.alpha * td_error
        return td_error

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: Path | str) -> None:
        data = {
            "action_size": self.action_size,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
            "q_table": self.q_table,
        }
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path | str) -> None:
        dest = Path(path)
        data = json.loads(dest.read_text(encoding="utf-8"))
        self.action_size = int(data["action_size"])
        self.alpha = float(data["alpha"])
        self.gamma = float(data["gamma"])
        self.epsilon = float(data["epsilon"])
        self.epsilon_min = float(data["epsilon_min"])
        self.epsilon_decay = float(data["epsilon_decay"])
        self.q_table = {
            k: [float(v) for v in vals] for k, vals in data["q_table"].items()
        }


class QLearningController(SignalController):
    def __init__(
        self,
        agent: QLearningAgent,
        signal_plan: SignalPlan,
        intersection: Intersection,
        min_green: float = 7.0,
    ) -> None:
        self._agent = agent
        self._signal_plan = signal_plan
        self._intersection = intersection
        self._min_green = min_green
        self._phase_ids = tuple(p.id for p in signal_plan.phases)
        lane_ids: list[str] = []
        for app in intersection.approaches:
            for lane in app.lanes:
                lane_ids.append(lane.id)
        self._lane_ids = tuple(sorted(lane_ids))
        self._last_change_time = 0.0

    @property
    def agent(self) -> QLearningAgent:
        return self._agent

    def reset(self) -> None:
        self._last_change_time = 0.0

    def decide(self, context: ControllerContext) -> ControllerDecision:
        if context.is_in_transition:
            return ControllerDecision(target_phase_id=None, reason="in_transition")

        time_in_phase = context.current_time - self._last_change_time
        if time_in_phase < self._min_green:
            return ControllerDecision(target_phase_id=None, reason="min_green_enforced")

        obs_vals: list[float] = [
            float(context.queue_lengths.get(lid, 0)) for lid in self._lane_ids
        ]
        for pid in self._phase_ids:
            obs_vals.append(1.0 if pid == context.active_phase_id else 0.0)
        obs_vals.append(1.0)
        obs_vals.append(0.5)

        discrete_state = discretize_observation(obs_vals)
        action = self._agent.select_action(discrete_state, evaluate=True)
        chosen_phase_id = self._phase_ids[action]

        if chosen_phase_id != context.active_phase_id:
            self._last_change_time = context.current_time
            return ControllerDecision(
                target_phase_id=chosen_phase_id, reason="q_learning_phase_switch"
            )

        return ControllerDecision(target_phase_id=None, reason="q_learning_hold_phase")


def train_q_learning(
    env: JunctionEnv,
    episodes: int = 10,
    max_steps: int | None = None,
    seed: int | None = 42,
) -> tuple[QLearningAgent, list[float]]:
    if episodes <= 0:
        raise ValidationError("episodes must be positive")

    agent = QLearningAgent(
        action_size=env.action_size,
        seed=seed,
    )
    episode_rewards: list[float] = []

    for ep in range(episodes):
        ep_seed = (seed + ep) if seed is not None else None
        obs, _ = env.reset(seed=ep_seed)
        state = discretize_observation(obs)
        total_reward = 0.0
        step_count = 0

        while True:
            action = agent.select_action(state, evaluate=False)
            next_obs, reward, terminated, truncated, _ = env.step(action)
            next_state = discretize_observation(next_obs)
            done = terminated or truncated
            agent.update(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward
            step_count += 1

            if done or (max_steps is not None and step_count >= max_steps):
                break

        agent.decay_epsilon()
        episode_rewards.append(round(total_reward, 2))

    return agent, episode_rewards
