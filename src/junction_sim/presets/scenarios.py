from collections.abc import Callable
from typing import Final

from pydantic import BaseModel, ConfigDict

from junction_sim.config.schema import (
    ApproachConfig,
    DemandProfileConfig,
    IntersectionConfig,
    LaneConfig,
    MovementConfig,
    ScenarioConfig,
    SignalPhaseConfig,
    SignalPlanConfig,
    SimulationConfig,
)
from junction_sim.domain.direction import Direction
from junction_sim.domain.movement import TurnType
from junction_sim.domain.network import (
    IntersectionNetwork,
    IntersectionNode,
    RoadLink,
)
from junction_sim.exceptions import ConfigurationError


class PresetInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str


def build_webster_four_way_preset() -> ScenarioConfig:
    return ScenarioConfig(
        intersection=IntersectionConfig(
            id="webster_four_way",
            approaches=[
                ApproachConfig(
                    id="north",
                    direction=Direction.NORTH,
                    lanes=[
                        LaneConfig(
                            id="lane_n_0",
                            approach_id="north",
                            allowed_movement_ids=["N_T"],
                            max_capacity=50,
                        )
                    ],
                ),
                ApproachConfig(
                    id="south",
                    direction=Direction.SOUTH,
                    lanes=[
                        LaneConfig(
                            id="lane_s_0",
                            approach_id="south",
                            allowed_movement_ids=["S_T"],
                            max_capacity=50,
                        )
                    ],
                ),
                ApproachConfig(
                    id="east",
                    direction=Direction.EAST,
                    lanes=[
                        LaneConfig(
                            id="lane_e_0",
                            approach_id="east",
                            allowed_movement_ids=["E_T"],
                            max_capacity=50,
                        )
                    ],
                ),
                ApproachConfig(
                    id="west",
                    direction=Direction.WEST,
                    lanes=[
                        LaneConfig(
                            id="lane_w_0",
                            approach_id="west",
                            allowed_movement_ids=["W_T"],
                            max_capacity=50,
                        )
                    ],
                ),
            ],
            movements=[
                MovementConfig(
                    id="N_T",
                    origin="north",
                    destination="south",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="S_T",
                    origin="south",
                    destination="north",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="E_T",
                    origin="east",
                    destination="west",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="W_T",
                    origin="west",
                    destination="east",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
            ],
            conflicting_movement_pairs=[
                ["N_T", "E_T"],
                ["N_T", "W_T"],
                ["S_T", "E_T"],
                ["S_T", "W_T"],
            ],
        ),
        signal_plan=SignalPlanConfig(
            id="plan_webster_four_way",
            phases=[
                SignalPhaseConfig(
                    id="P1",
                    green_movement_ids=["N_T", "S_T"],
                    green_duration=25.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=5.0,
                    max_green=45.0,
                ),
                SignalPhaseConfig(
                    id="P2",
                    green_movement_ids=["E_T", "W_T"],
                    green_duration=25.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=5.0,
                    max_green=45.0,
                ),
            ],
        ),
        demands=[
            DemandProfileConfig(movement_id="N_T", flow_rate_vph=400.0),
            DemandProfileConfig(movement_id="S_T", flow_rate_vph=400.0),
            DemandProfileConfig(movement_id="E_T", flow_rate_vph=400.0),
            DemandProfileConfig(movement_id="W_T", flow_rate_vph=400.0),
        ],
        simulation=SimulationConfig(duration=300.0, step_size=1.0, seed=42),
    )


def build_arterial_corridor_preset() -> ScenarioConfig:
    return ScenarioConfig(
        intersection=IntersectionConfig(
            id="arterial_corridor",
            approaches=[
                ApproachConfig(
                    id="north",
                    direction=Direction.NORTH,
                    lanes=[
                        LaneConfig(
                            id="lane_n_0",
                            approach_id="north",
                            allowed_movement_ids=["N_T"],
                            max_capacity=60,
                        ),
                        LaneConfig(
                            id="lane_n_1",
                            approach_id="north",
                            allowed_movement_ids=["N_T"],
                            max_capacity=60,
                        ),
                    ],
                ),
                ApproachConfig(
                    id="south",
                    direction=Direction.SOUTH,
                    lanes=[
                        LaneConfig(
                            id="lane_s_0",
                            approach_id="south",
                            allowed_movement_ids=["S_T"],
                            max_capacity=60,
                        ),
                        LaneConfig(
                            id="lane_s_1",
                            approach_id="south",
                            allowed_movement_ids=["S_T"],
                            max_capacity=60,
                        ),
                    ],
                ),
                ApproachConfig(
                    id="east",
                    direction=Direction.EAST,
                    lanes=[
                        LaneConfig(
                            id="lane_e_0",
                            approach_id="east",
                            allowed_movement_ids=["E_T"],
                            max_capacity=30,
                        )
                    ],
                ),
                ApproachConfig(
                    id="west",
                    direction=Direction.WEST,
                    lanes=[
                        LaneConfig(
                            id="lane_w_0",
                            approach_id="west",
                            allowed_movement_ids=["W_T"],
                            max_capacity=30,
                        )
                    ],
                ),
            ],
            movements=[
                MovementConfig(
                    id="N_T",
                    origin="north",
                    destination="south",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=3600.0,
                ),
                MovementConfig(
                    id="S_T",
                    origin="south",
                    destination="north",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=3600.0,
                ),
                MovementConfig(
                    id="E_T",
                    origin="east",
                    destination="west",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="W_T",
                    origin="west",
                    destination="east",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
            ],
            conflicting_movement_pairs=[
                ["N_T", "E_T"],
                ["N_T", "W_T"],
                ["S_T", "E_T"],
                ["S_T", "W_T"],
            ],
        ),
        signal_plan=SignalPlanConfig(
            id="plan_arterial_corridor",
            phases=[
                SignalPhaseConfig(
                    id="P1",
                    green_movement_ids=["N_T", "S_T"],
                    green_duration=40.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=10.0,
                    max_green=60.0,
                ),
                SignalPhaseConfig(
                    id="P2",
                    green_movement_ids=["E_T", "W_T"],
                    green_duration=15.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=5.0,
                    max_green=30.0,
                ),
            ],
        ),
        demands=[
            DemandProfileConfig(movement_id="N_T", flow_rate_vph=800.0),
            DemandProfileConfig(movement_id="S_T", flow_rate_vph=800.0),
            DemandProfileConfig(movement_id="E_T", flow_rate_vph=150.0),
            DemandProfileConfig(movement_id="W_T", flow_rate_vph=150.0),
        ],
        simulation=SimulationConfig(duration=300.0, step_size=1.0, seed=42),
    )


def build_peak_hour_surge_preset() -> ScenarioConfig:
    return ScenarioConfig(
        intersection=IntersectionConfig(
            id="peak_hour_surge",
            approaches=[
                ApproachConfig(
                    id="north",
                    direction=Direction.NORTH,
                    lanes=[
                        LaneConfig(
                            id="lane_n_0",
                            approach_id="north",
                            allowed_movement_ids=["N_T"],
                            max_capacity=50,
                        )
                    ],
                ),
                ApproachConfig(
                    id="south",
                    direction=Direction.SOUTH,
                    lanes=[
                        LaneConfig(
                            id="lane_s_0",
                            approach_id="south",
                            allowed_movement_ids=["S_T"],
                            max_capacity=50,
                        )
                    ],
                ),
                ApproachConfig(
                    id="east",
                    direction=Direction.EAST,
                    lanes=[
                        LaneConfig(
                            id="lane_e_0",
                            approach_id="east",
                            allowed_movement_ids=["E_T"],
                            max_capacity=50,
                        )
                    ],
                ),
                ApproachConfig(
                    id="west",
                    direction=Direction.WEST,
                    lanes=[
                        LaneConfig(
                            id="lane_w_0",
                            approach_id="west",
                            allowed_movement_ids=["W_T"],
                            max_capacity=50,
                        )
                    ],
                ),
            ],
            movements=[
                MovementConfig(
                    id="N_T",
                    origin="north",
                    destination="south",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="S_T",
                    origin="south",
                    destination="north",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="E_T",
                    origin="east",
                    destination="west",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="W_T",
                    origin="west",
                    destination="east",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
            ],
            conflicting_movement_pairs=[
                ["N_T", "E_T"],
                ["N_T", "W_T"],
                ["S_T", "E_T"],
                ["S_T", "W_T"],
            ],
        ),
        signal_plan=SignalPlanConfig(
            id="plan_peak_hour_surge",
            phases=[
                SignalPhaseConfig(
                    id="P1",
                    green_movement_ids=["N_T", "S_T"],
                    green_duration=30.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=10.0,
                    max_green=60.0,
                ),
                SignalPhaseConfig(
                    id="P2",
                    green_movement_ids=["E_T", "W_T"],
                    green_duration=30.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=10.0,
                    max_green=60.0,
                ),
            ],
        ),
        demands=[
            DemandProfileConfig(movement_id="N_T", flow_rate_vph=900.0),
            DemandProfileConfig(movement_id="S_T", flow_rate_vph=850.0),
            DemandProfileConfig(movement_id="E_T", flow_rate_vph=900.0),
            DemandProfileConfig(movement_id="W_T", flow_rate_vph=850.0),
        ],
        simulation=SimulationConfig(duration=300.0, step_size=1.0, seed=42),
    )


def build_bottleneck_spillback_preset() -> ScenarioConfig:
    return ScenarioConfig(
        intersection=IntersectionConfig(
            id="bottleneck_spillback",
            approaches=[
                ApproachConfig(
                    id="north",
                    direction=Direction.NORTH,
                    lanes=[
                        LaneConfig(
                            id="lane_n_0",
                            approach_id="north",
                            allowed_movement_ids=["N_T"],
                            max_capacity=15,
                        )
                    ],
                ),
                ApproachConfig(
                    id="south",
                    direction=Direction.SOUTH,
                    lanes=[
                        LaneConfig(
                            id="lane_s_0",
                            approach_id="south",
                            allowed_movement_ids=["S_T"],
                            max_capacity=15,
                        )
                    ],
                ),
                ApproachConfig(
                    id="east",
                    direction=Direction.EAST,
                    lanes=[
                        LaneConfig(
                            id="lane_e_0",
                            approach_id="east",
                            allowed_movement_ids=["E_T"],
                            max_capacity=15,
                        )
                    ],
                ),
                ApproachConfig(
                    id="west",
                    direction=Direction.WEST,
                    lanes=[
                        LaneConfig(
                            id="lane_w_0",
                            approach_id="west",
                            allowed_movement_ids=["W_T"],
                            max_capacity=15,
                        )
                    ],
                ),
            ],
            movements=[
                MovementConfig(
                    id="N_T",
                    origin="north",
                    destination="south",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="S_T",
                    origin="south",
                    destination="north",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="E_T",
                    origin="east",
                    destination="west",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
                MovementConfig(
                    id="W_T",
                    origin="west",
                    destination="east",
                    turn_type=TurnType.THROUGH,
                    saturation_flow_rate=1800.0,
                ),
            ],
            conflicting_movement_pairs=[
                ["N_T", "E_T"],
                ["N_T", "W_T"],
                ["S_T", "E_T"],
                ["S_T", "W_T"],
            ],
        ),
        signal_plan=SignalPlanConfig(
            id="plan_bottleneck_spillback",
            phases=[
                SignalPhaseConfig(
                    id="P1",
                    green_movement_ids=["N_T", "S_T"],
                    green_duration=20.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=5.0,
                    max_green=40.0,
                ),
                SignalPhaseConfig(
                    id="P2",
                    green_movement_ids=["E_T", "W_T"],
                    green_duration=20.0,
                    yellow_duration=3.0,
                    all_red_duration=1.0,
                    min_green=5.0,
                    max_green=40.0,
                ),
            ],
        ),
        demands=[
            DemandProfileConfig(movement_id="N_T", flow_rate_vph=750.0),
            DemandProfileConfig(movement_id="S_T", flow_rate_vph=750.0),
            DemandProfileConfig(movement_id="E_T", flow_rate_vph=300.0),
            DemandProfileConfig(movement_id="W_T", flow_rate_vph=300.0),
        ],
        simulation=SimulationConfig(duration=300.0, step_size=1.0, seed=42),
    )


_PRESET_BUILDERS: Final[dict[str, tuple[str, Callable[[], ScenarioConfig]]]] = {
    "webster_four_way": (
        "Classic Webster (1958) symmetric four-way intersection under balanced demand",
        build_webster_four_way_preset,
    ),
    "arterial_corridor": (
        "Arterial corridor with heavy major street and low-demand cross-street",
        build_arterial_corridor_preset,
    ),
    "peak_hour_surge": (
        "High-density peak hour surge approaching intersection saturation capacity",
        build_peak_hour_surge_preset,
    ),
    "bottleneck_spillback": (
        "Constrained lane storage intersection exhibiting queue spillback dynamics",
        build_bottleneck_spillback_preset,
    ),
}


def list_presets() -> list[str]:
    return list(_PRESET_BUILDERS.keys())


def list_presets_info() -> list[PresetInfo]:
    return [
        PresetInfo(name=name, description=desc)
        for name, (desc, _) in _PRESET_BUILDERS.items()
    ]


def get_preset_info(name: str) -> PresetInfo:
    if name not in _PRESET_BUILDERS:
        available = ", ".join(list_presets())
        raise ConfigurationError(
            f"unknown preset '{name}', available presets: {available}"
        )
    desc, _ = _PRESET_BUILDERS[name]
    return PresetInfo(name=name, description=desc)


def get_preset(name: str) -> ScenarioConfig:
    if name not in _PRESET_BUILDERS:
        available = ", ".join(list_presets())
        raise ConfigurationError(
            f"unknown preset '{name}', available presets: {available}"
        )
    _, builder = _PRESET_BUILDERS[name]
    return builder()


def build_two_junction_corridor_network() -> IntersectionNetwork:
    sc1 = build_webster_four_way_preset()
    sc2 = build_webster_four_way_preset()
    int1, plan1, demands1, _ = sc1.build_scenario()
    int2, plan2, demands2, _ = sc2.build_scenario()

    node1 = IntersectionNode(
        id="junc_1",
        intersection=int1,
        signal_plan=plan1,
        demands=demands1,
    )
    node2 = IntersectionNode(
        id="junc_2",
        intersection=int2,
        signal_plan=plan2,
        demands=demands2,
    )

    link12 = RoadLink(
        id="link_1_to_2",
        source_node_id="junc_1",
        source_movement_id="W_T",
        target_node_id="junc_2",
        target_lane_id="lane_e_0",
        length=200.0,
        free_flow_speed=13.89,
    )
    link21 = RoadLink(
        id="link_2_to_1",
        source_node_id="junc_2",
        source_movement_id="E_T",
        target_node_id="junc_1",
        target_lane_id="lane_w_0",
        length=200.0,
        free_flow_speed=13.89,
    )

    return IntersectionNetwork(
        id="corridor_two_junction",
        nodes={"junc_1": node1, "junc_2": node2},
        links=(link12, link21),
    )
