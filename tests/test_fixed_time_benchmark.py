import pytest

from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import InvalidStateError


def create_benchmark_setup(
    demand_n: float,
    demand_s: float,
    demand_e: float,
    demand_w: float,
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
        max_capacity=100,
    )
    lane_s = Lane(
        id="lane_s_0",
        approach_id="south",
        allowed_movement_ids=("S_T",),
        max_capacity=100,
    )
    lane_e = Lane(
        id="lane_e_0",
        approach_id="east",
        allowed_movement_ids=("E_T",),
        max_capacity=100,
    )
    lane_w = Lane(
        id="lane_w_0",
        approach_id="west",
        allowed_movement_ids=("W_T",),
        max_capacity=100,
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
        id="bench_int",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )

    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
    )
    signal_plan = SignalPlan(id="bench_plan", phases=(phase_1, phase_2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=demand_n),
        DemandProfile(movement_id="S_T", flow_rate_vph=demand_s),
        DemandProfile(movement_id="E_T", flow_rate_vph=demand_e),
        DemandProfile(movement_id="W_T", flow_rate_vph=demand_w),
    )

    return intersection, signal_plan, demands


def test_fixed_time_undersaturated_regime() -> None:
    inter, plan, demands = create_benchmark_setup(300.0, 300.0, 300.0, 300.0)
    controller = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=controller,
        seed=12345,
        step_size=1.0,
    )

    results = engine.run(240.0)
    assert len(results) == 240

    total_arrivals = sum(len(r.arrived_vehicles) for r in results)
    total_discharges = sum(len(r.discharged_vehicles) for r in results)

    assert total_arrivals > 50
    assert total_discharges > 0
    assert total_discharges >= total_arrivals - 15

    for k in range(5):
        p1_start = k * 48
        assert (
            min(
                results[t].queue_lengths["lane_n_0"]
                for t in range(p1_start, p1_start + 20)
            )
            == 0
        )
        assert (
            min(
                results[t].queue_lengths["lane_s_0"]
                for t in range(p1_start, p1_start + 20)
            )
            == 0
        )

        p2_start = k * 48 + 24
        assert (
            min(
                results[t].queue_lengths["lane_e_0"]
                for t in range(p2_start, p2_start + 20)
            )
            == 0
        )
        assert (
            min(
                results[t].queue_lengths["lane_w_0"]
                for t in range(p2_start, p2_start + 20)
            )
            == 0
        )

    waiting_times = [
        v.waiting_time(r.time) for r in results for v in r.discharged_vehicles
    ]
    avg_delay = sum(waiting_times) / len(waiting_times)
    assert avg_delay < 25.0


def test_fixed_time_near_saturated_regime() -> None:
    inter, plan, demands = create_benchmark_setup(650.0, 650.0, 650.0, 650.0)
    controller = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=controller,
        seed=42,
        step_size=1.0,
    )

    results = engine.run(240.0)
    total_arrivals = sum(len(r.arrived_vehicles) for r in results)
    total_discharges = sum(len(r.discharged_vehicles) for r in results)

    assert total_arrivals > 120
    assert total_discharges >= int(total_arrivals * 0.75)

    max_queue = max(max(r.queue_lengths.values()) for r in results)
    assert max_queue < 20


def test_fixed_time_oversaturated_regime() -> None:
    inter, plan, demands = create_benchmark_setup(1200.0, 1200.0, 1200.0, 1200.0)
    controller = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=controller,
        seed=999,
        step_size=1.0,
    )

    results = engine.run(240.0)
    total_arrivals = sum(len(r.arrived_vehicles) for r in results)
    total_discharges = sum(len(r.discharged_vehicles) for r in results)

    assert total_arrivals > 250
    assert total_discharges < total_arrivals

    queue_cycle_1 = sum(results[47].queue_lengths.values())
    queue_cycle_5 = sum(results[239].queue_lengths.values())
    assert queue_cycle_5 > queue_cycle_1 + 20


def test_fixed_time_asymmetric_demand_wasted_green() -> None:
    inter, plan, demands = create_benchmark_setup(900.0, 900.0, 100.0, 100.0)
    controller = FixedTimeController(signal_plan=plan)
    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=controller,
        seed=777,
        step_size=1.0,
    )

    results = engine.run(192.0)

    wasted_green_steps = 0
    for r in results:
        if (
            r.active_phase_id == "P2"
            and r.signal_state == SignalState.GREEN
            and r.queue_lengths["lane_e_0"] == 0
            and r.queue_lengths["lane_w_0"] == 0
            and len(r.discharged_vehicles) == 0
        ):
            wasted_green_steps += 1

    assert wasted_green_steps > 30

    residual_north_queue = results[-1].queue_lengths["lane_n_0"]
    residual_east_queue = results[-1].queue_lengths["lane_e_0"]
    assert residual_north_queue > residual_east_queue


def test_fixed_time_benchmark_repeatability() -> None:
    inter, plan, demands = create_benchmark_setup(500.0, 500.0, 500.0, 500.0)

    engine_a = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=FixedTimeController(signal_plan=plan),
        seed=888,
        step_size=1.0,
    )
    engine_b = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=FixedTimeController(signal_plan=plan),
        seed=888,
        step_size=1.0,
    )

    results_a = engine_a.run(120.0)
    results_b = engine_b.run(120.0)

    assert results_a == results_b


def test_fixed_time_spillback_under_restricted_storage_capacity() -> None:
    lane_n = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_T",),
        max_capacity=5,
    )
    lane_s = Lane(
        id="lane_s_0",
        approach_id="south",
        allowed_movement_ids=("S_T",),
        max_capacity=5,
    )
    lane_e = Lane(
        id="lane_e_0",
        approach_id="east",
        allowed_movement_ids=("E_T",),
        max_capacity=5,
    )
    lane_w = Lane(
        id="lane_w_0",
        approach_id="west",
        allowed_movement_ids=("W_T",),
        max_capacity=5,
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

    intersection = Intersection(
        id="spill_int",
        approaches=(app_n, app_s, app_e, app_w),
        movements=(mov_n_t, mov_s_t, mov_e_t, mov_w_t),
        conflicting_movement_pairs=conflicts,
    )

    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=1.0,
    )
    signal_plan = SignalPlan(id="spill_plan", phases=(phase_1, phase_2))

    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="E_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="W_T", flow_rate_vph=1800.0),
    )

    controller = FixedTimeController(signal_plan=signal_plan)
    engine = SimulationEngine(
        intersection=intersection,
        signal_plan=signal_plan,
        demands=demands,
        controller=controller,
        seed=111,
        step_size=1.0,
    )

    with pytest.raises(InvalidStateError):
        engine.run(100.0)
