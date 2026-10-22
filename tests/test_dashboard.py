from junction_sim.controllers.protocol import ControllerDecision
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.transition import SignalState
from junction_sim.visualization import (
    render_ascii_intersection,
    render_queue_bars,
    render_step_dashboard,
)


def test_render_queue_bars_empty() -> None:
    res = render_queue_bars({})
    assert res == "No active lanes"


def test_render_queue_bars_populated() -> None:
    lengths = {
        "lane_n_0": 5,
        "lane_s_0": 25,
    }
    res = render_queue_bars(lengths, max_bar_width=10, max_capacity=20)
    lines = res.split("\n")
    assert len(lines) == 2
    assert "lane_n_0" in lines[0]
    assert "lane_s_0" in lines[1]
    assert "[##--------]" in lines[0]
    assert "[##########]" in lines[1]


def test_render_queue_bars_zero_capacity() -> None:
    lengths = {"lane_n_0": 5}
    res = render_queue_bars(lengths, max_bar_width=10, max_capacity=0)
    assert "[----------]" in res


def test_render_ascii_intersection_plain() -> None:
    step = StepResult(
        step_index=1,
        time=1.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={
            "north_0": 3,
            "lane_s_0": 4,
            "east_0": 2,
            "lane_w_0": 6,
        },
        controller_decision=None,
    )
    ascii_art = render_ascii_intersection(step, use_colors=False)
    assert "[ 3 ]" in ascii_art
    assert "[ 4 ]" in ascii_art
    assert "[ 2 ]" in ascii_art
    assert "[ 6 ]" in ascii_art
    assert "GREEN" in ascii_art


def test_render_ascii_intersection_colors() -> None:
    step_green = StepResult(
        step_index=1,
        time=1.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={},
        controller_decision=None,
    )
    art_green = render_ascii_intersection(step_green, use_colors=True)
    assert "\033[92m" in art_green

    step_yellow = StepResult(
        step_index=2,
        time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={},
        controller_decision=None,
    )
    art_yellow = render_ascii_intersection(step_yellow, use_colors=True)
    assert "\033[93m" in art_yellow

    step_red = StepResult(
        step_index=3,
        time=3.0,
        active_phase_id="P1",
        signal_state=SignalState.ALL_RED,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={},
        controller_decision=None,
    )
    art_red = render_ascii_intersection(step_red, use_colors=True)
    assert "\033[91m" in art_red


def test_render_step_dashboard_full_features() -> None:
    v_arr = Vehicle(id="V1", origin="north", destination="south", arrival_time=1.0)
    v_dis = Vehicle(
        id="V2",
        origin="north",
        destination="south",
        arrival_time=0.0,
        departure_time=1.0,
    )
    decision = ControllerDecision(
        target_phase_id="P2",
        reason="max_pressure_shift",
    )
    step = StepResult(
        step_index=5,
        time=5.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(v_arr,),
        discharged_vehicles=(v_dis,),
        queue_lengths={"lane_n_0": 4},
        controller_decision=decision,
    )
    p1 = SignalPhase(id="P1", green_movement_ids=("M1",), green_duration=10.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("M2",), green_duration=10.0)
    plan = SignalPlan(id="PLAN1", phases=(p1, p2))

    out = render_step_dashboard(step, plan=plan, use_colors=True)
    assert "SIMULATION TIME:   5.00s | STEP #5" in out
    assert "Active Phase:    P1 (serves: M1)" in out
    assert "max_pressure_shift -> P2" in out
    assert "\033[92m" in out
    assert "lane_n_0" in out

    out_no_colors = render_step_dashboard(step, plan=plan, use_colors=False)
    assert "\033[92m" not in out_no_colors
    assert "GREEN" in out_no_colors


def test_render_step_dashboard_variations() -> None:
    decision_no_target = ControllerDecision(
        target_phase_id=None,
        reason="gap_out",
    )
    step_yellow = StepResult(
        step_index=6,
        time=6.0,
        active_phase_id="P_UNKNOWN",
        signal_state=SignalState.YELLOW,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={},
        controller_decision=decision_no_target,
    )
    p1 = SignalPhase(id="P1", green_movement_ids=("M1",), green_duration=10.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("M2",), green_duration=10.0)
    plan = SignalPlan(id="PLAN1", phases=(p1, p2))

    out_yellow = render_step_dashboard(step_yellow, plan=plan, use_colors=True)
    assert "gap_out" in out_yellow
    assert "\033[93m" in out_yellow
    assert "Active Phase:    P_UNKNOWN" in out_yellow

    step_red_no_plan = StepResult(
        step_index=7,
        time=7.0,
        active_phase_id="P1",
        signal_state=SignalState.ALL_RED,
        arrived_vehicles=(),
        discharged_vehicles=(),
        queue_lengths={},
        controller_decision=None,
    )
    out_red = render_step_dashboard(step_red_no_plan, plan=None, use_colors=True)
    assert "\033[91m" in out_red
    assert "Decision:        none" in out_red
