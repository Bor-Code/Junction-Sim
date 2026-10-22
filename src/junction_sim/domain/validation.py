from itertools import combinations

from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.exceptions import InvalidGeometryError, InvalidSignalPlanError


def validate_signal_plan_against_intersection(
    plan: SignalPlan,
    intersection: Intersection,
) -> None:
    intersection_movement_ids = {m.id for m in intersection.movements}
    intersection_crosswalk_ids = {cw.id for cw in intersection.crosswalks}
    all_green_movement_ids: set[str] = set()

    for phase in plan.phases:
        for m_id in phase.green_movement_ids:
            if m_id not in intersection_movement_ids:
                raise InvalidSignalPlanError(
                    f"phase '{phase.id}' references unknown movement '{m_id}'"
                )
            all_green_movement_ids.add(m_id)

        for cw_id in phase.pedestrian_crosswalk_ids:
            if cw_id not in intersection_crosswalk_ids:
                raise InvalidSignalPlanError(
                    f"phase '{phase.id}' references unknown crosswalk '{cw_id}'"
                )

        for m1, m2 in combinations(phase.green_movement_ids, 2):
            if intersection.are_conflicting(m1, m2):
                raise InvalidSignalPlanError(
                    f"phase '{phase.id}' green movements '{m1}' and '{m2}' "
                    "are conflicting"
                )

    unserved_movements = intersection_movement_ids - all_green_movement_ids
    if unserved_movements:
        unserved_str = ", ".join(sorted(unserved_movements))
        raise InvalidSignalPlanError(
            f"signal plan '{plan.id}' leaves movements unserved: {unserved_str}"
        )


def validate_vehicle_against_intersection(
    vehicle: Vehicle,
    intersection: Intersection,
) -> None:
    approach_ids = {app.id for app in intersection.approaches}

    if vehicle.origin not in approach_ids:
        raise InvalidGeometryError(
            f"vehicle '{vehicle.id}' origin '{vehicle.origin}' "
            f"not found in intersection '{intersection.id}'"
        )

    if vehicle.destination not in approach_ids:
        raise InvalidGeometryError(
            f"vehicle '{vehicle.id}' destination '{vehicle.destination}' "
            f"not found in intersection '{intersection.id}'"
        )

    matching_movements = [
        m
        for m in intersection.movements
        if m.origin == vehicle.origin and m.destination == vehicle.destination
    ]
    if not matching_movements:
        raise InvalidGeometryError(
            f"no movement exists from '{vehicle.origin}' to '{vehicle.destination}' "
            f"in intersection '{intersection.id}'"
        )

    if vehicle.target_lane_id is not None:
        lane = intersection.get_lane(vehicle.target_lane_id)
        if lane.approach_id != vehicle.origin:
            raise InvalidGeometryError(
                f"vehicle target lane '{lane.id}' approach '{lane.approach_id}' "
                f"does not match vehicle origin '{vehicle.origin}'"
            )
        if not any(lane.allows_movement(m.id) for m in matching_movements):
            raise InvalidGeometryError(
                f"target lane '{lane.id}' does not allow movement "
                f"from '{vehicle.origin}' to '{vehicle.destination}'"
            )
