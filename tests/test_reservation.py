import io
from pathlib import Path

import pytest

from junction_sim.cli import main
from junction_sim.cli.commands import instantiate_controller
from junction_sim.controllers.protocol import ControllerContext
from junction_sim.controllers.reservation import (
    ReservationController,
    ReservationGrid,
    ReservationRequest,
    ReservationStatus,
    ReservationTile,
)
from junction_sim.domain.signal import SignalPhase, SignalPlan, SignalState
from junction_sim.exceptions import ConfigurationError, ValidationError
from junction_sim.presets import get_preset


def test_reservation_models() -> None:
    tile = ReservationTile(grid_x=1, grid_y=2, time_index=5)
    assert tile.grid_x == 1
    assert tile.grid_y == 2
    assert tile.time_index == 5

    with pytest.raises(ValidationError, match="cannot be empty"):
        ReservationRequest(
            vehicle_id="veh_1",
            movement_id="NB_T",
            arrival_time=10.0,
            traversal_duration=3.0,
            cells=(),
        )

    req = ReservationRequest(
        vehicle_id="veh_1",
        movement_id="NB_T",
        arrival_time=10.0,
        traversal_duration=3.0,
        cells=((0, 0), (1, 0)),
    )
    assert req.vehicle_id == "veh_1"
    assert req.traversal_duration == 3.0


def test_reservation_grid_validation_and_bounds() -> None:
    with pytest.raises(ValidationError, match="must be positive"):
        ReservationGrid(cell_size_m=0.0)

    with pytest.raises(ValidationError, match="must be positive"):
        ReservationGrid(time_step_s=-1.0)

    with pytest.raises(ValidationError, match="must be positive"):
        ReservationGrid(grid_width_m=0.0)

    with pytest.raises(ValidationError, match="must be positive"):
        ReservationGrid(grid_height_m=-5.0)

    grid = ReservationGrid(
        cell_size_m=5.0,
        time_step_s=0.5,
        grid_width_m=20.0,
        grid_height_m=20.0,
    )
    assert grid.cols == 4
    assert grid.rows == 4

    bad_req = ReservationRequest(
        vehicle_id="v_bad",
        movement_id="NB_T",
        arrival_time=0.0,
        traversal_duration=1.0,
        cells=((10, 10),),
    )
    with pytest.raises(ValidationError, match="outside grid bounds"):
        grid.request_reservation(bad_req)


def test_reservation_grid_conflicts_and_cleanup() -> None:
    grid = ReservationGrid(
        cell_size_m=5.0,
        time_step_s=1.0,
        grid_width_m=20.0,
        grid_height_m=20.0,
    )

    req1 = ReservationRequest(
        vehicle_id="v1",
        movement_id="NB_T",
        arrival_time=1.0,
        traversal_duration=2.0,
        cells=((1, 1), (1, 2)),
    )
    status1 = grid.request_reservation(req1)
    assert status1 == ReservationStatus.GRANTED
    assert grid.granted_count == 1
    assert grid.total_reservations == 1

    req2_conflict = ReservationRequest(
        vehicle_id="v2",
        movement_id="EB_T",
        arrival_time=1.5,
        traversal_duration=2.0,
        cells=((1, 1),),
    )
    status2 = grid.request_reservation(req2_conflict)
    assert status2 == ReservationStatus.REJECTED
    assert grid.rejected_count == 1

    cleaned = grid.clean_expired(current_time=5.0)
    assert cleaned > 0

    grid.clear()
    assert grid.granted_count == 0
    assert grid.rejected_count == 0
    assert grid.total_reservations == 0


def test_reservation_controller_lifecycle() -> None:
    scenario = get_preset("webster_four_way")
    inter, plan, _, _ = scenario.build_scenario()

    ctrl = instantiate_controller("reservation", plan, inter)
    assert isinstance(ctrl, ReservationController)
    assert ctrl.grid is not None

    ctrl.reset()

    ctx_trans = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={},
    )
    dec_trans = ctrl.decide(ctx_trans)
    assert dec_trans.reason == "in_transition"

    ctx_min = ControllerContext(
        current_time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_north_0": 5},
    )
    dec_min = ctrl.decide(ctx_min)
    assert dec_min.reason == "min_green_enforced"

    first_lane = inter.approaches[0].lanes[0].id
    ctx_demand = ControllerContext(
        current_time=20.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={first_lane: 10},
    )
    dec_demand = ctrl.decide(ctx_demand)
    assert dec_demand.reason is not None

    ctx_idle = ControllerContext(
        current_time=50.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    dec_idle = ctrl.decide(ctx_idle)
    assert dec_idle.reason == "reservation_hold_phase"


def test_reservation_controller_conflict_rejection() -> None:
    scenario = get_preset("webster_four_way")
    inter, _, _, _ = scenario.build_scenario()

    phases = (
        SignalPhase(id="P1", green_movement_ids=("N_T",), green_duration=10.0),
        SignalPhase(id="P2", green_movement_ids=("S_T",), green_duration=10.0),
        SignalPhase(id="P3", green_movement_ids=("E_T",), green_duration=10.0),
    )
    plan3 = SignalPlan(id="plan3", phases=phases)
    ctrl = ReservationController(signal_plan=plan3, intersection=inter)

    p2_cells = ctrl._synthesize_trajectory_cells(1)
    req_block = ReservationRequest(
        vehicle_id="blocker",
        movement_id="P2",
        arrival_time=20.0,
        traversal_duration=5.0,
        cells=p2_cells,
    )
    assert ctrl.grid.request_reservation(req_block) == ReservationStatus.GRANTED

    ctx = ControllerContext(
        current_time=20.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"lane_s_0": 10, "lane_e_0": 10},
    )
    dec = ctrl.decide(ctx)
    assert dec.reason == "reservation_granted_P3"
    assert dec.target_phase_id == "P3"


def test_cli_reservation_controller(tmp_path: Path) -> None:
    out = io.StringIO()
    err = io.StringIO()
    code_run = main(
        [
            "run",
            "--preset",
            "webster_four_way",
            "--controller",
            "reservation",
            "--duration",
            "10",
        ],
        stdout=out,
        stderr=err,
    )
    assert code_run == 0
    assert "Simulation Execution Summary" in out.getvalue()
    assert "reservation" in out.getvalue()

    out_vis = io.StringIO()
    html_target = tmp_path / "vis_res.html"
    code_vis = main(
        [
            "visualize",
            "--preset",
            "webster_four_way",
            "--controller",
            "reservation",
            "--duration",
            "5",
            "--out-html",
            str(html_target),
        ],
        stdout=out_vis,
        stderr=err,
    )
    assert code_vis == 0
    assert html_target.exists()


def test_instantiate_controller_unknown_includes_reservation() -> None:
    scenario = get_preset("webster_four_way")
    inter, plan, _, _ = scenario.build_scenario()
    with pytest.raises(ConfigurationError, match="reservation"):
        instantiate_controller("bad_name", plan, inter)
