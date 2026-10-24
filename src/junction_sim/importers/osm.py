import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
from junction_sim.exceptions import ValidationError


class OSMNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    lat: float
    lon: float
    tags: dict[str, str] = Field(default_factory=dict)


class OSMWay(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    nodes: tuple[int, ...]
    tags: dict[str, str] = Field(default_factory=dict)


class OSMData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: dict[int, OSMNode]
    ways: dict[int, OSMWay]


def parse_osm_json(raw: dict[str, Any]) -> OSMData:
    elements = raw.get("elements", [])
    nodes: dict[int, OSMNode] = {}
    ways: dict[int, OSMWay] = {}

    for elem in elements:
        e_type = elem.get("type")
        e_id = elem.get("id")
        if e_type == "node" and e_id is not None:
            nodes[int(e_id)] = OSMNode(
                id=int(e_id),
                lat=float(elem.get("lat", 0.0)),
                lon=float(elem.get("lon", 0.0)),
                tags=dict(elem.get("tags", {})),
            )
        elif e_type == "way" and e_id is not None:
            node_ids = tuple(int(nid) for nid in elem.get("nodes", []))
            ways[int(e_id)] = OSMWay(
                id=int(e_id),
                nodes=node_ids,
                tags=dict(elem.get("tags", {})),
            )

    return OSMData(nodes=nodes, ways=ways)


def infer_approach_direction(dx: float, dy: float) -> Direction:
    angle = math.atan2(dy, dx)
    deg = math.degrees(angle)
    if -45.0 <= deg < 45.0:
        return Direction.WEST
    if 45.0 <= deg < 135.0:
        return Direction.SOUTH
    if -135.0 <= deg < -45.0:
        return Direction.NORTH
    return Direction.EAST


def build_scenario_from_osm(
    osm_data: OSMData,
    center_node_id: int,
    junction_id: str = "osm_junction",
) -> ScenarioConfig:
    if center_node_id not in osm_data.nodes:
        raise ValidationError(f"center node {center_node_id} not found in OSM data")

    center = osm_data.nodes[center_node_id]
    connecting_ways: list[tuple[OSMWay, int]] = []

    for way in osm_data.ways.values():
        if center_node_id in way.nodes:
            idx = way.nodes.index(center_node_id)
            neighbor_id: int | None = None
            if idx > 0:
                neighbor_id = way.nodes[idx - 1]
            elif idx + 1 < len(way.nodes):
                neighbor_id = way.nodes[idx + 1]
            if neighbor_id is not None and neighbor_id in osm_data.nodes:
                connecting_ways.append((way, neighbor_id))

    if len(connecting_ways) < 2:
        raise ValidationError("at least 2 connecting ways required for an intersection")

    approaches: list[ApproachConfig] = []
    movements: list[MovementConfig] = []
    used_dirs: set[Direction] = set()

    dir_candidates = [
        Direction.NORTH,
        Direction.SOUTH,
        Direction.EAST,
        Direction.WEST,
    ]

    for way, n_id in connecting_ways:
        neighbor = osm_data.nodes[n_id]
        dx = neighbor.lon - center.lon
        dy = neighbor.lat - center.lat
        raw_dir = infer_approach_direction(dx, dy)

        chosen_dir = raw_dir
        if chosen_dir in used_dirs:
            for cand in dir_candidates:
                if cand not in used_dirs:
                    chosen_dir = cand
                    break

        used_dirs.add(chosen_dir)
        app_id = f"app_{chosen_dir.value}"
        lane_count = max(1, int(way.tags.get("lanes", "1")))
        mov_id = f"{chosen_dir.value.upper()}_T"

        lanes: list[LaneConfig] = []
        for l_idx in range(lane_count):
            lanes.append(
                LaneConfig(
                    id=f"lane_{chosen_dir.value}_{l_idx}",
                    approach_id=app_id,
                    allowed_movement_ids=[mov_id],
                    max_capacity=50,
                )
            )

        approaches.append(
            ApproachConfig(
                id=app_id,
                direction=chosen_dir,
                lanes=lanes,
            )
        )

        dest_dir = (
            Direction.SOUTH
            if chosen_dir == Direction.NORTH
            else (
                Direction.NORTH
                if chosen_dir == Direction.SOUTH
                else (
                    Direction.WEST if chosen_dir == Direction.EAST else Direction.EAST
                )
            )
        )
        movements.append(
            MovementConfig(
                id=mov_id,
                origin=app_id,
                destination=f"app_{dest_dir.value}",
                turn_type=TurnType.THROUGH,
                saturation_flow_rate=1800.0 * lane_count,
            )
        )

    m_ids = [m.id for m in movements]
    p1_movs = [m for idx, m in enumerate(m_ids) if idx % 2 == 0]
    p2_movs = [m for idx, m in enumerate(m_ids) if idx % 2 == 1]

    conflicts: list[list[str]] = []
    for m1 in p1_movs:
        for m2 in p2_movs:
            if m1 != m2 and [m2, m1] not in conflicts:
                conflicts.append([m1, m2])

    phases = [
        SignalPhaseConfig(
            id="P1",
            green_movement_ids=p1_movs,
            green_duration=30.0,
            yellow_duration=3.0,
            all_red_duration=2.0,
        ),
        SignalPhaseConfig(
            id="P2",
            green_movement_ids=p2_movs,
            green_duration=30.0,
            yellow_duration=3.0,
            all_red_duration=2.0,
        ),
    ]

    inter_cfg = IntersectionConfig(
        id=junction_id,
        approaches=approaches,
        movements=movements,
        conflicting_movement_pairs=conflicts,
    )
    plan_cfg = SignalPlanConfig(
        id=f"plan_{junction_id}",
        phases=phases,
    )
    demands = [
        DemandProfileConfig(movement_id=m.id, flow_rate_vph=300.0) for m in movements
    ]

    return ScenarioConfig(
        intersection=inter_cfg,
        signal_plan=plan_cfg,
        demands=demands,
        simulation=SimulationConfig(duration=60.0, step_size=1.0),
    )
