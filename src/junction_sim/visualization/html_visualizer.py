import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.engine.step_result import StepResult


def serialize_simulation_data(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    step_size: float = 1.0,
) -> dict[str, Any]:
    approaches_data: list[dict[str, Any]] = []
    for app in intersection.approaches:
        lanes_data: list[dict[str, Any]] = []
        for ln in app.lanes:
            lanes_data.append(
                {
                    "id": ln.id,
                    "approach_id": ln.approach_id,
                    "allowed_movement_ids": list(ln.allowed_movement_ids),
                    "max_capacity": ln.max_capacity,
                }
            )
        approaches_data.append(
            {
                "id": app.id,
                "direction": app.direction.value,
                "lanes": lanes_data,
            }
        )

    movements_data: list[dict[str, Any]] = []
    for mv in intersection.movements:
        movements_data.append(
            {
                "id": mv.id,
                "origin": mv.origin,
                "destination": mv.destination,
                "turn_type": mv.turn_type.value,
                "saturation_flow_rate": mv.saturation_flow_rate,
            }
        )

    crosswalks_data: list[dict[str, Any]] = []
    for cw in intersection.crosswalks:
        crosswalks_data.append(
            {
                "id": cw.id,
                "approach_id": cw.approach_id,
                "length_meters": cw.length_meters,
                "pedestrian_speed_mps": cw.pedestrian_speed_mps,
                "walk_duration": cw.walk_duration,
                "clearance_duration": cw.effective_clearance_duration,
            }
        )

    phases_data: list[dict[str, Any]] = []
    for ph in signal_plan.phases:
        phases_data.append(
            {
                "id": ph.id,
                "green_movement_ids": list(ph.green_movement_ids),
                "pedestrian_crosswalk_ids": list(ph.pedestrian_crosswalk_ids),
                "green_duration": ph.green_duration,
                "min_green": ph.min_green,
                "max_green": ph.max_green,
                "yellow_duration": ph.yellow_duration,
                "all_red_duration": ph.all_red_duration,
            }
        )

    steps_data: list[dict[str, Any]] = []
    for r in results:
        dec_dict = (
            {
                "target_phase_id": r.controller_decision.target_phase_id,
                "reason": r.controller_decision.reason,
            }
            if r.controller_decision is not None
            else None
        )
        discharged_veh: list[dict[str, Any]] = []
        for v in r.discharged_vehicles:
            discharged_veh.append(
                {
                    "id": v.id,
                    "origin": v.origin,
                    "destination": v.destination,
                    "arrival_time": v.arrival_time,
                    "departure_time": v.departure_time,
                    "waiting_time": v.waiting_time(r.time),
                }
            )
        discharged_ped: list[dict[str, Any]] = []
        for p in r.discharged_pedestrians:
            discharged_ped.append(
                {
                    "id": p.id,
                    "crosswalk_id": p.crosswalk_id,
                    "arrival_time": p.arrival_time,
                    "crossing_start_time": p.crossing_start_time,
                    "crossing_completion_time": p.crossing_completion_time,
                    "waiting_time": p.waiting_time(r.time),
                }
            )
        ped_signals: dict[str, str] = {
            k: v.value for k, v in r.pedestrian_signals.items()
        }
        steps_data.append(
            {
                "time": r.time,
                "step_index": r.step_index,
                "active_phase_id": r.active_phase_id,
                "signal_state": r.signal_state.value,
                "arrived_vehicle_ids": [v.id for v in r.arrived_vehicles],
                "discharged_vehicles": discharged_veh,
                "queue_lengths": r.queue_lengths,
                "controller_decision": dec_dict,
                "arrived_pedestrians": [p.id for p in r.arrived_pedestrians],
                "discharged_pedestrians": discharged_ped,
                "pedestrian_queue_lengths": r.pedestrian_queue_lengths,
                "pedestrian_signals": ped_signals,
            }
        )

    total_arrivals = sum(len(r.arrived_vehicles) for r in results)
    total_discharges = sum(len(r.discharged_vehicles) for r in results)
    all_delays = [
        v.waiting_time(r.time) for r in results for v in r.discharged_vehicles
    ]
    avg_delay = sum(all_delays) / len(all_delays) if all_delays else 0.0
    max_delay = max(all_delays) if all_delays else 0.0

    return {
        "metadata": {
            "controller": controller_name,
            "scenario": scenario_name,
            "seed": seed,
            "step_size": step_size,
            "duration": results[-1].time if results else 0.0,
            "total_steps": len(results),
            "total_arrivals": total_arrivals,
            "total_discharges": total_discharges,
            "average_delay": avg_delay,
            "max_delay": max_delay,
        },
        "intersection": {
            "id": intersection.id,
            "approaches": approaches_data,
            "movements": movements_data,
            "crosswalks": crosswalks_data,
        },
        "signal_plan": {
            "id": signal_plan.id,
            "cycle_length": signal_plan.cycle_length,
            "phases": phases_data,
        },
        "steps": steps_data,
    }


