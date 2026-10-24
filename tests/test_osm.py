import io
import json
from pathlib import Path

import pytest

from junction_sim.cli import main
from junction_sim.domain.direction import Direction
from junction_sim.exceptions import ValidationError
from junction_sim.importers.osm import (
    OSMData,
    OSMNode,
    OSMWay,
    build_scenario_from_osm,
    infer_approach_direction,
    parse_osm_json,
)


def test_osm_models() -> None:
    node = OSMNode(id=1, lat=41.0, lon=29.0, tags={"highway": "traffic_signals"})
    assert node.id == 1
    assert node.lat == 41.0
    assert node.lon == 29.0
    assert node.tags["highway"] == "traffic_signals"

    way = OSMWay(id=10, nodes=(1, 2, 3), tags={"lanes": "2"})
    assert way.id == 10
    assert way.nodes == (1, 2, 3)

    data = OSMData(nodes={1: node}, ways={10: way})
    assert len(data.nodes) == 1
    assert len(data.ways) == 1


def test_parse_osm_json() -> None:
    raw = {
        "elements": [
            {"type": "node", "id": 1, "lat": 40.0, "lon": 30.0},
            {"type": "node", "id": 2, "lat": 40.01, "lon": 30.0},
            {"type": "way", "id": 100, "nodes": [1, 2], "tags": {"lanes": "2"}},
            {"type": "other", "id": 999},
            {"type": "node"},
            {"type": "way"},
        ]
    }
    data = parse_osm_json(raw)
    assert 1 in data.nodes
    assert 2 in data.nodes
    assert 100 in data.ways
    assert data.ways[100].tags["lanes"] == "2"


def test_infer_approach_direction() -> None:
    assert infer_approach_direction(1.0, 0.0) == Direction.WEST
    assert infer_approach_direction(0.0, 1.0) == Direction.SOUTH
    assert infer_approach_direction(0.0, -1.0) == Direction.NORTH
    assert infer_approach_direction(-1.0, 0.0) == Direction.EAST


def test_build_scenario_from_osm_missing_center() -> None:
    data = OSMData(nodes={}, ways={})
    with pytest.raises(ValidationError, match="center node 99 not found"):
        build_scenario_from_osm(data, center_node_id=99)


def test_build_scenario_from_osm_insufficient_ways() -> None:
    nodes = {
        1: OSMNode(id=1, lat=0.0, lon=0.0),
        2: OSMNode(id=2, lat=0.0, lon=1.0),
    }
    ways = {
        10: OSMWay(id=10, nodes=(1, 2)),
    }
    data = OSMData(nodes=nodes, ways=ways)
    with pytest.raises(ValidationError, match="at least 2 connecting ways"):
        build_scenario_from_osm(data, center_node_id=1)


def test_build_scenario_from_osm_valid_four_way() -> None:
    nodes = {
        1: OSMNode(id=1, lat=0.0, lon=0.0),
        2: OSMNode(id=2, lat=0.01, lon=0.0),
        3: OSMNode(id=3, lat=-0.01, lon=0.0),
        4: OSMNode(id=4, lat=0.0, lon=0.01),
        5: OSMNode(id=5, lat=0.0, lon=-0.01),
    }
    ways = {
        10: OSMWay(id=10, nodes=(1, 2), tags={"lanes": "2"}),
        20: OSMWay(id=20, nodes=(3, 1), tags={"lanes": "1"}),
        30: OSMWay(id=30, nodes=(1, 4), tags={"lanes": "2"}),
        40: OSMWay(id=40, nodes=(5, 1), tags={"lanes": "1"}),
    }
    data = OSMData(nodes=nodes, ways=ways)
    scenario = build_scenario_from_osm(data, center_node_id=1, junction_id="test_osm")
    assert scenario.intersection.id == "test_osm"
    assert len(scenario.intersection.approaches) == 4
    inter, plan, demands, sim = scenario.build_scenario()
    assert inter.id == "test_osm"
    assert len(plan.phases) == 2


