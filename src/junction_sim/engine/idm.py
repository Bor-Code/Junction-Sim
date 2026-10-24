import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DriverProfile(StrEnum):
    CAUTIOUS = "cautious"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


class IDMParameters(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    v0: float = Field(default=13.8, gt=0.0)
    time_headway: float = Field(default=1.4, gt=0.0)
    min_gap: float = Field(default=2.0, ge=0.0)
    max_accel: float = Field(default=1.8, gt=0.0)
    desired_decel: float = Field(default=2.0, gt=0.0)
    accel_exponent: float = Field(default=4.0, gt=0.0)
    max_decel: float = Field(default=8.0, gt=0.0)


DRIVER_PROFILES: dict[DriverProfile, IDMParameters] = {
    DriverProfile.CAUTIOUS: IDMParameters(
        v0=11.1,
        time_headway=1.8,
        min_gap=2.5,
        max_accel=1.2,
        desired_decel=1.5,
        accel_exponent=4.0,
        max_decel=6.0,
    ),
    DriverProfile.NORMAL: IDMParameters(
        v0=13.8,
        time_headway=1.4,
        min_gap=2.0,
        max_accel=1.8,
        desired_decel=2.0,
        accel_exponent=4.0,
        max_decel=8.0,
    ),
    DriverProfile.AGGRESSIVE: IDMParameters(
        v0=16.6,
        time_headway=0.9,
        min_gap=1.2,
        max_accel=2.8,
        desired_decel=3.0,
        accel_exponent=4.0,
        max_decel=10.0,
    ),
}


def get_driver_profile(vehicle_id: str) -> tuple[DriverProfile, IDMParameters]:
    val = sum(ord(c) for c in vehicle_id) % 10
    if val < 2:
        prof = DriverProfile.CAUTIOUS
    elif val < 8:
        prof = DriverProfile.NORMAL
    else:
        prof = DriverProfile.AGGRESSIVE
    return prof, DRIVER_PROFILES[prof]


def compute_idm_acceleration(
    current_speed: float,
    lead_speed: float | None,
    gap: float,
    params: IDMParameters,
) -> float:
    v = max(0.0, current_speed)
    ratio = (v / params.v0) ** params.accel_exponent
    free_road_accel = params.max_accel * (1.0 - ratio)

    if lead_speed is None:
        return float(max(-params.max_decel, min(params.max_accel, free_road_accel)))

    delta_v = v - max(0.0, lead_speed)
    interaction = v * params.time_headway + (v * delta_v) / (
        2.0 * math.sqrt(params.max_accel * params.desired_decel)
    )
    s_star = params.min_gap + max(0.0, interaction)

    if gap <= 0.0:
        return float(-params.max_decel)

    clamped_gap = max(0.2, gap)
    decel_ratio = (s_star / clamped_gap) ** 2
    accel = params.max_accel * (1.0 - ratio - decel_ratio)
    return float(max(-params.max_decel, min(params.max_accel, accel)))


def step_idm(
    current_s: float,
    current_speed: float,
    lead_s: float | None,
    lead_speed: float | None,
    dt: float,
    params: IDMParameters,
) -> tuple[float, float, float]:
    gap = (lead_s - current_s) if lead_s is not None else 999.0
    accel = compute_idm_acceleration(
        current_speed=current_speed,
        lead_speed=lead_speed,
        gap=gap,
        params=params,
    )
    new_speed = max(0.0, current_speed + accel * dt)
    new_s = current_s + new_speed * dt
    return new_s, new_speed, accel
