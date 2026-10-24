import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.movement import TurnType
from junction_sim.domain.signal import SignalPlan
from junction_sim.engine.idm import (
    DriverProfile,
    compute_idm_acceleration,
    get_driver_profile,
)
from junction_sim.engine.step_result import StepResult


class VehicleType(StrEnum):
    SEDAN = "sedan"
    SUV = "suv"
    HATCHBACK = "hatchback"
    VAN = "van"
    BUS = "bus"
    BOX_TRUCK = "box_truck"
    SEMI_TRUCK = "semi_truck"


VEHICLE_LENGTHS: dict[VehicleType, float] = {
    VehicleType.HATCHBACK: 3.9,
    VehicleType.SEDAN: 4.4,
    VehicleType.SUV: 4.8,
    VehicleType.VAN: 5.6,
    VehicleType.BOX_TRUCK: 7.8,
    VehicleType.BUS: 11.2,
    VehicleType.SEMI_TRUCK: 14.8,
}


class VehicleState3D(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    time: float
    vehicle_id: str
    x: float
    y: float
    z: float = 0.0
    heading: float
    speed: float = 0.0
    acceleration: float = 0.0
    steering_angle: float = 0.0
    brake_light: bool = False
    turn_signal: str = "none"
    vehicle_type: VehicleType = VehicleType.SEDAN
    color: str = "#2563eb"
    driver_profile: DriverProfile = DriverProfile.NORMAL


VEHICLE_COLORS: tuple[str, ...] = (
    "#2563eb",
    "#dc2626",
    "#f8fafc",
    "#0f172a",
    "#64748b",
    "#d97706",
    "#059669",
    "#7c3aed",
    "#eab308",
    "#0284c7",
)

VEHICLE_TYPES: tuple[VehicleType, ...] = (
    VehicleType.SEDAN,
    VehicleType.SUV,
    VehicleType.HATCHBACK,
    VehicleType.VAN,
    VehicleType.BUS,
    VehicleType.BOX_TRUCK,
    VehicleType.SEMI_TRUCK,
)


def get_deterministic_vehicle_attributes(vehicle_id: str) -> tuple[VehicleType, str]:
    val = sum(ord(c) for c in vehicle_id)
    v_type = VEHICLE_TYPES[val % len(VEHICLE_TYPES)]
    color = VEHICLE_COLORS[(val // 3) % len(VEHICLE_COLORS)]
    return v_type, color


def compute_bezier_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    u: float,
) -> tuple[float, float, float]:
    u_clamped = max(0.0, min(1.0, u))
    one_minus_u = 1.0 - u_clamped

    b0 = one_minus_u**3
    b1 = 3.0 * (one_minus_u**2) * u_clamped
    b2 = 3.0 * one_minus_u * (u_clamped**2)
    b3 = u_clamped**3

    x = b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0]
    y = b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1]

    d0 = 3.0 * (one_minus_u**2)
    d1 = 6.0 * one_minus_u * u_clamped
    d2 = 3.0 * (u_clamped**2)

    vx = d0 * (p1[0] - p0[0]) + d1 * (p2[0] - p1[0]) + d2 * (p3[0] - p2[0])
    vy = d0 * (p1[1] - p0[1]) + d1 * (p2[1] - p1[1]) + d2 * (p3[1] - p2[1])

    if abs(vy) < 1e-9:
        vy = 0.0
    if abs(vx) < 1e-9:
        vx = 0.0
    heading = math.atan2(vy, vx)
    return x, y, heading


def get_approach_vectors(
    direction: Direction,
) -> tuple[tuple[float, float], tuple[float, float]]:
    if direction == Direction.NORTH:
        return (0.0, -1.0), (1.0, 0.0)
    if direction == Direction.SOUTH:
        return (0.0, 1.0), (-1.0, 0.0)
    if direction == Direction.EAST:
        return (-1.0, 0.0), (0.0, -1.0)
    return (1.0, 0.0), (0.0, 1.0)


def get_lane_stop_position(
    direction: Direction,
    lane_index: int,
    total_lanes: int,
    lane_width: float = 3.5,
    stop_distance: float = 18.0,
) -> tuple[float, float, float]:
    forward, right = get_approach_vectors(direction)
    offset = (lane_index + 0.5) * lane_width

    x = -forward[0] * stop_distance + right[0] * offset
    y = -forward[1] * stop_distance + right[1] * offset
    heading = math.atan2(forward[1], forward[0])
    return x, y, heading


def get_outbound_exit_position(
    destination_direction: Direction,
    lane_width: float = 3.5,
    exit_distance: float = 18.0,
) -> tuple[float, float, float]:
    out_forward, out_right = get_approach_vectors(destination_direction)
    opp_forward = (-out_forward[0], -out_forward[1])
    offset = 0.5 * lane_width

    x = opp_forward[0] * exit_distance - out_right[0] * offset
    y = opp_forward[1] * exit_distance - out_right[1] * offset
    heading = math.atan2(opp_forward[1], opp_forward[0])
    return x, y, heading


