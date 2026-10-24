import json
import math
import random
from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import ValidationError
from junction_sim.rl.env import JunctionEnv


class ReplayBuffer:
    def __init__(self, capacity: int = 2000, seed: int | None = None) -> None:
        if capacity <= 0:
            raise ValidationError("capacity must be positive")
        self._buffer: deque[tuple[list[float], int, float, list[float], bool]] = deque(
            maxlen=capacity
        )
        self._rng = random.Random(seed)

    def __len__(self) -> int:
        return len(self._buffer)

    def push(
        self,
        state: list[float],
        action: int,
        reward: float,
        next_state: list[float],
        done: bool,
    ) -> None:
        self._buffer.append(
            (list(state), action, float(reward), list(next_state), done)
        )

    def sample(
        self, batch_size: int
    ) -> list[tuple[list[float], int, float, list[float], bool]]:
        if batch_size <= 0:
            raise ValidationError("batch_size must be positive")
        if batch_size > len(self._buffer):
            raise ValidationError(
                f"sample size {batch_size} exceeds buffer length {len(self._buffer)}"
            )
        indices = self._rng.sample(range(len(self._buffer)), batch_size)
        return [self._buffer[i] for i in indices]


class DenseLayer:
    def __init__(
        self,
        in_features: int,
        out_features: int,
        weights: list[list[float]] | None = None,
        biases: list[float] | None = None,
        seed: int | None = None,
    ) -> None:
        if in_features <= 0 or out_features <= 0:
            raise ValidationError("layer dimensions must be positive")
        self.in_features = in_features
        self.out_features = out_features
        rng = random.Random(seed)

        if weights is not None:
            self.weights = [list(w) for w in weights]
        else:
            limit = math.sqrt(2.0 / in_features)
            self.weights = [
                [rng.uniform(-limit, limit) for _ in range(out_features)]
                for _ in range(in_features)
            ]

        if biases is not None:
            self.biases = list(biases)
        else:
            self.biases = [0.0] * out_features

    def forward(self, x: Sequence[float]) -> list[float]:
        out = list(self.biases)
        for i, val in enumerate(x):
            row = self.weights[i]
            for j in range(self.out_features):
                out[j] += val * row[j]
        return out

    def clone(self) -> "DenseLayer":
        return DenseLayer(
            in_features=self.in_features,
            out_features=self.out_features,
            weights=[list(w) for w in self.weights],
            biases=list(self.biases),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "in_features": self.in_features,
            "out_features": self.out_features,
            "weights": self.weights,
            "biases": self.biases,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DenseLayer":
        return cls(
            in_features=int(data["in_features"]),
            out_features=int(data["out_features"]),
            weights=data["weights"],
            biases=data["biases"],
        )


class DQNNetwork:
    def __init__(
        self,
        state_dim: int,
        hidden_dim: int,
        action_dim: int,
        seed: int | None = None,
    ) -> None:
        if state_dim <= 0 or hidden_dim <= 0 or action_dim <= 0:
            raise ValidationError("network dimensions must be positive")
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.action_dim = action_dim
        self.layer1 = DenseLayer(
            state_dim, hidden_dim, seed=seed if seed is not None else 42
        )
        self.layer2 = DenseLayer(
            hidden_dim, action_dim, seed=(seed + 1) if seed is not None else 43
        )

    def forward(self, state: Sequence[float]) -> tuple[list[float], list[float]]:
        h_pre = self.layer1.forward(state)
        h_act = [max(0.0, val) for val in h_pre]
        q_values = self.layer2.forward(h_act)
        return h_act, q_values

    def predict(self, state: Sequence[float]) -> list[float]:
        _, q_values = self.forward(state)
        return q_values

    def train_on_batch(
        self,
        states: list[list[float]],
        actions: list[int],
        targets: list[float],
        lr: float = 0.01,
    ) -> float:
        total_loss = 0.0
        n = len(states)
        if n == 0:
            return 0.0

        for state, action, target in zip(states, actions, targets, strict=True):
            h_act, q_values = self.forward(state)
            pred = q_values[action]
            err = pred - target
            total_loss += err * err

            grad_out = [0.0] * self.action_dim
            grad_out[action] = 2.0 * err / n

            for j in range(self.action_dim):
                g_j = grad_out[j]
                if g_j != 0.0:
                    self.layer2.biases[j] -= lr * g_j
                    for k in range(self.hidden_dim):
                        self.layer2.weights[k][j] -= lr * g_j * h_act[k]

            grad_h = [0.0] * self.hidden_dim
            for k in range(self.hidden_dim):
                s = 0.0
                for j in range(self.action_dim):
                    s += grad_out[j] * self.layer2.weights[k][j]
                grad_h[k] = s if h_act[k] > 0.0 else 0.0

            for k in range(self.hidden_dim):
                g_k = grad_h[k]
                if g_k != 0.0:
                    self.layer1.biases[k] -= lr * g_k
                    for i in range(self.state_dim):
                        self.layer1.weights[i][k] -= lr * g_k * state[i]

        return total_loss / n

    def copy_weights_from(self, other: "DQNNetwork") -> None:
        self.layer1 = other.layer1.clone()
        self.layer2 = other.layer2.clone()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_dim": self.state_dim,
            "hidden_dim": self.hidden_dim,
            "action_dim": self.action_dim,
            "layer1": self.layer1.to_dict(),
            "layer2": self.layer2.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DQNNetwork":
        net = cls(
            state_dim=int(data["state_dim"]),
            hidden_dim=int(data["hidden_dim"]),
            action_dim=int(data["action_dim"]),
        )
        net.layer1 = DenseLayer.from_dict(data["layer1"])
        net.layer2 = DenseLayer.from_dict(data["layer2"])
        return net


class DQNAgent:
    def __init__(
        self,
        state_size: int,
        action_size: int,
        hidden_dim: int = 32,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        learning_rate: float = 0.01,
        batch_size: int = 32,
        buffer_capacity: int = 2000,
        target_update_interval: int = 50,
        seed: int | None = None,
    ) -> None:
        if state_size <= 0 or action_size <= 0:
            raise ValidationError("state_size and action_size must be positive")
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.target_update_interval = target_update_interval

        self.policy_net = DQNNetwork(state_size, hidden_dim, action_size, seed=seed)
        self.target_net = DQNNetwork(state_size, hidden_dim, action_size, seed=seed)
        self.target_net.copy_weights_from(self.policy_net)

        self.memory = ReplayBuffer(capacity=buffer_capacity, seed=seed)
        self._step_counter = 0
        self._rng = random.Random(seed)

    def select_action(self, state: Sequence[float], evaluate: bool = False) -> int:
        if not evaluate and self._rng.random() < self.epsilon:
            return self._rng.randrange(self.action_size)
        q_values = self.policy_net.predict(state)
        max_q = max(q_values)
        best_actions = [i for i, v in enumerate(q_values) if v == max_q]
        return self._rng.choice(best_actions)

    def remember(
        self,
        state: list[float],
        action: int,
        reward: float,
        next_state: list[float],
        done: bool,
    ) -> None:
        self.memory.push(state, action, reward, next_state, done)

    def update(self) -> float:
        if len(self.memory) < self.batch_size:
            return 0.0

        batch = self.memory.sample(self.batch_size)
        states: list[list[float]] = []
        actions: list[int] = []
        targets: list[float] = []

        for s, a, r, next_s, done in batch:
            states.append(s)
            actions.append(a)
            if done:
                targets.append(r)
            else:
                next_q = max(self.target_net.predict(next_s))
                targets.append(r + self.gamma * next_q)

        loss = self.policy_net.train_on_batch(
            states, actions, targets, lr=self.learning_rate
        )

        self._step_counter += 1
        if self._step_counter % self.target_update_interval == 0:
            self.target_net.copy_weights_from(self.policy_net)

        return loss

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: Path | str) -> None:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "state_size": self.state_size,
            "action_size": self.action_size,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "policy_net": self.policy_net.to_dict(),
        }
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path | str) -> None:
        dest = Path(path)
        data = json.loads(dest.read_text(encoding="utf-8"))
        self.state_size = int(data["state_size"])
        self.action_size = int(data["action_size"])
        self.gamma = float(data["gamma"])
        self.epsilon = float(data["epsilon"])
        self.epsilon_min = float(data["epsilon_min"])
        self.epsilon_decay = float(data["epsilon_decay"])
        self.learning_rate = float(data["learning_rate"])
        self.batch_size = int(data["batch_size"])
        self.policy_net = DQNNetwork.from_dict(data["policy_net"])
        self.target_net.copy_weights_from(self.policy_net)


