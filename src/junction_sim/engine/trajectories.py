import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.movement import TurnType
from junction_sim.domain.signal import SignalPlan
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

        dep_info: dict[str, tuple[float, str, str]] = {}
        discharge_counts: dict[tuple[str, float], int] = {}
        for r in results:
            for v in r.discharged_vehicles:
                count = discharge_counts.get((v.origin, r.time), 0)
                discharge_counts[(v.origin, r.time)] = count + 1
                staggered_time = r.time + count * self.discharge_headway
                dep_info[v.id] = (
                    staggered_time,
                    v.origin,
                    v.destination,
                )

        od_to_turn: dict[tuple[str, str], TurnType] = {
            (mv.origin, mv.destination): mv.turn_type
            for mv in self.intersection.movements
        }

        step_times = [r.time for r in results]
        max_time = step_times[-1] + self.transit_duration + 15.0

        all_arrived_vehicles = [
            (idx, v) for r in results for idx, v in enumerate(r.arrived_vehicles)
        ]

        queue_slots: dict[str, float] = {}
        for idx, v in all_arrived_vehicles:
            ahead_vehicles = [
                (p_idx, p_v)
                for p_idx, p_v in all_arrived_vehicles
                if p_v.origin == v.origin
                and p_v.id != v.id
                and (
                    p_v.arrival_time < v.arrival_time
                    or (p_v.arrival_time == v.arrival_time and p_idx < idx)
                )
                and dep_info.get(p_v.id, (max_time + 100.0,))[0] > v.arrival_time
            ]
            ahead_vehicles.sort(key=lambda item: (item[1].arrival_time, item[0]))

            offset = 2.0
            for _, p_v in ahead_vehicles:
                p_type, _ = get_deterministic_vehicle_attributes(p_v.id)
                p_len = VEHICLE_LENGTHS.get(p_type, 4.4)
                offset += p_len + self.safety_gap

            v_type, _ = get_deterministic_vehicle_attributes(v.id)
            v_len = VEHICLE_LENGTHS.get(v_type, 4.4)
            queue_slots[v.id] = offset + v_len / 2.0

        for r in results:
            for v in r.arrived_vehicles:
                v_type, color = get_deterministic_vehicle_attributes(v.id)
                v_len = VEHICLE_LENGTHS.get(v_type, 4.4)
                states: list[VehicleState3D] = []

                app = app_map.get(v.origin)
                origin_dir = app.direction if app else Direction.NORTH
                f_in, _ = get_approach_vectors(origin_dir)

                stop_x, stop_y, heading_in = get_lane_stop_position(
                    origin_dir,
                    lane_index=0,
                    total_lanes=len(app.lanes) if app else 1,
                    lane_width=self.lane_width,
                )

                dest_app = app_map.get(v.destination)
                dest_dir = dest_app.direction if dest_app else Direction.SOUTH
                exit_x, exit_y, heading_out = get_outbound_exit_position(
                    dest_dir,
                    lane_width=self.lane_width,
                )

                turn_type = od_to_turn.get((v.origin, v.destination), TurnType.THROUGH)

                p_start = (stop_x, stop_y)
                p_end = (exit_x, exit_y)
                cp0, cp1, cp2, cp3 = build_turn_control_points(
                    origin_dir, dest_dir, turn_type, p_start, p_end
                )

                dep = dep_info.get(v.id)
                dep_time = dep[0] if dep is not None else max_time + 100.0

                turn_sig = "none"
                if turn_type == TurnType.LEFT:
                    turn_sig = "left"
                elif turn_type == TurnType.RIGHT:
                    turn_sig = "right"

                dist_back = queue_slots.get(v.id, 4.0)
                front_dist = 2.0 + v_len / 2.0
                is_front = dist_back <= (front_dist + 0.1)

                if is_front:
                    t_start_roll = dep_time
                    roll_advance = 0.0
                else:
                    roll_advance = dist_back - front_dist
                    duration_needed = max(1.2, roll_advance / 4.5)
                    available_wait = max(0.0, dep_time - v.arrival_time)
                    roll_dur = min(duration_needed, max(0.8, available_wait * 0.75))
                    t_start_roll = max(v.arrival_time + 0.001, dep_time - roll_dur)

                v_turn = 7.5 if turn_type != TurnType.THROUGH else 9.0

                t = v.arrival_time
                while t <= min(max_time, dep_time + self.transit_duration + 8.0):
                    if t < t_start_roll:
                        vx = stop_x - f_in[0] * dist_back
                        vy = stop_y - f_in[1] * dist_back
                        states.append(
                            VehicleState3D(
                                time=round(t, 3),
                                vehicle_id=v.id,
                                x=round(vx, 3),
                                y=round(vy, 3),
                                z=0.0,
                                heading=round(heading_in, 4),
                                speed=0.0,
                                acceleration=0.0,
                                steering_angle=0.0,
                                brake_light=True,
                                turn_signal=turn_sig,
                                vehicle_type=v_type,
                                color=color,
                            )
                        )
                    elif t < dep_time:
                        denom = max(0.01, dep_time - t_start_roll)
                        u_roll = max(0.0, min(1.0, (t - t_start_roll) / denom))
                        smooth_u = 0.5 * (1.0 - math.cos(u_roll * math.pi))
                        cur_dist = dist_back - roll_advance * smooth_u
                        vx = stop_x - f_in[0] * cur_dist
                        vy = stop_y - f_in[1] * cur_dist
                        spd = v_turn * math.sin(u_roll * math.pi / 2.0)
                        states.append(
                            VehicleState3D(
                                time=round(t, 3),
                                vehicle_id=v.id,
                                x=round(vx, 3),
                                y=round(vy, 3),
                                z=0.0,
                                heading=round(heading_in, 4),
                                speed=round(spd, 2),
                                acceleration=1.4,
                                steering_angle=0.0,
                                brake_light=False,
                                turn_signal=turn_sig,
                                vehicle_type=v_type,
                                color=color,
                            )
                        )
                    elif t <= dep_time + self.transit_duration:
                        progress = (t - dep_time) / self.transit_duration
                        px, py, h = compute_bezier_point(cp0, cp1, cp2, cp3, progress)
                        steer = 0.0
                        if turn_type == TurnType.LEFT:
                            steer = 0.35 * math.sin(progress * math.pi)
                        elif turn_type == TurnType.RIGHT:
                            steer = -0.45 * math.sin(progress * math.pi)

                        spd = v_turn + 1.5 * math.sin(progress * math.pi / 2.0)
                        states.append(
                            VehicleState3D(
                                time=round(t, 3),
                                vehicle_id=v.id,
                                x=round(px, 3),
                                y=round(py, 3),
                                z=0.0,
                                heading=round(h, 4),
                                speed=round(spd, 2),
                                acceleration=0.8,
                                steering_angle=round(steer, 4),
                                brake_light=False,
                                turn_signal=turn_sig,
                                vehicle_type=v_type,
                                color=color,
                            )
                        )
                    else:
                        out_f, _ = get_approach_vectors(dest_dir)
                        opp_out_f = (-out_f[0], -out_f[1])
                        dt_out = t - (dep_time + self.transit_duration)
                        ramp_u = min(1.0, dt_out / 2.5)
                        v_cur = (v_turn + 1.5) + (12.5 - (v_turn + 1.5)) * ramp_u
                        dist_traveled = (v_turn + 1.5) * dt_out + 0.5 * (
                            12.5 - (v_turn + 1.5)
                        ) * ramp_u * dt_out
                        vx = exit_x + opp_out_f[0] * dist_traveled
                        vy = exit_y + opp_out_f[1] * dist_traveled
                        states.append(
                            VehicleState3D(
                                time=round(t, 3),
                                vehicle_id=v.id,
                                x=round(vx, 3),
                                y=round(vy, 3),
                                z=0.0,
                                heading=round(heading_out, 4),
                                speed=round(v_cur, 2),
                                acceleration=0.5 if ramp_u < 1.0 else 0.0,
                                steering_angle=0.0,
                                brake_light=False,
                                turn_signal="none",
                                vehicle_type=v_type,
                                color=color,
                            )
                        )
                    t += substep_dt

                registry[v.id] = states

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
