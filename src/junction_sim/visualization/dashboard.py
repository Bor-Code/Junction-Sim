from junction_sim.domain.signal import SignalPlan
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.transition import SignalState


def render_queue_bars(
    queue_lengths: dict[str, int],
    max_bar_width: int = 20,
    max_capacity: int = 20,
) -> str:
    if not queue_lengths:
        return "No active lanes"

    lines: list[str] = []
    for lane_id in sorted(queue_lengths):
        count = queue_lengths[lane_id]
        if max_capacity > 0:
            fill = min(
                max_bar_width,
                round((count / max_capacity) * max_bar_width),
            )
        else:
            fill = 0
        bar = "#" * fill + "-" * (max_bar_width - fill)
        lines.append(f"{lane_id:<12}: [{bar}] {count} veh")
    return "\n".join(lines)


def render_ascii_intersection(
    step: StepResult,
    use_colors: bool = False,
) -> str:
    q_north = sum(
        count
        for lid, count in step.queue_lengths.items()
        if "north" in lid.lower() or "_n_" in lid.lower()
    )
    q_south = sum(
        count
        for lid, count in step.queue_lengths.items()
        if "south" in lid.lower() or "_s_" in lid.lower()
    )
    q_east = sum(
        count
        for lid, count in step.queue_lengths.items()
        if "east" in lid.lower() or "_e_" in lid.lower()
    )
    q_west = sum(
        count
        for lid, count in step.queue_lengths.items()
        if "west" in lid.lower() or "_w_" in lid.lower()
    )

    state_badge = step.signal_state.value.upper()
    if use_colors:
        if step.signal_state == SignalState.GREEN:
            state_badge = f"\033[92m{state_badge}\033[0m"
        elif step.signal_state == SignalState.YELLOW:
            state_badge = f"\033[93m{state_badge}\033[0m"
        else:
            state_badge = f"\033[91m{state_badge}\033[0m"

    lines = [
        "              |   N   |",
        f"              |  [{q_north:^3}]  |",
        "--------------+       +--------------",
        f"W   [{q_west:^3}]       {state_badge:^7}       [{q_east:^3}]   E",
        "--------------+       +--------------",
        f"              |  [{q_south:^3}]  |",
        "              |   S   |",
    ]
    return "\n".join(lines)


def render_step_dashboard(
    step: StepResult,
    plan: SignalPlan | None = None,
    max_bar_width: int = 20,
    use_colors: bool = False,
) -> str:
    total_queue = sum(step.queue_lengths.values())
    state_str = step.signal_state.value.upper()
    if use_colors:
        if step.signal_state == SignalState.GREEN:
            state_str = f"\033[92m{state_str}\033[0m"
        elif step.signal_state == SignalState.YELLOW:
            state_str = f"\033[93m{state_str}\033[0m"
        else:
            state_str = f"\033[91m{state_str}\033[0m"

    if step.controller_decision is not None:
        target = (
            f" -> {step.controller_decision.target_phase_id}"
            if step.controller_decision.target_phase_id
            else ""
        )
        decision_str = f"{step.controller_decision.reason}{target}"
    else:
        decision_str = "none"

    phase_label = step.active_phase_id
    if plan is not None:
        try:
            curr_phase = plan.get_phase(step.active_phase_id)
            movements = ",".join(curr_phase.green_movement_ids)
            phase_label = f"{step.active_phase_id} (serves: {movements})"
        except Exception:
            pass

    header = (
        "=" * 64
        + "\n"
        + f"SIMULATION TIME: {step.time:6.2f}s | STEP #{step.step_index}\n"
        + f"Active Phase:    {phase_label}\n"
        + f"Signal State:    {state_str}\n"
        + f"Decision:        {decision_str}\n"
        + f"Total Queue:     {total_queue} veh | "
        + f"Arrived: {len(step.arrived_vehicles)} | "
        + f"Discharged: {len(step.discharged_vehicles)}\n"
        + "-" * 64
    )

    bars = render_queue_bars(step.queue_lengths, max_bar_width=max_bar_width)
    layout = render_ascii_intersection(step, use_colors=use_colors)
    footer = "=" * 64

    return (
        header
        + "\nQUEUE LENGTHS:\n"
        + bars
        + "\n"
        + "-" * 64
        + "\nINTERSECTION LAYOUT:\n"
        + layout
        + "\n"
        + footer
    )