def build_turn_control_points(
    origin_dir: Direction,
    dest_dir: Direction,
    turn_type: TurnType,
    p_start: tuple[float, float],
    p_end: tuple[float, float],
) -> tuple[
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
]:
    f_in, _ = get_approach_vectors(origin_dir)
    f_out, _ = get_approach_vectors(dest_dir)
    opp_f_out = (-f_out[0], -f_out[1])

    if turn_type == TurnType.THROUGH:
        p1 = (p_start[0] + f_in[0] * 6.0, p_start[1] + f_in[1] * 6.0)
        p2 = (p_end[0] - opp_f_out[0] * 6.0, p_end[1] - opp_f_out[1] * 6.0)
        return p_start, p1, p2, p_end

    if turn_type == TurnType.LEFT:
        arm = 12.0
        p1 = (p_start[0] + f_in[0] * arm, p_start[1] + f_in[1] * arm)
        p2 = (p_end[0] - opp_f_out[0] * arm, p_end[1] - opp_f_out[1] * arm)
        return p_start, p1, p2, p_end

    arm = 6.0
    p1 = (p_start[0] + f_in[0] * arm, p_start[1] + f_in[1] * arm)
    p2 = (p_end[0] - opp_f_out[0] * arm, p_end[1] - opp_f_out[1] * arm)
    return p_start, p1, p2, p_end


