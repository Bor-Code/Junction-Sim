from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from junction_sim.engine.step_result import StepResult
from junction_sim.engine.trajectories import VehicleState3D


class EmissionVehicleCategory(StrEnum):
    PASSENGER = "passenger"
    HEAVY = "heavy"


class InstantaneousEmissions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fuel_rate_ml_s: float = Field(ge=0.0)
    co2_rate_g_s: float = Field(ge=0.0)


class EmissionsResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fuel_liters: float = Field(ge=0.0)
    co2_kg: float = Field(ge=0.0)


HEAVY_VEHICLE_NAMES: frozenset[str] = frozenset(
    {"bus", "box_truck", "semi_truck", "heavy"}
)
CO2_GRAMS_PER_ML_FUEL: float = 2.392


def compute_instantaneous_emissions(
    speed: float, accel: float = 0.0, vehicle_type: str = "passenger"
) -> InstantaneousEmissions:
    is_heavy = vehicle_type.lower() in HEAVY_VEHICLE_NAMES
    idle_rate = 0.85 if is_heavy else 0.35
    v = max(0.0, float(speed))
    a = float(accel)

    power_term = (0.20 if is_heavy else 0.08) * a * v if a > 0.0 else 0.0

    cruise_term = (0.10 if is_heavy else 0.05) * v + (
        0.0018 if is_heavy else 0.0008
    ) * (v**3)
    fuel_rate = max(idle_rate, idle_rate + cruise_term + power_term)
    co2_rate = fuel_rate * CO2_GRAMS_PER_ML_FUEL

    return InstantaneousEmissions(
        fuel_rate_ml_s=round(fuel_rate, 4),
        co2_rate_g_s=round(co2_rate, 4),
    )


def compute_trajectory_emissions(
    states: Sequence[VehicleState3D], step_size: float = 0.1
) -> EmissionsResult:
    if not states:
        return EmissionsResult(fuel_liters=0.0, co2_kg=0.0)

    total_fuel_ml = 0.0
    for state in states:
        v_type = state.vehicle_type.value
        rates = compute_instantaneous_emissions(
            speed=state.speed,
            accel=state.acceleration,
            vehicle_type=v_type,
        )
        total_fuel_ml += rates.fuel_rate_ml_s * step_size

    fuel_liters = round(total_fuel_ml / 1000.0, 4)
    co2_kg = round((total_fuel_ml * CO2_GRAMS_PER_ML_FUEL) / 1000.0, 4)
    return EmissionsResult(fuel_liters=fuel_liters, co2_kg=co2_kg)


def compute_benchmark_emissions(
    results: Sequence[StepResult], step_size: float
) -> EmissionsResult:
    if not results:
        return EmissionsResult(fuel_liters=0.0, co2_kg=0.0)

    total_idle_seconds = 0.0
    for r in results:
        total_queue_vehicles = sum(r.queue_lengths.values())
        total_idle_seconds += total_queue_vehicles * step_size

    idle_fuel_ml = total_idle_seconds * 0.35

    discharged_count = sum(len(r.discharged_vehicles) for r in results)
    acceleration_fuel_ml = discharged_count * 15.0

    arrived_count = sum(len(r.arrived_vehicles) for r in results)
    cruise_fuel_ml = arrived_count * 5.8

    total_fuel_ml = idle_fuel_ml + acceleration_fuel_ml + cruise_fuel_ml
    fuel_liters = round(total_fuel_ml / 1000.0, 4)
    co2_kg = round((total_fuel_ml * CO2_GRAMS_PER_ML_FUEL) / 1000.0, 4)

    return EmissionsResult(fuel_liters=fuel_liters, co2_kg=co2_kg)
