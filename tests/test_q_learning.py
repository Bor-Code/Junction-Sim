import io
from pathlib import Path

import pytest

from junction_sim.cli import main
from junction_sim.cli.commands import instantiate_controller
from junction_sim.controllers.protocol import ControllerContext
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import ValidationError
from junction_sim.presets import get_preset
from junction_sim.rl.env import JunctionEnv
from junction_sim.rl.q_learning import (
    QLearningAgent,
    QLearningController,
    discretize_observation,
    train_q_learning,
)


def create_simple_intersection_and_plan() -> tuple[Intersection, SignalPlan]:
    m1 = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    m2 = Movement(
        id="S_T",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    l1 = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    l2 = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(l1,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(l2,))
    inter = Intersection(
        id="test_int",
        approaches=(app_n, app_s),
        movements=(m1, m2),
        conflicting_movement_pairs=frozenset(),
    )
    p1 = SignalPhase(id="P1", green_movement_ids=("N_T",), green_duration=10.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("S_T",), green_duration=10.0)
    plan = SignalPlan(id="test_plan", phases=(p1, p2))
    return inter, plan


def test_discretize_observation() -> None:
    obs = [-1.0, 0.0, 1.5, 3.0, 7.0, 15.0]
    discrete = discretize_observation(obs)
    assert discrete == (0, 0, 1, 2, 3, 4)


def test_q_learning_agent_validation() -> None:
    with pytest.raises(ValidationError):
        QLearningAgent(action_size=0)


def test_q_learning_agent_update_and_decay(tmp_path: Path) -> None:
    agent = QLearningAgent(
        action_size=2,
        alpha=0.5,
        gamma=0.9,
        epsilon=1.0,
        epsilon_min=0.1,
        epsilon_decay=0.5,
        seed=42,
    )
    s0 = (0, 1)
    s1 = (1, 2)

    with pytest.raises(ValidationError):
        agent.update(s0, action=5, reward=1.0, next_state=s1, done=False)

    err = agent.update(s0, action=0, reward=10.0, next_state=s1, done=True)
    assert err == 10.0
    assert agent.get_q_values(s0)[0] == 5.0

    agent.update(s0, action=1, reward=5.0, next_state=s0, done=False)
    assert agent.get_q_values(s0)[1] > 0.0

    agent.decay_epsilon()
    assert agent.epsilon == 0.5
    agent.decay_epsilon()
    agent.decay_epsilon()
    agent.decay_epsilon()
    assert agent.epsilon == 0.1

    act_train = agent.select_action(s0, evaluate=False)
    assert act_train in (0, 1)
    act_eval = agent.select_action(s0, evaluate=True)
    assert act_eval == 0

    save_path = tmp_path / "model.json"
    agent.save(save_path)
    assert save_path.exists()

    agent2 = QLearningAgent(action_size=2)
    agent2.load(save_path)
    assert agent2.action_size == 2
    assert agent2.alpha == 0.5
    assert agent2.get_q_values(s0)[0] == 5.0


def test_q_learning_controller_decide() -> None:
    inter, plan = create_simple_intersection_and_plan()
    agent = QLearningAgent(action_size=2, seed=42)
    ctrl = QLearningController(
        agent=agent, signal_plan=plan, intersection=inter, min_green=5.0
    )
    assert ctrl.agent is agent

    ctx_trans = ControllerContext(
        current_time=1.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={"lane_n_0": 5, "lane_s_0": 0},
    )
    d_trans = ctrl.decide(ctx_trans)
    assert d_trans.reason == "in_transition"

    ctx_min_green = ControllerContext(
        current_time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 5, "lane_s_0": 0},
    )
    d_min = ctrl.decide(ctx_min_green)
    assert d_min.reason == "min_green_enforced"

    state_key = ",".join(["0", "3", "1", "0", "1", "1"])
    agent.q_table[state_key] = [0.0, 10.0]
    ctx_switch = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 0, "lane_s_0": 10},
    )
    d_switch = ctrl.decide(ctx_switch)
    assert d_switch.reason == "q_learning_phase_switch"
    assert d_switch.target_phase_id == "P2"

    agent.q_table[state_key] = [10.0, 0.0]
    ctx_hold = ControllerContext(
        current_time=20.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_n_0": 0, "lane_s_0": 10},
    )
    d_hold = ctrl.decide(ctx_hold)
    assert d_hold.reason == "q_learning_hold_phase"
    assert d_hold.target_phase_id is None

    ctrl.reset()


def test_train_q_learning() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario, reward_type="queue_penalty", duration=10.0)

    with pytest.raises(ValidationError):
        train_q_learning(env=env, episodes=0)

    agent, rewards = train_q_learning(env=env, episodes=2, max_steps=3, seed=42)
    assert len(rewards) == 2
    assert isinstance(agent, QLearningAgent)


def test_instantiate_controller_q_learning() -> None:
    inter, plan = create_simple_intersection_and_plan()
    c1 = instantiate_controller("q-learning", plan, inter)
    assert isinstance(c1, QLearningController)
    c2 = instantiate_controller("rl", plan, inter)
    assert isinstance(c2, QLearningController)


def test_cli_train_and_run(tmp_path: Path) -> None:
    out_model = tmp_path / "trained.json"
    buf = io.StringIO()
    code = main(
        [
            "train",
            "--preset",
            "webster_four_way",
            "--episodes",
            "2",
            "--out-model",
            str(out_model),
        ],
        stdout=buf,
    )
    assert code == 0
    assert out_model.exists()
    assert "Training Complete" in buf.getvalue()

    buf_run = io.StringIO()
    code_run = main(
        [
            "run",
            "--preset",
            "webster_four_way",
            "--controller",
            "q-learning",
            "--duration",
            "5.0",
        ],
        stdout=buf_run,
    )
    assert code_run == 0

    buf_no_model = io.StringIO()
    code_no_model = main(
        [
            "train",
            "--preset",
            "webster_four_way",
            "--episodes",
            "1",
        ],
        stdout=buf_no_model,
    )
    assert code_no_model == 0
