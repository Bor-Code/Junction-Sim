from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.transition import SignalState


def create_scenario_network(
    demand_n: float,
    demand_s: float,
    demand_e: float,
    demand_w: float,
    p1_min_green: float = 5.0,
    p1_green_duration: float = 25.0,
    p1_max_green: float = 40.0,
    p2_min_green: float = 5.0,
    p2_green_duration: float = 25.0,
    p2_max_green: float = 40.0,
) -> tuple[Intersection, SignalPlan, tuple[DemandProfile, ...]]:
    mov_n_t = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_s_t = Movement(
        id="S_T",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_e_t = Movement(
        id="E_T",
        origin="east",
        destination="west",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_w_t = Movement(
        id="W_T",
        origin="west",
        destination="east",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )

    lane_n = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_T",),
        max_capacity=200,
    )
    lane_s = Lane(
        id="lane_s_0",
        approach_id="south",
        allowed_movement_ids=("S_T",),
        max_capacity=200,
    )
    lane_e = Lane(
        id="lane_e_0",
        approach_id="east",
        allowed_movement_ids=("E_T",),
        max_capacity=200,
    )
    lane_w = Lane(
        id="lane_w_0",
        approach_id="west",
        allowed_movement_ids=("W_T",),
        max_capacity=200,
    )

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    app_e = Approach(id="east", direction=Direction.EAST, lanes=(lane_e,))
    app_w = Approach(id="west", direction=Direction.WEST, lanes=(lane_w,))

    conflicts = frozenset(
        {
            frozenset({"N_T", "E_T"}),
            frozenset({"N_T", "W_T"}),
            frozenset({"S_T", "E_T"}),
            frozenset({"S_T", "W_T"}),
        }
    )

    intersection = Intersection(
        id="mp_scenario_int",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )

    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        min_green=p1_min_green,
        green_duration=p1_green_duration,
        max_green=p1_max_green,
        yellow_duration=3.0,
        all_red_duration=1.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        min_green=p2_min_green,
        green_duration=p2_green_duration,
        max_green=p2_max_green,
        yellow_duration=3.0,
        all_red_duration=1.0,
    )
    signal_plan = SignalPlan(id="mp_scenario_plan", phases=(phase_1, phase_2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=demand_n),
        DemandProfile(movement_id="S_T", flow_rate_vph=demand_s),
        DemandProfile(movement_id="E_T", flow_rate_vph=demand_e),
        DemandProfile(movement_id="W_T", flow_rate_vph=demand_w),
    )

    return intersection, signal_plan, demands


def test_max_pressure_vs_fixed_time_asymmetric_demand() -> None:
    intersection, plan, demands = create_scenario_network(
        demand_n=850.0,
        demand_s=850.0,
        demand_e=70.0,
        demand_w=70.0,
        p1_min_green=5.0,
        p1_green_duration=25.0,
        p1_max_green=40.0,
        p2_min_green=5.0,
        p2_green_duration=25.0,
        p2_max_green=40.0,
    )

    fixed_ctrl = FixedTimeController(plan)
    fixed_engine = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=42,
        controller=fixed_ctrl,
    )

    mp_ctrl = MaxPressureController(signal_plan=plan, intersection=intersection)
    mp_engine = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=42,
        controller=mp_ctrl,
    )

    fixed_results = fixed_engine.run(300.0)
    mp_results = mp_engine.run(300.0)

    fixed_discharged = sum(len(r.discharged_vehicles) for r in fixed_results)
    mp_discharged = sum(len(r.discharged_vehicles) for r in mp_results)

    fixed_final_queue = sum(fixed_results[-1].queue_lengths.values())
    mp_final_queue = sum(mp_results[-1].queue_lengths.values())

    assert mp_discharged > fixed_discharged
    assert mp_final_queue < fixed_final_queue

    mp_reasons = {
        res.controller_decision.reason
        for res in mp_results
        if res.controller_decision is not None
    }
    assert "max_pressure_switch" in mp_reasons
    assert "max_pressure_hold" in mp_reasons
    assert "min_green_hold" in mp_reasons
    assert "in_transition" in mp_reasons


def test_max_pressure_isolated_stream_hold_in_green() -> None:
    intersection, plan, demands = create_scenario_network(
        demand_n=650.0,
        demand_s=650.0,
        demand_e=0.0,
        demand_w=0.0,
        p1_min_green=5.0,
        p1_green_duration=20.0,
        p1_max_green=30.0,
        p2_min_green=5.0,
        p2_green_duration=20.0,
        p2_max_green=30.0,
    )

    controller = MaxPressureController(signal_plan=plan, intersection=intersection)
    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=101,
        controller=controller,
    )

    results = engine.run(150.0)

    for res in results:
        assert res.active_phase_id == "P1"
        assert res.signal_state == SignalState.GREEN

    hold_reasons = [
        res.controller_decision.reason
        for res in results
        if res.controller_decision is not None
        and res.controller_decision.reason == "max_pressure_hold"
    ]
    assert len(hold_reasons) > 0
    assert engine.active_phase_id == "P1"
    assert engine.signal_state == SignalState.GREEN


