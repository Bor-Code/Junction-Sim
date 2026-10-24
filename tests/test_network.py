import pytest

from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.domain.network import (
    IntersectionNetwork,
    IntersectionNode,
    RoadLink,
)
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.network_engine import (
    InTransitVehicle,
    NetworkSimulationEngine,
    NetworkStepResult,
)
from junction_sim.exceptions import InvalidGeometryError, ValidationError
from junction_sim.presets.scenarios import (
    build_two_junction_corridor_network,
    build_webster_four_way_preset,
)


def create_simple_network() -> IntersectionNetwork:
    return build_two_junction_corridor_network()


def test_road_link_properties() -> None:
    link = RoadLink(
        id="link_1",
        source_node_id="junc_1",
        source_movement_id="W_T",
        target_node_id="junc_2",
        target_lane_id="lane_e_0",
        length=200.0,
        free_flow_speed=10.0,
    )
    assert link.id == "link_1"
    assert link.travel_time == 20.0


def test_intersection_node_validation() -> None:
    sc = build_webster_four_way_preset()
    inter, plan, demands, _ = sc.build_scenario()
    ctrl = FixedTimeController(signal_plan=plan)

    node = IntersectionNode(
        id="node_a",
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl,
    )
    assert node.id == "node_a"
    assert node.controller is ctrl

    with pytest.raises(ValidationError, match="controller must implement"):
        IntersectionNode(
            id="node_b",
            intersection=inter,
            signal_plan=plan,
            demands=demands,
            controller="not_a_controller",
        )


def test_network_topology_validations() -> None:
    net = create_simple_network()
    node1 = net.nodes["junc_1"]
    node2 = net.nodes["junc_2"]

    with pytest.raises(ValidationError, match="node key 'wrong_key' does not match"):
        IntersectionNetwork(
            id="bad_net",
            nodes={"wrong_key": node1},
            links=(),
        )

    link_dup = RoadLink(
        id="dup_link",
        source_node_id="junc_1",
        source_movement_id="W_T",
        target_node_id="junc_2",
        target_lane_id="lane_e_0",
        length=100.0,
    )
    with pytest.raises(ValidationError, match="duplicate link id"):
        IntersectionNetwork(
            id="dup_net",
            nodes={"junc_1": node1, "junc_2": node2},
            links=(link_dup, link_dup),
        )

    bad_src_link = RoadLink(
        id="l_bad_src",
        source_node_id="nonexistent_src",
        source_movement_id="W_T",
        target_node_id="junc_2",
        target_lane_id="lane_e_0",
        length=100.0,
    )
    with pytest.raises(InvalidGeometryError, match="references unknown source node"):
        IntersectionNetwork(
            id="net_bad_src",
            nodes={"junc_1": node1, "junc_2": node2},
            links=(bad_src_link,),
        )

    bad_tgt_link = RoadLink(
        id="l_bad_tgt",
        source_node_id="junc_1",
        source_movement_id="W_T",
        target_node_id="nonexistent_tgt",
        target_lane_id="lane_e_0",
        length=100.0,
    )
    with pytest.raises(InvalidGeometryError, match="references unknown target node"):
        IntersectionNetwork(
            id="net_bad_tgt",
            nodes={"junc_1": node1, "junc_2": node2},
            links=(bad_tgt_link,),
        )

    loop_link = RoadLink(
        id="l_loop",
        source_node_id="junc_1",
        source_movement_id="W_T",
        target_node_id="junc_1",
        target_lane_id="lane_w_0",
        length=100.0,
    )
    with pytest.raises(ValidationError, match="self-loops"):
        IntersectionNetwork(
            id="net_loop",
            nodes={"junc_1": node1, "junc_2": node2},
            links=(loop_link,),
        )

    bad_lane_link = RoadLink(
        id="l_bad_lane",
        source_node_id="junc_1",
        source_movement_id="W_T",
        target_node_id="junc_2",
        target_lane_id="nonexistent_lane",
        length=100.0,
    )
    with pytest.raises(InvalidGeometryError, match="target lane"):
        IntersectionNetwork(
            id="net_bad_lane",
            nodes={"junc_1": node1, "junc_2": node2},
            links=(bad_lane_link,),
        )


def test_network_helper_queries() -> None:
    net = create_simple_network()
    assert net.get_node("junc_1").id == "junc_1"

    with pytest.raises(InvalidGeometryError, match="unknown node id"):
        net.get_node("unknown_node")

    out_1 = net.get_outgoing_links("junc_1")
    assert len(out_1) == 1
    assert out_1[0].id == "link_1_to_2"

    in_1 = net.get_incoming_links("junc_1")
    assert len(in_1) == 1
    assert in_1[0].id == "link_2_to_1"

    with pytest.raises(InvalidGeometryError):
        net.get_outgoing_links("missing_node")

    with pytest.raises(InvalidGeometryError):
        net.get_incoming_links("missing_node")


