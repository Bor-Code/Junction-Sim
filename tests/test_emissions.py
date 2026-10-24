import csv
import io

from junction_sim.benchmarks.metrics import BenchmarkMetrics, BenchmarkResult
from junction_sim.benchmarks.multi_seed import (
    MultiSeedBenchmarkResult,
    aggregate_seed_metrics,
)
from junction_sim.domain.crosswalk import PedestrianSignalState
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.emissions import (
    EmissionsResult,
    EmissionVehicleCategory,
    InstantaneousEmissions,
    compute_benchmark_emissions,
    compute_instantaneous_emissions,
    compute_trajectory_emissions,
)
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.trajectories import VehicleState3D, VehicleType
from junction_sim.engine.transition import SignalState
from junction_sim.reporting.csv_reporter import (
    export_benchmark_to_csv,
    export_multi_seed_benchmark_to_csv,
)


def test_emission_vehicle_category_values() -> None:
    assert EmissionVehicleCategory.PASSENGER.value == "passenger"
    assert EmissionVehicleCategory.HEAVY.value == "heavy"


def test_compute_instantaneous_emissions_idle() -> None:
    em = compute_instantaneous_emissions(speed=0.0, accel=0.0, vehicle_type="passenger")
    assert isinstance(em, InstantaneousEmissions)
    assert em.fuel_rate_ml_s == 0.35
    assert em.co2_rate_g_s == round(0.35 * 2.392, 4)


def test_compute_instantaneous_emissions_negative_speed_and_accel() -> None:
    em = compute_instantaneous_emissions(speed=-10.0, accel=-2.0, vehicle_type="sedan")
    assert em.fuel_rate_ml_s == 0.35


def test_compute_instantaneous_emissions_cruising_and_accelerating() -> None:
    em = compute_instantaneous_emissions(
        speed=15.0, accel=1.5, vehicle_type="passenger"
    )
    assert em.fuel_rate_ml_s > 0.35
    assert em.co2_rate_g_s > 0.0


def test_compute_instantaneous_emissions_heavy_vehicle() -> None:
    em_bus = compute_instantaneous_emissions(speed=12.0, accel=1.0, vehicle_type="bus")
    em_car = compute_instantaneous_emissions(speed=12.0, accel=1.0, vehicle_type="car")
    assert em_bus.fuel_rate_ml_s > em_car.fuel_rate_ml_s
    assert em_bus.co2_rate_g_s > em_car.co2_rate_g_s


def test_compute_instantaneous_emissions_heavy_decelerating() -> None:
    em = compute_instantaneous_emissions(
        speed=10.0, accel=-1.0, vehicle_type="semi_truck"
    )
    assert em.fuel_rate_ml_s >= 0.85


def test_compute_trajectory_emissions_empty() -> None:
    res = compute_trajectory_emissions([])
    assert isinstance(res, EmissionsResult)
    assert res.fuel_liters == 0.0
    assert res.co2_kg == 0.0


def test_compute_trajectory_emissions_with_states() -> None:
    s1 = VehicleState3D(
        time=0.0,
        vehicle_id="veh_0",
        x=0.0,
        y=0.0,
        heading=0.0,
        speed=10.0,
        acceleration=1.0,
        vehicle_type=VehicleType.SEDAN,
    )
    s2 = VehicleState3D(
        time=0.1,
        vehicle_id="veh_1",
        x=1.0,
        y=0.0,
        heading=0.0,
        speed=8.0,
        acceleration=0.5,
        vehicle_type=VehicleType.BUS,
    )
    res = compute_trajectory_emissions([s1, s2], step_size=0.1)
    assert res.fuel_liters > 0.0
    assert res.co2_kg > 0.0


def test_compute_benchmark_emissions_empty() -> None:
    res = compute_benchmark_emissions([], step_size=1.0)
    assert res.fuel_liters == 0.0
    assert res.co2_kg == 0.0


def test_compute_benchmark_emissions_with_results() -> None:
    v_arr = Vehicle(id="v_1", origin="north", destination="south", arrival_time=0.0)
    v_dep = Vehicle(
        id="v_0",
        origin="north",
        destination="south",
        arrival_time=0.0,
        departure_time=5.0,
    )
    sr = StepResult(
        time=1.0,
        step_index=1,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(v_arr,),
        discharged_vehicles=(v_dep,),
        queue_lengths={"lane_1": 3, "lane_2": 2},
        pedestrian_signals={"cw_1": PedestrianSignalState.WALK},
    )
    res = compute_benchmark_emissions([sr], step_size=1.0)
    assert res.fuel_liters > 0.0
    assert res.co2_kg > 0.0


def test_benchmark_metrics_and_csv_reporting() -> None:
    m = BenchmarkMetrics(
        controller_name="test_ctrl",
        total_arrivals=20,
        total_discharges=18,
        completion_rate=90.0,
        average_delay=5.5,
        max_delay=12.0,
        average_queue=2.1,
        max_queue=6,
        phase_switch_count=2,
        wasted_green_time=1.5,
        fuel_consumed_liters=0.1234,
        co2_emitted_kg=0.2952,
    )
    b_res = BenchmarkResult(
        metrics={"test_ctrl": m},
        duration=50.0,
        step_size=1.0,
        seed=42,
    )
    csv_str = export_benchmark_to_csv(b_res)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["fuel_consumed_liters"] == "0.1234"
    assert rows[0]["co2_emitted_kg"] == "0.2952"


def test_multi_seed_metrics_and_csv_reporting() -> None:
    m1 = BenchmarkMetrics(
        controller_name="ctrl",
        total_arrivals=20,
        total_discharges=18,
        completion_rate=90.0,
        average_delay=5.0,
        max_delay=10.0,
        average_queue=2.0,
        max_queue=5,
        phase_switch_count=2,
        wasted_green_time=1.0,
        fuel_consumed_liters=0.1000,
        co2_emitted_kg=0.2392,
    )
    m2 = BenchmarkMetrics(
        controller_name="ctrl",
        total_arrivals=20,
        total_discharges=20,
        completion_rate=100.0,
        average_delay=6.0,
        max_delay=12.0,
        average_queue=2.5,
        max_queue=6,
        phase_switch_count=2,
        wasted_green_time=2.0,
        fuel_consumed_liters=0.1200,
        co2_emitted_kg=0.2870,
    )
    agg = aggregate_seed_metrics("ctrl", [m1, m2])
    assert agg.mean_fuel_consumed == 0.1100
    assert agg.mean_co2_emitted == 0.2631

    ms_res = MultiSeedBenchmarkResult(
        controller_metrics={"ctrl": agg},
        seeds=(1, 2),
        duration=50.0,
        step_size=1.0,
    )
    csv_str = export_multi_seed_benchmark_to_csv(ms_res)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["mean_fuel_consumed_liters"] == "0.1100"
    assert rows[0]["mean_co2_emitted_kg"] == "0.2631"
