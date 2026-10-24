import io
from pathlib import Path

import pytest

from junction_sim.cli import main
from junction_sim.cli.commands import instantiate_controller
from junction_sim.controllers.protocol import ControllerContext
from junction_sim.domain.signal import SignalState
from junction_sim.exceptions import ConfigurationError, ValidationError
from junction_sim.presets import get_preset
from junction_sim.rl import (
    DenseLayer,
    DQNAgent,
    DQNController,
    DQNNetwork,
    JunctionEnv,
    ReplayBuffer,
    train_dqn,
)


def test_replay_buffer_validation_and_sampling() -> None:
    with pytest.raises(ValidationError, match="capacity must be positive"):
        ReplayBuffer(capacity=0)

    buf = ReplayBuffer(capacity=10, seed=42)
    assert len(buf) == 0

    with pytest.raises(ValidationError, match="batch_size must be positive"):
        buf.sample(0)

    with pytest.raises(ValidationError, match="exceeds buffer length"):
        buf.sample(1)

    buf.push([1.0], 0, 1.0, [2.0], False)
    assert len(buf) == 1
    sample = buf.sample(1)
    assert len(sample) == 1
    assert sample[0][0] == [1.0]
    assert sample[0][1] == 0
    assert sample[0][2] == 1.0
    assert sample[0][3] == [2.0]
    assert sample[0][4] is False


def test_dense_layer_operations() -> None:
    with pytest.raises(ValidationError, match="layer dimensions must be positive"):
        DenseLayer(in_features=0, out_features=5)

    with pytest.raises(ValidationError, match="layer dimensions must be positive"):
        DenseLayer(in_features=5, out_features=0)

    layer = DenseLayer(
        in_features=2,
        out_features=2,
        weights=[[1.0, 2.0], [3.0, 4.0]],
        biases=[0.5, -0.5],
    )
    out = layer.forward([1.0, 1.0])
    assert out[0] == 4.5
    assert out[1] == 5.5

    cloned = layer.clone()
    assert cloned.weights == layer.weights
    assert cloned.biases == layer.biases

    d = layer.to_dict()
    restored = DenseLayer.from_dict(d)
    assert restored.in_features == 2
    assert restored.out_features == 2
    assert restored.weights == layer.weights


def test_dqn_network_forward_backward() -> None:
    with pytest.raises(ValidationError, match="network dimensions must be positive"):
        DQNNetwork(state_dim=0, hidden_dim=4, action_dim=2)

    net = DQNNetwork(state_dim=2, hidden_dim=4, action_dim=2, seed=42)
    q_vals = net.predict([1.0, 0.5])
    assert len(q_vals) == 2

    empty_loss = net.train_on_batch([], [], [])
    assert empty_loss == 0.0

    loss = net.train_on_batch([[1.0, 0.5]], [0], [10.0], lr=0.05)
    assert loss > 0.0

    other = DQNNetwork(state_dim=2, hidden_dim=4, action_dim=2, seed=99)
    other.copy_weights_from(net)
    assert other.predict([1.0, 0.5]) == net.predict([1.0, 0.5])

    data = net.to_dict()
    restored_net = DQNNetwork.from_dict(data)
    assert restored_net.predict([1.0, 0.5]) == net.predict([1.0, 0.5])


def test_dqn_agent_lifecycle(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="must be positive"):
        DQNAgent(state_size=0, action_size=2)

    agent = DQNAgent(
        state_size=4,
        action_size=2,
        hidden_dim=8,
        batch_size=2,
        target_update_interval=2,
        seed=42,
    )

    action_explore = agent.select_action([1.0, 2.0, 3.0, 4.0], evaluate=False)
    assert 0 <= action_explore < 2

    agent.epsilon = 0.0
    action_greedy = agent.select_action([1.0, 2.0, 3.0, 4.0], evaluate=True)
    assert 0 <= action_greedy < 2

    assert agent.update() == 0.0

    agent.remember([1.0, 0.0, 0.0, 0.0], 0, 1.0, [0.0, 1.0, 0.0, 0.0], False)
    agent.remember([0.0, 1.0, 0.0, 0.0], 1, -1.0, [0.0, 0.0, 1.0, 0.0], True)

    loss1 = agent.update()
    assert loss1 >= 0.0
    loss2 = agent.update()
    assert loss2 >= 0.0

    agent.epsilon = 1.0
    agent.decay_epsilon()
    assert agent.epsilon < 1.0

    model_file = tmp_path / "model.json"
    agent.save(model_file)
    assert model_file.exists()

    agent2 = DQNAgent(state_size=4, action_size=2, hidden_dim=8)
    agent2.load(model_file)
    assert agent2.epsilon == agent.epsilon


