import pytest

from junction_sim.controllers.protocol import ControllerContext
from junction_sim.domain.signal import SignalState
from junction_sim.exceptions import ConfigurationError, ValidationError
from junction_sim.presets import get_preset
from junction_sim.rl import JunctionEnv, RLController


def test_rl_controller_direct() -> None:
    scenario = get_preset("webster_four_way")
    _, plan, _, _ = scenario.build_scenario()

    ctrl = RLController(signal_plan=plan)
    context_normal = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )

    d1 = ctrl.decide(context_normal)
    assert d1.target_phase_id is None
    assert d1.reason == "rl_action"

    ctrl.set_target_phase_id("P2")
    d2 = ctrl.decide(context_normal)
    assert d2.target_phase_id == "P2"

    context_transition = ControllerContext(
        current_time=12.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={},
    )
    d_trans = ctrl.decide(context_transition)
    assert d_trans.target_phase_id is None
    assert d_trans.reason == "in_transition"

    ctrl.reset()
    d3 = ctrl.decide(context_normal)
    assert d3.target_phase_id is None


def test_junction_env_init_and_properties() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario, reward_type="queue_penalty", duration=100.0)

    assert env.action_size == 2
    assert env.observation_size == 4 + 2 + 2
    assert len(env.lane_ids) == 4
    assert env.current_time == 0.0
    env.reset()
    assert env.current_time == 0.0
    env.step(0)
    assert env.current_time == 1.0


def test_junction_env_invalid_reward_type() -> None:
    scenario = get_preset("webster_four_way")
    with pytest.raises(ConfigurationError) as exc_info:
        JunctionEnv(scenario=scenario, reward_type="invalid_reward")
    assert "unsupported reward_type 'invalid_reward'" in str(exc_info.value)


def test_junction_env_reset_and_observation_uninitialized() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario)

    uninit_obs = env._get_observation()
    assert uninit_obs == [0.0] * env.observation_size

    obs, info = env.reset(seed=123)
    assert len(obs) == env.observation_size
    assert info["step_index"] == 0
    assert info["current_time"] == 0.0
    assert info["active_phase_id"] == "P1"
    assert info["signal_state"] == "green"


def test_junction_env_step_invalid_action() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario)
    env.reset()

    with pytest.raises(ValidationError):
        env.step(-1)

    with pytest.raises(ValidationError):
        env.step(5)


def test_junction_env_step_without_prior_reset() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario)
    obs, reward, terminated, truncated, info = env.step(0)
    assert len(obs) == env.observation_size
    assert not terminated
    assert not truncated
    assert info["step_index"] == 0


def test_junction_env_reward_types() -> None:
    scenario = get_preset("webster_four_way")

    env_q = JunctionEnv(scenario=scenario, reward_type="queue_penalty")
    env_q.reset(seed=42)
    _, r_q, _, _, _ = env_q.step(0)
    assert r_q <= 0.0

    env_d = JunctionEnv(scenario=scenario, reward_type="delay_penalty")
    env_d.reset(seed=42)
    has_discharged_delay = False
    for _ in range(30):
        _, r_d, _, _, _ = env_d.step(0)
        if r_d < 0.0:
            has_discharged_delay = True
            break
    assert has_discharged_delay

    env_t = JunctionEnv(scenario=scenario, reward_type="throughput")
    env_t.reset(seed=42)
    _, r_t, _, _, _ = env_t.step(0)
    assert r_t >= 0.0


def test_junction_env_signal_state_encodings_and_truncation() -> None:
    scenario = get_preset("webster_four_way")
    env = JunctionEnv(scenario=scenario, duration=35.0)
    env.reset(seed=42)

    seen_states: set[float] = set()
    truncated = False

    for _ in range(45):
        obs, _, _, truncated, _ = env.step(1)
        state_feature = obs[-2]
        seen_states.add(state_feature)
        if truncated:
            break

    assert truncated
    assert 1.0 in seen_states
    assert 0.5 in seen_states
    assert 0.0 in seen_states


def test_junction_env_seed_determinism() -> None:
    scenario = get_preset("webster_four_way")

    env1 = JunctionEnv(scenario=scenario)
    env2 = JunctionEnv(scenario=scenario)

    obs1, _ = env1.reset(seed=777)
    obs2, _ = env2.reset(seed=777)
    assert obs1 == obs2

    actions = [0, 1, 1, 0, 1, 0, 0, 1]
    for act in actions:
        o1, r1, term1, trunc1, info1 = env1.step(act)
        o2, r2, term2, trunc2, info2 = env2.step(act)
        assert o1 == o2
        assert r1 == r2
        assert term1 == term2
        assert trunc1 == trunc2
        assert info1 == info2