def test_network_simulation_engine_initialization() -> None:
    net = create_simple_network()

    with pytest.raises(ValidationError, match="step_size must be greater than zero"):
        NetworkSimulationEngine(network=net, step_size=0.0)

    engine = NetworkSimulationEngine(network=net, step_size=1.0, seed=42)
    assert engine.network is net
    assert engine.step_size == 1.0
    assert engine.current_time == 0.0

    eng1 = engine.get_engine("junc_1")
    assert eng1 is not None

    with pytest.raises(InvalidGeometryError, match="unknown node id"):
        engine.get_engine("fake_node")

    assert engine.get_transit_vehicles("link_1_to_2") == ()
    with pytest.raises(InvalidGeometryError, match="unknown link id"):
        engine.get_transit_vehicles("fake_link")


def test_network_simulation_engine_step_and_run() -> None:
    net = create_simple_network()
    engine = NetworkSimulationEngine(network=net, step_size=1.0, seed=123)

    res = engine.step()
    assert isinstance(res, NetworkStepResult)
    assert res.step_index == 0
    assert res.time == 0.0
    assert "junc_1" in res.node_results
    assert "junc_2" in res.node_results
    assert res.total_in_transit >= 0
    assert res.total_network_arrivals >= 0
    assert res.total_network_discharges >= 0
    assert res.network_max_queue >= 0

    results = engine.run(duration=10.0)
    assert len(results) == 10
    assert engine.current_time == 11.0

    with pytest.raises(ValidationError, match="duration must be greater than zero"):
        engine.run(duration=0.0)


def test_network_transit_vehicle_transfer() -> None:
    net = create_simple_network()
    engine = NetworkSimulationEngine(network=net, step_size=1.0, seed=999)

    v1 = Vehicle(
        id="veh_transfer_1",
        origin="east",
        destination="west",
        arrival_time=0.0,
    )
    tv = InTransitVehicle(
        vehicle=v1,
        entry_time=0.0,
        exit_time=0.0,
        link_id="link_1_to_2",
        target_node_id="junc_2",
        target_lane_id="lane_e_0",
    )
    tv_future = InTransitVehicle(
        vehicle=v1,
        entry_time=0.0,
        exit_time=50.0,
        link_id="link_1_to_2",
        target_node_id="junc_2",
        target_lane_id="lane_e_0",
    )
    engine._transit["link_1_to_2"].extend([tv, tv_future])

    engine.step()
    assert len(engine._transit["link_1_to_2"]) == 1


def test_network_discharged_vehicle_entering_link() -> None:
    sc1 = build_webster_four_way_preset()
    sc2 = build_webster_four_way_preset()
    int1, plan1, _, _ = sc1.build_scenario()
    int2, plan2, _, _ = sc2.build_scenario()

    node1 = IntersectionNode(
        id="n1",
        intersection=int1,
        signal_plan=plan1,
        demands=(),
    )
    node2 = IntersectionNode(
        id="n2",
        intersection=int2,
        signal_plan=plan2,
        demands=(),
    )
    link = RoadLink(
        id="l12",
        source_node_id="n1",
        source_movement_id="N_T",
        target_node_id="n2",
        target_lane_id="lane_s_0",
        length=50.0,
        free_flow_speed=10.0,
    )
    net = IntersectionNetwork(
        id="net_test",
        nodes={"n1": node1, "n2": node2},
        links=(link,),
    )
    engine = NetworkSimulationEngine(network=net, step_size=4.0, seed=55)

    v_dep = Vehicle(
        id="veh_out",
        origin="north",
        destination="south",
        target_lane_id="lane_n_0",
        arrival_time=0.0,
    )
    engine.get_engine("n1").enqueue_vehicle(v_dep, "lane_n_0")

    v_no_mov = Vehicle(
        id="veh_no_link",
        origin="south",
        destination="north",
        target_lane_id="lane_s_0",
        arrival_time=0.0,
    )
    engine.get_engine("n1").enqueue_vehicle(v_no_mov, "lane_s_0")

    v_no_match = Vehicle(
        id="veh_no_match",
        origin="north",
        destination="east",
        target_lane_id="lane_n_0",
        arrival_time=0.0,
    )
    engine.get_engine("n1").enqueue_vehicle(v_no_match, "lane_n_0")

    step_res = engine.step()
    assert step_res.time == 0.0
    transit_vehs = engine.get_transit_vehicles("l12")
    assert len(transit_vehs) >= 1
    assert any(tv.vehicle.id == "veh_out" for tv in transit_vehs)


def test_simulation_engine_enqueue_vehicle() -> None:
    sc = build_webster_four_way_preset()
    inter, plan, demands, sim_cfg = sc.build_scenario()
    from junction_sim.engine.engine import SimulationEngine

    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        step_size=sim_cfg.step_size,
    )
    v = Vehicle(id="v_manual", origin="north", destination="south", arrival_time=0.0)
    engine.enqueue_vehicle(v, "lane_n_0")
    assert engine.get_queue_length("lane_n_0") >= 1

    with pytest.raises(InvalidGeometryError, match="unknown lane id"):
        engine.enqueue_vehicle(v, "unknown_lane")


def test_network_step_result_empty_queues() -> None:
    from junction_sim.engine.step_result import StepResult
    from junction_sim.engine.transition import SignalState

    empty_step = StepResult(
        step_index=0,
        time=0.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={},
    )
    res = NetworkStepResult(
        step_index=0,
        time=0.0,
        node_results={"node1": empty_step},
        transit_vehicle_counts={"l1": 0},
    )
    assert res.network_max_queue == 0