def test_max_pressure_high_saturation_max_green_behavior() -> None:
    intersection, plan, demands = create_scenario_network(
        demand_n=1400.0,
        demand_s=1400.0,
        demand_e=200.0,
        demand_w=200.0,
        p1_min_green=5.0,
        p1_green_duration=15.0,
        p1_max_green=15.0,
        p2_min_green=5.0,
        p2_green_duration=15.0,
        p2_max_green=15.0,
    )

    controller = MaxPressureController(signal_plan=plan, intersection=intersection)
    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=77,
        controller=controller,
    )

    results = engine.run(200.0)

    max_green_events = [
        res
        for res in results
        if res.controller_decision is not None
        and res.controller_decision.reason == "max_green"
    ]
    assert len(max_green_events) >= 4

    p1_served = any(
        res.active_phase_id == "P1" and res.signal_state == SignalState.GREEN
        for res in results
    )
    p2_served = any(
        res.active_phase_id == "P2" and res.signal_state == SignalState.GREEN
        for res in results
    )
    assert p1_served
    assert p2_served

    discharged_n = sum(
        1 for r in results for v in r.discharged_vehicles if v.origin == "north"
    )
    discharged_e = sum(
        1 for r in results for v in r.discharged_vehicles if v.origin == "east"
    )
    assert discharged_n > 0
    assert discharged_e > 0


def test_max_pressure_dynamic_burst_adaptation() -> None:
    intersection, plan, demands = create_scenario_network(
        demand_n=0.0,
        demand_s=0.0,
        demand_e=0.0,
        demand_w=0.0,
        p1_min_green=5.0,
        p1_green_duration=20.0,
        p1_max_green=25.0,
        p2_min_green=5.0,
        p2_green_duration=20.0,
        p2_max_green=25.0,
    )

    controller = MaxPressureController(signal_plan=plan, intersection=intersection)
    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=1,
        controller=controller,
    )

    for i in range(4):
        engine.queues["lane_n_0"].enqueue(
            Vehicle(
                id=f"veh_n_{i}",
                origin="north",
                destination="south",
                target_lane_id="lane_n_0",
                arrival_time=0.0,
            ),
        )

    for i in range(12):
        engine.queues["lane_e_0"].enqueue(
            Vehicle(
                id=f"veh_e_{i}",
                origin="east",
                destination="west",
                target_lane_id="lane_e_0",
                arrival_time=0.0,
            ),
        )

    step_results = [engine.step() for _ in range(30)]

    reasons = [
        res.controller_decision.reason
        for res in step_results
        if res.controller_decision is not None
    ]

    assert "min_green_hold" in reasons
    assert "max_pressure_switch" in reasons

    switch_idx = reasons.index("max_pressure_switch")
    assert switch_idx >= 5
    assert reasons[switch_idx + 1] == "in_transition"
    dec = step_results[switch_idx].controller_decision
    assert dec is not None
    assert dec.target_phase_id == "P2"


def test_max_pressure_safety_clearance_preservation() -> None:
    intersection, plan, demands = create_scenario_network(
        demand_n=800.0,
        demand_s=800.0,
        demand_e=800.0,
        demand_w=800.0,
        p1_min_green=5.0,
        p1_green_duration=10.0,
        p1_max_green=10.0,
        p2_min_green=5.0,
        p2_green_duration=10.0,
        p2_max_green=10.0,
    )

    controller = MaxPressureController(signal_plan=plan, intersection=intersection)
    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=42,
        controller=controller,
    )

    results = engine.run(60.0)

    for i, res in enumerate(results[:-1]):
        next_res = results[i + 1]
        if (
            res.active_phase_id == "P1"
            and next_res.active_phase_id == "P2"
            and next_res.signal_state == SignalState.GREEN
        ):
            prior_states = [r.signal_state for r in results[max(0, i - 3) : i + 1]]
            assert SignalState.YELLOW in prior_states
            assert SignalState.ALL_RED in prior_states

    for res in results:
        if res.signal_state in (SignalState.YELLOW, SignalState.ALL_RED):
            assert len(res.discharged_vehicles) == 0
            assert res.controller_decision is not None
            assert res.controller_decision.reason in (
                "max_green",
                "max_pressure_switch",
                "in_transition",
            )


def test_max_pressure_repeatability_and_reset() -> None:
    intersection, plan, demands = create_scenario_network(
        demand_n=500.0,
        demand_s=500.0,
        demand_e=300.0,
        demand_w=300.0,
        p1_min_green=5.0,
        p1_green_duration=15.0,
        p1_max_green=25.0,
        p2_min_green=5.0,
        p2_green_duration=15.0,
        p2_max_green=25.0,
    )

    ctrl_a = MaxPressureController(signal_plan=plan, intersection=intersection)
    engine_a = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=12345,
        controller=ctrl_a,
    )

    ctrl_b = MaxPressureController(signal_plan=plan, intersection=intersection)
    engine_b = SimulationEngine(
        intersection=intersection,
        signal_plan=plan,
        demands=demands,
        step_size=1.0,
        seed=12345,
        controller=ctrl_b,
    )

    results_a = engine_a.run(100.0)
    results_b = engine_b.run(100.0)

    assert results_a == results_b

    ctrl_a.reset()
    assert ctrl_a.current_phase_index == 0
    assert ctrl_a.elapsed_green == 0.0