def generate_interactive_html(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    step_size: float = 1.0,
) -> str:
    sim_data = serialize_simulation_data(
        results=results,
        intersection=intersection,
        signal_plan=signal_plan,
        controller_name=controller_name,
        scenario_name=scenario_name,
        seed=seed,
        step_size=step_size,
    )
    json_blob = json.dumps(sim_data)

    parts = [
        "<!DOCTYPE html>\n",
        '<html lang="en">\n',
        "<head>\n",
        '<meta charset="UTF-8">\n',
        '<meta name="viewport" ',
        'content="width=device-width, initial-scale=1.0">\n',
        "<title>Junction-Sim Interactive Visualizer</title>\n",
        "<style>\n",
        "  :root {\n",
        "    --bg-primary: #0a0e17;\n",
        "    --bg-secondary: #111827;\n",
        "    --bg-card: rgba(17, 24, 39, 0.85);\n",
        "    --border-color: rgba(255, 255, 255, 0.1);\n",
        "    --text-primary: #f8fafc;\n",
        "    --text-secondary: #94a3b8;\n",
        "    --accent-primary: #6366f1;\n",
        "    --accent-emerald: #10b981;\n",
        "    --accent-amber: #f59e0b;\n",
        "    --accent-rose: #ef4444;\n",
        "    --accent-sky: #0ea5e9;\n",
        "  }\n",
        "  * { box-sizing: border-box; margin: 0; padding: 0; }\n",
        "  body {\n",
        "    background-color: var(--bg-primary);\n",
        "    color: var(--text-primary);\n",
        "    font-family: -apple-system, BlinkMacSystemFont, sans-serif;\n",
        "    min-height: 100vh; display: flex; flex-direction: column;\n",
        "  }\n",
        "  header {\n",
        "    background: var(--bg-card); backdrop-filter: blur(12px);\n",
        "    border-bottom: 1px solid var(--border-color);\n",
        "    padding: 12px 24px; display: flex;\n",
        "    justify-content: space-between; align-items: center;\n",
        "  }\n",
        "  .brand-title {\n",
        "    font-size: 18px; font-weight: 800; color: #fff;\n",
        "  }\n",
        "  .brand-badge {\n",
        "    font-size: 11px; padding: 3px 8px;\n",
        "    background: rgba(99, 102, 241, 0.2);\n",
        "    border: 1px solid rgba(99, 102, 241, 0.4);\n",
        "    color: #818cf8; border-radius: 12px;\n",
        "  }\n",
        "  .meta-pills { display: flex; gap: 10px; flex-wrap: wrap; }\n",
        "  .meta-pill {\n",
        "    background: rgba(255, 255, 255, 0.04);\n",
        "    border: 1px solid var(--border-color);\n",
        "    padding: 5px 10px; border-radius: 6px; font-size: 12px;\n",
        "  }\n",
        "  .main-layout {\n",
        "    display: grid; grid-template-columns: 1fr 360px;\n",
        "    gap: 16px; padding: 16px; flex: 1;\n",
        "  }\n",
        "  @media (max-width: 960px) {\n",
        "    .main-layout { grid-template-columns: 1fr; }\n",
        "  }\n",
        "  .canvas-panel {\n",
        "    background: var(--bg-card);\n",
        "    border: 1px solid var(--border-color);\n",
        "    border-radius: 12px; padding: 12px;\n",
        "    display: flex; justify-content: center; align-items: center;\n",
        "  }\n",
        "  canvas {\n",
        "    border-radius: 8px; background: #0f172a;\n",
        "    max-width: 100%; height: auto;\n",
        "  }\n",
        "  .telemetry-panel {\n",
        "    display: flex; flex-direction: column; gap: 12px;\n",
        "  }\n",
        "  .card {\n",
        "    background: var(--bg-card);\n",
        "    border: 1px solid var(--border-color);\n",
        "    border-radius: 10px; padding: 12px;\n",
        "  }\n",
        "  .card-title {\n",
        "    font-size: 11px; font-weight: 700; color: var(--text-secondary);\n",
        "    text-transform: uppercase; margin-bottom: 8px;\n",
        "  }\n",
        "  .signal-badge-row { display: flex; gap: 8px; align-items: center; }\n",
        "  .phase-badge {\n",
        "    padding: 5px 12px; border-radius: 6px; font-weight: 800;\n",
        "    font-size: 14px; background: rgba(99, 102, 241, 0.2);\n",
        "    border: 1px solid var(--accent-primary); color: #c7d2fe;\n",
        "  }\n",
        "  .state-badge {\n",
        "    padding: 5px 12px; border-radius: 6px; font-weight: 800;\n",
        "    font-size: 13px; text-transform: uppercase;\n",
        "  }\n",
        "  .state-green {\n",
        "    background: rgba(16, 185, 129, 0.2);\n",
        "    border: 1px solid var(--accent-emerald);\n",
        "    color: var(--accent-emerald);\n",
        "  }\n",
        "  .state-yellow {\n",
        "    background: rgba(245, 158, 11, 0.2);\n",
        "    border: 1px solid var(--accent-amber);\n",
        "    color: var(--accent-amber);\n",
        "  }\n",
        "  .state-red {\n",
        "    background: rgba(239, 68, 68, 0.2);\n",
        "    border: 1px solid var(--accent-rose);\n",
        "    color: var(--accent-rose);\n",
        "  }\n",
        "  .decision-box {\n",
        "    margin-top: 8px; padding: 6px 10px; background: rgba(0, 0, 0, 0.3);\n",
        "    border-radius: 6px; font-size: 12px; font-family: monospace;\n",
        "  }\n",
        "  .kpi-grid {\n",
        "    display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;\n",
        "  }\n",
        "  .kpi-box {\n",
        "    background: rgba(0, 0, 0, 0.2); padding: 8px; border-radius: 6px;\n",
        "  }\n",
        "  .kpi-label {\n",
        "    font-size: 10px; color: var(--text-secondary);\n",
        "    text-transform: uppercase;\n",
        "  }\n",
        "  .kpi-value {\n",
        "    font-size: 16px; font-weight: 800; margin-top: 2px;\n",
        "  }\n",
        "  .queue-list {\n",
        "    display: flex; flex-direction: column; gap: 6px;\n",
        "    max-height: 180px; overflow-y: auto;\n",
        "  }\n",
        "  .queue-item {\n",
        "    display: flex; align-items: center; gap: 6px; font-size: 12px;\n",
        "  }\n",
        "  .queue-lane-id {\n",
        "    width: 80px; font-family: monospace;\n",
        "    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;\n",
        "  }\n",
        "  .queue-bar-track {\n",
        "    flex: 1; height: 8px; background: rgba(255, 255, 255, 0.08);\n",
        "    border-radius: 4px; overflow: hidden;\n",
        "  }\n",
        "  .queue-bar-fill {\n",
        "    height: 100%; background: var(--accent-sky);\n",
        "  }\n",
        "  .queue-val { width: 35px; text-align: right; font-weight: 700; }\n",
        "  .playback-bar {\n",
        "    background: var(--bg-card);\n",
        "    border-top: 1px solid var(--border-color);\n",
        "    padding: 10px 20px; display: flex;\n",
        "    align-items: center; gap: 16px;\n",
        "  }\n",
        "  .playback-buttons { display: flex; gap: 6px; }\n",
        "  .btn {\n",
        "    background: rgba(255, 255, 255, 0.06);\n",
        "    border: 1px solid var(--border-color); color: var(--text-primary);\n",
        "    padding: 6px 12px; border-radius: 6px; font-size: 12px;\n",
        "    font-weight: 700; cursor: pointer;\n",
        "  }\n",
        "  .btn.btn-primary {\n",
        "    background: var(--accent-primary);\n",
        "    border-color: var(--accent-primary);\n",
        "  }\n",
        "  .timeline-container {\n",
        "    flex: 1; display: flex; align-items: center; gap: 10px;\n",
        "  }\n",
        "  .timeline-slider {\n",
        "    flex: 1; height: 6px; cursor: pointer;\n",
        "  }\n",
        "  .time-display {\n",
        "    font-family: monospace; font-size: 12px; min-width: 90px;\n",
        "  }\n",
        "  .speed-group { display: flex; gap: 4px; }\n",
        "  .speed-btn {\n",
        "    padding: 4px 6px; font-size: 10px; border-radius: 4px;\n",
        "    background: rgba(255, 255, 255, 0.04);\n",
        "    border: 1px solid var(--border-color);\n",
        "    color: var(--text-secondary); cursor: pointer;\n",
        "  }\n",
        "  .speed-btn.active {\n",
        "    background: var(--accent-primary); color: #fff;\n",
        "  }\n",
        "</style>\n",
        "</head>\n",
        "<body>\n",
        "<header>\n",
        "  <div>\n",
        '    <span class="brand-title">JUNCTION-SIM</span>\n',
        '    <span class="brand-badge">VISUALIZER</span>\n',
        "  </div>\n",
        '  <div class="meta-pills">\n',
        '    <div class="meta-pill">Scenario: <b id="p-sc">-</b></div>\n',
        '    <div class="meta-pill">Controller: <b id="p-ctrl">-</b></div>\n',
        '    <div class="meta-pill">Steps: <b id="p-steps">-</b></div>\n',
        "  </div>\n",
        "</header>\n",
        '<main class="main-layout">\n',
        '  <div class="canvas-panel">\n',
        '    <canvas id="sim-canvas" width="800" height="800"></canvas>\n',
        "  </div>\n",
        '  <div class="telemetry-panel">\n',
        '    <div class="card">\n',
        '      <div class="card-title">Signal Telemetry</div>\n',
        '      <div class="signal-badge-row">\n',
        '        <div class="phase-badge" id="disp-phase">P1</div>\n',
        '        <div class="state-badge state-green" ',
        'id="disp-state">GREEN</div>\n',
        "      </div>\n",
        '      <div class="decision-box" id="disp-decision">Decision</div>\n',
        "    </div>\n",
        '    <div class="card">\n',
        '      <div class="card-title">Metrics</div>\n',
        '      <div class="kpi-grid">\n',
        '        <div class="kpi-box">\n',
        '          <div class="kpi-label">Queue</div>\n',
        '          <div class="kpi-value" id="kpi-q">0</div>\n',
        "        </div>\n",
        '        <div class="kpi-box">\n',
        '          <div class="kpi-label">Discharged</div>\n',
        '          <div class="kpi-value" id="kpi-dis">0</div>\n',
        "        </div>\n",
        '        <div class="kpi-box">\n',
        '          <div class="kpi-label">Arrivals</div>\n',
        '          <div class="kpi-value" id="kpi-arr">0</div>\n',
        "        </div>\n",
        '        <div class="kpi-box">\n',
        '          <div class="kpi-label">Avg Delay</div>\n',
        '          <div class="kpi-value" id="kpi-del">0.0s</div>\n',
        "        </div>\n",
        "      </div>\n",
        "    </div>\n",
        '    <div class="card">\n',
        '      <div class="card-title">Lane Queues</div>\n',
        '      <div class="queue-list" id="queue-list"></div>\n',
        "    </div>\n",
        "  </div>\n",
        "</main>\n",
        '<footer class="playback-bar">\n',
        '  <div class="playback-buttons">\n',
        '    <button class="btn btn-primary" id="btn-play">Play</button>\n',
        '    <button class="btn" id="btn-prev">Back</button>\n',
        '    <button class="btn" id="btn-next">Next</button>\n',
        '    <button class="btn" id="btn-rst">Reset</button>\n',
        "  </div>\n",
        '  <div class="timeline-container">\n',
        '    <input type="range" class="timeline-slider" ',
        'id="scrubber" min="0" max="0" value="0">\n',
        '    <div class="time-display" id="time-display">0.0s</div>\n',
        "  </div>\n",
        '  <div class="speed-group">\n',
        '    <button class="speed-btn active" data-speed="1.0">1x</button>\n',
        '    <button class="speed-btn" data-speed="2.0">2x</button>\n',
        "  </div>\n",
        "</footer>\n",
        "<script>\n",
        "const DATA = " + json_blob + ";\n",
        "class IntersectionVisualizer {\n",
        "  constructor(data) {\n",
        "    this.data = data;\n",
        "    this.canvas = document.getElementById('sim-canvas');\n",
        "    this.ctx = this.canvas.getContext('2d');\n",
        "    this.idx = 0;\n",
        "    this.isPlaying = false;\n",
        "    this.speed = 1.0;\n",
        "    this.initUI();\n",
        "    this.bindEvents();\n",
        "    this.render();\n",
        "  }\n",
        "  initUI() {\n",
        "    document.getElementById('p-sc').textContent = "
        "this.data.metadata.scenario;\n",
        "    document.getElementById('p-ctrl').textContent = "
        "this.data.metadata.controller;\n",
        "    document.getElementById('p-steps').textContent = "
        "this.data.metadata.total_steps;\n",
        "    const sc = document.getElementById('scrubber');\n",
        "    sc.max = Math.max(0, this.data.steps.length - 1);\n",
        "  }\n",
        "  bindEvents() {\n",
        "    document.getElementById('btn-play').addEventListener('click', "
        "() => this.toggle());\n",
        "    document.getElementById('btn-prev').addEventListener('click', "
        "() => this.stepBy(-1));\n",
        "    document.getElementById('btn-next').addEventListener('click', "
        "() => this.stepBy(1));\n",
        "    document.getElementById('btn-rst').addEventListener('click', "
        "() => this.setStep(0));\n",
        "    document.getElementById('scrubber').addEventListener('input', "
        "(e) => this.setStep(parseInt(e.target.value, 10)));\n",
        "    document.querySelectorAll('.speed-btn').forEach((b) => {\n",
        "      b.addEventListener('click', () => {\n",
        "        document.querySelectorAll('.speed-btn').forEach("
        "(x) => x.classList.remove('active'));\n",
        "        b.classList.add('active');\n",
        "        this.speed = parseFloat(b.getAttribute('data-speed'));\n",
        "      });\n",
        "    });\n",
        "  }\n",
        "  toggle() {\n",
        "    this.isPlaying = !this.isPlaying;\n",
        "    document.getElementById('btn-play').textContent = "
        "this.isPlaying ? 'Pause' : 'Play';\n",
        "    if (this.isPlaying) this.loop();\n",
        "  }\n",
        "  stepBy(d) {\n",
        "    this.isPlaying = false;\n",
        "    document.getElementById('btn-play').textContent = 'Play';\n",
        "    this.setStep(this.idx + d);\n",
        "  }\n",
        "  setStep(i) {\n",
        "    if (!this.data.steps.length) return;\n",
        "    this.idx = Math.max(0, Math.min(i, this.data.steps.length - 1));\n",
        "    document.getElementById('scrubber').value = this.idx;\n",
        "    this.render();\n",
        "  }\n",
        "  loop() {\n",
        "    if (!this.isPlaying) return;\n",
        "    if (this.idx < this.data.steps.length - 1) {\n",
        "      this.setStep(this.idx + 1);\n",
        "      setTimeout(() => this.loop(), 500 / this.speed);\n",
        "    } else {\n",
        "      this.isPlaying = false;\n",
        "      document.getElementById('btn-play').textContent = 'Play';\n",
        "    }\n",
        "  }\n",
        "  render() {\n",
        "    const ctx = this.ctx;\n",
        "    const w = this.canvas.width;\n",
        "    const h = this.canvas.height;\n",
        "    ctx.clearRect(0, 0, w, h);\n",
        "    const cx = w / 2, cy = h / 2, rw = 160, hr = rw / 2;\n",
        "    ctx.fillStyle = '#1e293b';\n",
        "    ctx.fillRect(cx - hr, 0, rw, h);\n",
        "    ctx.fillRect(0, cy - hr, w, rw);\n",
        "    ctx.fillStyle = '#334155';\n",
        "    ctx.fillRect(cx - hr, cy - hr, rw, rw);\n",
        "    const step = this.data.steps[this.idx];\n",
        "    if (!step) return;\n",
        "    const isG = step.signal_state === 'green';\n",
        "    const isY = step.signal_state === 'yellow';\n",
        "    ctx.fillStyle = isG ? '#10b981' : (isY ? '#f59e0b' : '#ef4444');\n",
        "    ctx.beginPath();\n",
        "    ctx.arc(cx, cy, 14, 0, Math.PI * 2);\n",
        "    ctx.fill();\n",
        "    this.telemetry(step);\n",
        "  }\n",
        "  telemetry(step) {\n",
        "    document.getElementById('disp-phase').textContent = "
        "step.active_phase_id;\n",
        "    const st = document.getElementById('disp-state');\n",
        "    st.textContent = step.signal_state.toUpperCase();\n",
        "    st.className = 'state-badge state-' + "
        "(step.signal_state === 'green' ? 'green' : "
        "(step.signal_state === 'yellow' ? 'yellow' : 'red'));\n",
        "    const d = step.controller_decision;\n",
        "    document.getElementById('disp-decision').textContent = "
        "d ? d.reason : 'none';\n",
        "    const tq = Object.values(step.queue_lengths || {})"
        ".reduce((a, b) => a + b, 0);\n",
        "    document.getElementById('kpi-q').textContent = tq;\n",
        "    document.getElementById('time-display').textContent = "
        "step.time.toFixed(1) + 's';\n",
        "    const ql = document.getElementById('queue-list');\n",
        "    ql.innerHTML = '';\n",
        "    Object.entries(step.queue_lengths || {}).forEach(([k, v]) => {\n",
        "      const el = document.createElement('div');\n",
        "      el.className = 'queue-item';\n",
        "      el.innerHTML = '<span class=\"queue-lane-id\">' + k + "
        "'</span>' + \n"
        '        \'<div class="queue-bar-track"><div '
        'class="queue-bar-fill" style="width:\' + '
        "Math.min(100, v * 5) + '%\"></div></div>' + \n"
        "        '<span class=\"queue-val\">' + v + '</span>';\n",
        "      ql.appendChild(el);\n",
        "    });\n",
        "  }\n",
        "}\n",
        "document.addEventListener('DOMContentLoaded', "
        "() => new IntersectionVisualizer(DATA));\n",
        "</script>\n",
        "</body>\n",
        "</html>\n",
    ]
    return "".join(parts)


def export_interactive_html(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    destination: Path | str | TextIO | None = None,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    step_size: float = 1.0,
) -> str:
    html_content = generate_interactive_html(
        results=results,
        intersection=intersection,
        signal_plan=signal_plan,
        controller_name=controller_name,
        scenario_name=scenario_name,
        seed=seed,
        step_size=step_size,
    )

    if destination is None:
        return html_content

    if isinstance(destination, (str, Path)):
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html_content, encoding="utf-8")
        return html_content

    destination.write(html_content)
    return ""