class TrajectoryEngine:
    def __init__(
        self,
        intersection: Intersection,
        signal_plan: SignalPlan,
        slot_length: float = 6.5,
        lane_width: float = 3.5,
        transit_duration: float = 3.5,
        discharge_headway: float = 1.8,
        safety_gap: float = 2.5,
    ) -> None:
        self.intersection = intersection
        self.signal_plan = signal_plan
        self.slot_length = slot_length
        self.lane_width = lane_width
        self.transit_duration = transit_duration
        self.discharge_headway = discharge_headway
        self.safety_gap = safety_gap

    def generate_vehicle_states(
        self,
        results: Sequence[StepResult],
        substep_dt: float = 0.2,
    ) -> dict[str, list[VehicleState3D]]:
        registry: dict[str, list[VehicleState3D]] = {}
        if not results:
            return registry

        app_map = {app.id: app for app in self.intersection.approaches}

        dep_times: dict[str, float] = {}
        last_dep_per_app: dict[str, float] = {}
        for r in results:
            for v in r.discharged_vehicles:
                last_t = last_dep_per_app.get(v.origin, -1.0)
                t_dep = max(r.time, last_t + self.discharge_headway)
                last_dep_per_app[v.origin] = t_dep
                dep_times[v.id] = t_dep

        od_to_turn: dict[tuple[str, str], TurnType] = {
            (mv.origin, mv.destination): mv.turn_type
            for mv in self.intersection.movements
        }

        step_times = [r.time for r in results]
        max_time = step_times[-1] + self.transit_duration + 20.0
        num_substeps = int(max_time / substep_dt) + 1
        times = [round(i * substep_dt, 3) for i in range(num_substeps)]

        app_vehicles: dict[str, list[Any]] = {}
        for r in results:
            for v in r.arrived_vehicles:
                app_vehicles.setdefault(v.origin, []).append(v)

        for app_id, v_list in app_vehicles.items():
            app = app_map.get(app_id)
            origin_dir = app.direction if app else Direction.NORTH
            f_in, _ = get_approach_vectors(origin_dir)
            total_lanes = len(app.lanes) if app else 1

            stop_x, stop_y, heading_in = get_lane_stop_position(
                origin_dir, 0, total_lanes, lane_width=self.lane_width
            )

            s_hist: dict[str, dict[float, float]] = {}
            spd_hist: dict[str, dict[float, float]] = {}

            for v_idx, v in enumerate(v_list):
                s_hist[v.id] = {}
                spd_hist[v.id] = {}
                v_type, color = get_deterministic_vehicle_attributes(v.id)
                prof, idm_p = get_driver_profile(v.id)
                v_len = VEHICLE_LENGTHS.get(v_type, 4.4)
                v_dep = dep_times.get(v.id, max_time + 100.0)

                dest_app = app_map.get(v.destination)
                dest_dir = dest_app.direction if dest_app else Direction.SOUTH
                turn_type = od_to_turn.get((v.origin, v.destination), TurnType.THROUGH)
                exit_x, exit_y, heading_out = get_outbound_exit_position(
                    dest_dir, lane_width=self.lane_width
                )

                p_start = (stop_x, stop_y)
                p_end = (exit_x, exit_y)
                cp0, cp1, cp2, cp3 = build_turn_control_points(
                    origin_dir, dest_dir, turn_type, p_start, p_end
                )
                if turn_type == TurnType.THROUGH:
                    l_transit = 36.0
                elif turn_type == TurnType.LEFT:
                    l_transit = 28.0
                else:
                    l_transit = 16.0

                prev_v = v_list[v_idx - 1] if v_idx > 0 else None
                t_arr = v.arrival_time
                s_stop = -v_len / 2.0 - 0.5

                prev_s = None
                if prev_v is not None and prev_v.id in s_hist and s_hist[prev_v.id]:
                    hist = s_hist[prev_v.id]
                    prev_s = hist.get(t_arr)
                    if prev_s is None:
                        past_keys = [k for k in hist if k <= t_arr + 1e-4]
                        prev_s = hist[max(past_keys)] if past_keys else hist[min(hist)]

                if prev_v is not None and prev_s is not None:
                    prev_type, _ = get_deterministic_vehicle_attributes(prev_v.id)
                    prev_len = VEHICLE_LENGTHS.get(prev_type, 4.4)
                    s_cap_arr = prev_s - (prev_len + v_len) / 2.0 - self.safety_gap
                else:
                    s_cap_arr = s_stop

                cur_s = min(s_stop, s_cap_arr)
                cur_spd = 0.0

                turn_sig = "none"
                if turn_type == TurnType.LEFT:
                    turn_sig = "left"
                elif turn_type == TurnType.RIGHT:
                    turn_sig = "right"

                v_states: list[VehicleState3D] = []
                for t in times:
                    if t < t_arr:
                        continue

                    s_stop_lim = s_stop if t < v_dep else 999.0
                    lead_spd = None
                    if (
                        prev_v is not None
                        and prev_v.id in s_hist
                        and t in s_hist[prev_v.id]
                    ):
                        prev_s = s_hist[prev_v.id][t]
                        prev_type, _ = get_deterministic_vehicle_attributes(prev_v.id)
                        prev_len = VEHICLE_LENGTHS.get(prev_type, 4.4)
                        s_fol_lim = prev_s - (prev_len + v_len) / 2.0 - self.safety_gap
                        lead_spd = spd_hist[prev_v.id].get(t, 0.0)
                    else:
                        s_fol_lim = 999.0

                    s_cap = min(s_stop_lim, s_fol_lim)
                    avail = max(0.0, s_cap - cur_s)

                    v_max = 8.0 if cur_s < l_transit else idm_p.v0
                    lead_s = s_cap if s_cap < 900.0 else None
                    lead_v = lead_spd if s_fol_lim <= s_stop_lim else 0.0
                    gap = avail if lead_s is not None else 999.0

                    eff_p = (
                        idm_p
                        if v_max >= idm_p.v0
                        else idm_p.model_copy(update={"v0": v_max})
                    )
                    acc = compute_idm_acceleration(
                        current_speed=cur_spd,
                        lead_speed=lead_v if lead_s is not None else None,
                        gap=gap,
                        params=eff_p,
                    )
                    cur_spd = max(0.0, cur_spd + acc * substep_dt)
                    cur_s = min(s_cap, cur_s + cur_spd * substep_dt)
                    s_hist[v.id][t] = cur_s
                    spd_hist[v.id][t] = cur_spd

                    brk = (cur_spd < 0.1 and cur_s <= 0.0) or (acc < -0.8)

                    steer = 0.0
                    if cur_s <= 0.0:
                        dist_back = -cur_s
                        px = stop_x - f_in[0] * dist_back
                        py = stop_y - f_in[1] * dist_back
                        ph = heading_in
                        sig = turn_sig if dist_back < 25.0 else "none"
                    elif cur_s <= l_transit:
                        u = cur_s / l_transit
                        px, py, ph = compute_bezier_point(cp0, cp1, cp2, cp3, u)
                        sig = turn_sig
                        if turn_type == TurnType.LEFT:
                            steer = 0.35 * math.sin(u * math.pi)
                        elif turn_type == TurnType.RIGHT:
                            steer = -0.45 * math.sin(u * math.pi)
                    else:
                        out_f, _ = get_approach_vectors(dest_dir)
                        opp_out_f = (-out_f[0], -out_f[1])
                        d_out = cur_s - l_transit
                        px = exit_x + opp_out_f[0] * d_out
                        py = exit_y + opp_out_f[1] * d_out
                        ph = heading_out
                        sig = "none"

                    v_states.append(
                        VehicleState3D(
                            time=round(t, 3),
                            vehicle_id=v.id,
                            x=round(px, 3),
                            y=round(py, 3),
                            z=0.0,
                            heading=round(ph, 4),
                            speed=round(cur_spd, 2),
                            acceleration=round(acc, 2),
                            steering_angle=round(steer, 4),
                            brake_light=brk,
                            turn_signal=sig,
                            vehicle_type=v_type,
                            color=color,
                            driver_profile=prof,
                        )
                    )

                    if cur_s > l_transit + 90.0:
                        break

                registry[v.id] = v_states

        return registry


def sample_scene_vehicles(
    registry: Mapping[str, Sequence[VehicleState3D]],
    query_time: float,
    tolerance: float = 0.3,
) -> list[VehicleState3D]:
    active: list[VehicleState3D] = []
    for _vid, states in registry.items():
        if not states:
            continue
        best_state = min(states, key=lambda s: abs(s.time - query_time))
        if abs(best_state.time - query_time) <= tolerance:
            active.append(best_state)
    return active


def export_trajectories_to_dict(
    registry: Mapping[str, Sequence[VehicleState3D]],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for vid, states in registry.items():
        out[vid] = [s.model_dump() for s in states]
    return out
