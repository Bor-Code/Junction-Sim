import pytest

from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.engine.engine import SimulationEngine
from junction_sim.exceptions import ConfigurationError
from junction_sim.presets import (
    build_arterial_corridor_preset,
    build_bottleneck_spillback_preset,
    build_peak_hour_surge_preset,
    build_webster_four_way_preset,
    get_preset,
    get_preset_info,
    list_presets,
    list_presets_info,
)


def test_list_presets() -> None:
    presets = list_presets()
    expected = [
        "webster_four_way",
        "arterial_corridor",
        "peak_hour_surge",
        "bottleneck_spillback",
    ]
    assert presets == expected


def test_list_presets_info() -> None:
    info_list = list_presets_info()
    assert len(info_list) == 4
    names = [info.name for info in info_list]
    assert "webster_four_way" in names
    for info in info_list:
        assert len(info.description) > 0


def test_get_preset_info_valid_and_invalid() -> None:
    info = get_preset_info("webster_four_way")
    assert info.name == "webster_four_way"
    assert "Webster" in info.description

    with pytest.raises(ConfigurationError) as exc_info:
        get_preset_info("unknown_preset")
    assert "unknown preset 'unknown_preset'" in str(exc_info.value)


def test_get_preset_valid_and_invalid() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        get_preset("invalid_name")
    assert "unknown preset 'invalid_name'" in str(exc_info.value)

    cfg = get_preset("webster_four_way")
    assert cfg.intersection.id == "webster_four_way"


def test_build_webster_four_way_preset() -> None:
    cfg = build_webster_four_way_preset()
    inter, plan, demands, sim_cfg = cfg.build_scenario()
    assert inter.id == "webster_four_way"
    assert len(inter.approaches) == 4
    assert len(plan.phases) == 2
    assert len(demands) == 4
    assert sim_cfg.duration == 300.0

    ctrl = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )
    steps = engine.run(5.0)
    assert len(steps) == 5


def test_build_arterial_corridor_preset() -> None:
    cfg = build_arterial_corridor_preset()
    inter, plan, demands, sim_cfg = cfg.build_scenario()
    assert inter.id == "arterial_corridor"
    north = next(a for a in inter.approaches if a.id == "north")
    assert len(north.lanes) == 2
    east = next(a for a in inter.approaches if a.id == "east")
    assert len(east.lanes) == 1

    ctrl = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )
    steps = engine.run(5.0)
    assert len(steps) == 5


def test_build_peak_hour_surge_preset() -> None:
    cfg = build_peak_hour_surge_preset()
    inter, plan, demands, sim_cfg = cfg.build_scenario()
    assert inter.id == "peak_hour_surge"
    rates = [d.flow_rate_vph for d in demands]
    assert all(r >= 850.0 for r in rates)

    ctrl = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )
    steps = engine.run(5.0)
    assert len(steps) == 5


def test_build_bottleneck_spillback_preset() -> None:
    cfg = build_bottleneck_spillback_preset()
    inter, plan, demands, sim_cfg = cfg.build_scenario()
    assert inter.id == "bottleneck_spillback"
    for app in inter.approaches:
        for lane in app.lanes:
            assert lane.max_capacity == 15

    ctrl = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl,
        step_size=sim_cfg.step_size,
        seed=sim_cfg.seed,
    )
    steps = engine.run(5.0)
    assert len(steps) == 5