def test_dqn_controller_decisions() -> None:
    scenario = get_preset("webster_four_way")
    inter, plan, _, _ = scenario.build_scenario()
    ctrl = instantiate_controller("dqn", plan, inter)
    assert isinstance(ctrl, DQNController)
    assert ctrl.agent is not None

    ctrl.reset()

    ctx_trans = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={},
    )
    dec_trans = ctrl.decide(ctx_trans)
    assert dec_trans.reason == "in_transition"

    ctx_min = ControllerContext(
        current_time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_min = ctrl.decide(ctx_min)
    assert dec_min.reason == "min_green_enforced"

    ctx_p1 = ControllerContext(
        current_time=30.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_p1 = ctrl.decide(ctx_p1)
    assert dec_p1.reason in ("dqn_phase_switch", "dqn_hold_phase")

    ctx_p2 = ControllerContext(
        current_time=50.0,
        active_phase_id="P2",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_p2 = ctrl.decide(ctx_p2)
    assert dec_p2.reason in ("dqn_phase_switch", "dqn_hold_phase")


def test_train_dqn_execution() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario, reward_type="queue_penalty")

    with pytest.raises(ValidationError, match="episodes must be positive"):
        train_dqn(env=env, episodes=0)

    agent, rewards = train_dqn(env=env, episodes=2, max_steps=4, seed=42)
    assert len(rewards) == 2
    assert agent.epsilon < 1.0


def test_cli_train_dqn_and_run(tmp_path: Path) -> None:
    out = io.StringIO()
    err = io.StringIO()
    model_path = tmp_path / "dqn_model.json"
    code = main(
        [
            "train",
            "--preset",
            "webster_four_way",
            "--algorithm",
            "dqn",
            "--episodes",
            "2",
            "--out-model",
            str(model_path),
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 0
    assert "Deep Q-Network (DQN) Controller Training Complete" in out.getvalue()
    assert model_path.exists()

    out_no_model = io.StringIO()
    code_no_model = main(
        [
            "train",
            "--preset",
            "webster_four_way",
            "--algorithm",
            "dqn",
            "--episodes",
            "1",
        ],
        stdout=out_no_model,
        stderr=err,
    )
    assert code_no_model == 0

    out_run = io.StringIO()
    code_run = main(
        [
            "run",
            "--preset",
            "webster_four_way",
            "--controller",
            "dqn",
            "--duration",
            "10",
        ],
        stdout=out_run,
        stderr=err,
    )
    assert code_run == 0
    assert "Simulation Execution Summary" in out_run.getvalue()
    assert "dqn" in out_run.getvalue()

    out_vis = io.StringIO()
    html_target = tmp_path / "vis_dqn.html"
    code_vis = main(
        [
            "visualize",
            "--preset",
            "webster_four_way",
            "--controller",
            "dqn",
            "--duration",
            "5",
            "--out-html",
            str(html_target),
        ],
        stdout=out_vis,
        stderr=err,
    )
    assert code_vis == 0
    assert html_target.exists()


def test_instantiate_controller_unknown_includes_dqn() -> None:
    scenario = get_preset("webster_four_way")
    inter, plan, _, _ = scenario.build_scenario()
    with pytest.raises(ConfigurationError, match="dqn"):
        instantiate_controller("non-existent-ctrl", plan, inter)