def test_build_scenario_direction_collision_and_missing_neighbor() -> None:
    nodes = {
        1: OSMNode(id=1, lat=0.0, lon=0.0),
        2: OSMNode(id=2, lat=0.0, lon=0.01),
        3: OSMNode(id=3, lat=0.0, lon=0.02),
        4: OSMNode(id=4, lat=0.0, lon=-0.01),
        5: OSMNode(id=5, lat=0.0, lon=-0.02),
        6: OSMNode(id=6, lat=0.01, lon=0.0),
        100: OSMNode(id=100, lat=1.0, lon=1.0),
        101: OSMNode(id=101, lat=1.0, lon=1.01),
    }
    ways = {
        10: OSMWay(id=10, nodes=(1, 2)),
        20: OSMWay(id=20, nodes=(1, 3)),
        30: OSMWay(id=30, nodes=(1, 4)),
        40: OSMWay(id=40, nodes=(1, 5)),
        50: OSMWay(id=50, nodes=(1, 6)),
        60: OSMWay(id=60, nodes=(1, 999)),
        70: OSMWay(id=70, nodes=(1,)),
        80: OSMWay(id=80, nodes=(100, 101)),
    }
    data = OSMData(nodes=nodes, ways=ways)
    scenario = build_scenario_from_osm(data, center_node_id=1)
    assert len(scenario.intersection.approaches) == 5


def test_cli_import_missing_file(tmp_path: Path) -> None:
    out = io.StringIO()
    err = io.StringIO()
    code = main(
        ["import", "--osm", str(tmp_path / "non_existent.json"), "--node-id", "1"],
        stdout=out,
        stderr=err,
    )
    assert code == 1
    assert "OSM file not found" in err.getvalue()


def test_cli_import_invalid_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("invalid json", encoding="utf-8")
    out = io.StringIO()
    err = io.StringIO()
    code = main(
        ["import", "--osm", str(bad_file), "--node-id", "1"],
        stdout=out,
        stderr=err,
    )
    assert code == 1
    assert "failed to parse JSON" in err.getvalue()


def test_cli_import_success_stdout(tmp_path: Path) -> None:
    osm_file = tmp_path / "osm.json"
    osm_dict = {
        "elements": [
            {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
            {"type": "node", "id": 2, "lat": 0.01, "lon": 0.0},
            {"type": "node", "id": 3, "lat": -0.01, "lon": 0.0},
            {"type": "way", "id": 10, "nodes": [1, 2]},
            {"type": "way", "id": 20, "nodes": [3, 1]},
        ]
    }
    osm_file.write_text(json.dumps(osm_dict), encoding="utf-8")

    out = io.StringIO()
    err = io.StringIO()
    code = main(
        [
            "import",
            "--osm",
            str(osm_file),
            "--node-id",
            "1",
            "--junction-id",
            "osm_custom",
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 0
    assert "osm_custom" in out.getvalue()


def test_cli_import_success_to_file(tmp_path: Path) -> None:
    osm_file = tmp_path / "osm.json"
    osm_dict = {
        "elements": [
            {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
            {"type": "node", "id": 2, "lat": 0.01, "lon": 0.0},
            {"type": "node", "id": 3, "lat": -0.01, "lon": 0.0},
            {"type": "way", "id": 10, "nodes": [1, 2]},
            {"type": "way", "id": 20, "nodes": [3, 1]},
        ]
    }
    osm_file.write_text(json.dumps(osm_dict), encoding="utf-8")
    target_out = tmp_path / "out" / "scenario.json"

    out = io.StringIO()
    err = io.StringIO()
    code = main(
        [
            "import",
            "--osm",
            str(osm_file),
            "--node-id",
            "1",
            "--out",
            str(target_out),
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 0
    assert "Imported OSM scenario saved to" in out.getvalue()
    assert target_out.exists()