class DQNController(SignalController):
    def __init__(
        self,
        agent: DQNAgent,
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
    def agent(self) -> DQNAgent:
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

        action = self._agent.select_action(obs_vals, evaluate=True)
        chosen_phase_id = self._phase_ids[action]

        if chosen_phase_id != context.active_phase_id:
            self._last_change_time = context.current_time
            return ControllerDecision(
                target_phase_id=chosen_phase_id, reason="dqn_phase_switch"
            )

        return ControllerDecision(target_phase_id=None, reason="dqn_hold_phase")


def train_dqn(
    env: JunctionEnv,
    episodes: int = 10,
    max_steps: int | None = None,
    seed: int | None = 42,
) -> tuple[DQNAgent, list[float]]:
    if episodes <= 0:
        raise ValidationError("episodes must be positive")

    agent = DQNAgent(
        state_size=env.observation_size,
        action_size=env.action_size,
        seed=seed,
    )
    episode_rewards: list[float] = []

    for ep in range(episodes):
        ep_seed = (seed + ep) if seed is not None else None
        obs, _ = env.reset(seed=ep_seed)
        total_reward = 0.0
        step_count = 0

        while True:
            action = agent.select_action(obs, evaluate=False)
            next_obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated

            agent.remember(obs, action, reward, next_obs, done)
            agent.update()

            obs = next_obs
            total_reward += reward
            step_count += 1

            if done or (max_steps is not None and step_count >= max_steps):
                break

        agent.decay_epsilon()
        episode_rewards.append(round(total_reward, 2))

    return agent, episode_rewards
