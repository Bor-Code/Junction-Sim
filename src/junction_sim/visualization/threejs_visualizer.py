import json
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.trajectories import (
    TrajectoryEngine,
    export_trajectories_to_dict,
)
from junction_sim.visualization.html_visualizer import serialize_simulation_data


def generate_3d_html_visualizer(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    step_size: float = 1.0,
    substep_dt: float = 0.2,
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

    traj_engine = TrajectoryEngine(
        intersection=intersection,
        signal_plan=signal_plan,
        discharge_headway=1.8,
        safety_gap=2.5,
    )
    raw_trajectories = traj_engine.generate_vehicle_states(
        results=results, substep_dt=substep_dt
    )
    trajectories_data = export_trajectories_to_dict(raw_trajectories)

    sim_data["trajectories"] = trajectories_data

    json_payload = json.dumps(sim_data)

    font_url = (
        "https://fonts.googleapis.com/css2?"
        "family=JetBrains+Mono:wght@400;600;700&"
        "family=Outfit:wght@400;500;600;700;800&display=swap"
    )
    three_cdn = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
    orbit_cdn = (
        "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/"
        "OrbitControls.js"
    )

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>Junction-Sim Photorealistic 3D Simulation</title>",
        '  <link rel="preconnect" href="https://fonts.googleapis.com">',
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'  <link href="{font_url}" rel="stylesheet">',
        f'  <script src="{three_cdn}"></script>',
        f'  <script src="{orbit_cdn}"></script>',
        "  <style>",
        "    :root {",
        "      --bg-glass: rgba(15, 23, 42, 0.85);",
        "      --border-glass: rgba(255, 255, 255, 0.12);",
        "      --accent-blue: #38bdf8;",
        "      --accent-emerald: #10b981;",
        "      --accent-amber: #f59e0b;",
        "      --text-main: #f8fafc;",
        "      --text-muted: #94a3b8;",
        "    }",
        "    * { box-sizing: border-box; margin: 0; padding: 0; }",
        "    body, html {",
        "      width: 100%; height: 100%; overflow: hidden;",
        '      font-family: "Outfit", sans-serif;',
        "      background-color: #030712;",
        "      color: var(--text-main);",
        "      user-select: none;",
        "    }",
        "    #webgl-canvas {",
        "      width: 100%; height: 100%; display: block; outline: none;",
        "    }",
        "    .hud-layer {",
        "      position: absolute; inset: 0; pointer-events: none;",
        "      display: flex; flex-direction: column;",
        "      justify-content: space-between; padding: 18px; z-index: 10;",
        "    }",
        "    .interactive { pointer-events: auto; }",
        "    .glass-card {",
        "      background: var(--bg-glass); backdrop-filter: blur(16px);",
        "      -webkit-backdrop-filter: blur(16px);",
        "      border: 1px solid var(--border-glass); border-radius: 14px;",
        "      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);",
        "    }",
        "    .header-bar {",
        "      display: flex; justify-content: space-between;",
        "      align-items: flex-start; gap: 16px;",
        "    }",
        "    .brand-card {",
        "      padding: 12px 18px; display: flex;",
        "      flex-direction: column; gap: 3px;",
        "    }",
        "    .brand-title {",
        "      font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em;",
        "      background: linear-gradient(135deg, #38bdf8, #818cf8);",
        "      -webkit-background-clip: text;",
        "      -webkit-text-fill-color: transparent;",
        "      display: flex; align-items: center; gap: 8px;",
        "    }",
        "    .brand-badge {",
        "      font-size: 0.65rem; font-weight: 700; text-transform: uppercase;",
        "      letter-spacing: 0.05em; background: rgba(56, 189, 248, 0.2);",
        "      color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4);",
        "      padding: 2px 6px; border-radius: 6px;",
        "      -webkit-text-fill-color: initial;",
        "    }",
        "    .brand-subtitle {",
        "      font-size: 0.78rem; color: var(--text-muted);",
        '      font-family: "JetBrains Mono", monospace;',
        "    }",
        "    .metrics-grid {",
        "      display: grid; grid-template-columns: repeat(4, auto);",
        "      gap: 8px; padding: 8px 12px;",
        "    }",
        "    .metric-pill {",
        "      display: flex; flex-direction: column; padding: 5px 10px;",
        "      border-radius: 8px; background: rgba(255, 255, 255, 0.03);",
        "      border: 1px solid rgba(255, 255, 255, 0.06);",
        "    }",
        "    .metric-label {",
        "      font-size: 0.65rem; color: var(--text-muted);",
        "      text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600;",
        "    }",
        "    .metric-value {",
        "      font-size: 1.0rem; font-weight: 700;",
        '      font-family: "JetBrains Mono", monospace; color: #f1f5f9;',
        "    }",
        "    .signals-monitor {",
        "      display: flex; gap: 14px; padding: 6px 14px; align-items: center;",
        "      background: rgba(15, 23, 42, 0.85);",
        "      border: 1px solid rgba(255, 255, 255, 0.12);",
        "      border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);",
        "    }",
        "    .sig-approach {",
        "      display: flex; flex-direction: column; gap: 4px; align-items: center;",
        "    }",
        "    .sig-title {",
        "      font-size: 0.65rem; font-weight: 800; letter-spacing: 0.06em;",
        "      color: #94a3b8; text-transform: uppercase;",
        "    }",
        "    .sig-box {",
        "      display: flex; align-items: center; gap: 6px; background: #09090b;",
        "      padding: 5px 10px; border-radius: 999px; border: 1px solid #27272a;",
        "    }",
        "    .sig-bulb {",
        "      width: 14px; height: 14px; border-radius: 50%; opacity: 0.18;",
        "      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);",
        "    }",
        "    .sig-bulb.red { background: #ff0033; }",
        "    .sig-bulb.yellow { background: #ffaa00; }",
        "    .sig-bulb.green { background: #00ff66; }",
        "    .sig-bulb.red.active {",
        "      opacity: 1; transform: scale(1.22);",
        "      box-shadow: 0 0 16px #ff0033, 0 0 30px rgba(255, 0, 51, 0.7);",
        "    }",
        "    .sig-bulb.yellow.active {",
        "      opacity: 1; transform: scale(1.22);",
        "      box-shadow: 0 0 16px #ffaa00, 0 0 30px rgba(255, 170, 0, 0.7);",
        "    }",
        "    .sig-bulb.green.active {",
        "      opacity: 1; transform: scale(1.22);",
        "      box-shadow: 0 0 16px #00ff66, 0 0 30px rgba(0, 255, 102, 0.7);",
        "    }",
        "    .sig-badge {",
        "      font-size: 0.68rem; font-weight: 800;",
        '      font-family: "JetBrains Mono", monospace;',
        "      padding: 2px 7px; border-radius: 6px; letter-spacing: 0.04em;",
        "    }",
        "    .badge-red {",
        "      color: #f87171; background: rgba(239, 68, 68, 0.18);",
        "      border: 1px solid rgba(239, 68, 68, 0.45);",
        "    }",
        "    .badge-yellow {",
        "      color: #fbbf24; background: rgba(245, 158, 11, 0.18);",
        "      border: 1px solid rgba(245, 158, 11, 0.45);",
        "    }",
        "    .badge-green {",
        "      color: #4ade80; background: rgba(34, 197, 94, 0.18);",
        "      border: 1px solid rgba(34, 197, 94, 0.45);",
        "    }",
        "    .sig-divider {",
        "      width: 1px; height: 38px; background: rgba(255, 255, 255, 0.1);",
        "    }",
        "    .top-right-deck {",
        "      display: flex; flex-direction: column; gap: 10px;",
        "      align-items: flex-end;",
        "    }",
        "    .cam-modes, .lighting-modes {",
        "      display: flex; gap: 5px; padding: 5px;",
        "    }",
        "    .cam-btn, .light-btn {",
        "      background: transparent; border: 1px solid transparent;",
        "      color: var(--text-muted); padding: 5px 10px; border-radius: 8px;",
        "      font-size: 0.78rem; font-weight: 600; cursor: pointer;",
        "      transition: all 0.2s ease;",
        "    }",
        "    .cam-btn:hover, .light-btn:hover {",
        "      background: rgba(255, 255, 255, 0.08); color: var(--text-main);",
        "    }",
        "    .cam-btn.active {",
        "      background: rgba(56, 189, 248, 0.2);",
        "      border-color: rgba(56, 189, 248, 0.4); color: #38bdf8;",
        "    }",
        "    .light-btn.active {",
        "      background: rgba(245, 158, 11, 0.2);",
        "      border-color: rgba(245, 158, 11, 0.4); color: #fbbf24;",
        "    }",
        "    .inspector-card {",
        "      position: absolute; left: 18px; bottom: 120px; width: 280px;",
        "      padding: 14px; display: none; flex-direction: column; gap: 8px;",
        "    }",
        "    .inspector-header {",
        "      display: flex; justify-content: space-between; align-items: center;",
        "    }",
        "    .inspector-title {",
        "      font-size: 0.92rem; font-weight: 700;",
        '      font-family: "JetBrains Mono", monospace; color: #38bdf8;',
        "    }",
        "    .inspector-close {",
        "      background: none; border: none; color: var(--text-muted);",
        "      font-size: 1.1rem; cursor: pointer; padding: 2px;",
        "    }",
        "    .inspector-row {",
        "      display: flex; justify-content: space-between;",
        "      font-size: 0.76rem; padding: 2px 0;",
        "      border-bottom: 1px solid rgba(255, 255, 255, 0.04);",
        "    }",
        "    .inspector-key { color: var(--text-muted); }",
        "    .inspector-val {",
        "      font-weight: 600;",
        '      font-family: "JetBrains Mono", monospace;',
        "    }",
        "    .inspector-btn {",
        "      margin-top: 6px; background: linear-gradient(135deg, #2563eb, #3b82f6);",
        "      border: none; color: white; padding: 6px 10px; border-radius: 8px;",
        "      font-size: 0.75rem; font-weight: 700; cursor: pointer;",
        "    }",
        "    .bottom-control-deck {",
        "      display: flex; flex-direction: column; gap: 8px;",
        "      width: 100%; max-width: 900px; margin: 0 auto; padding: 12px 18px;",
        "    }",
        "    .scrubber-row { display: flex; align-items: center; gap: 10px; }",
        "    .timeline-slider {",
        "      flex: 1; -webkit-appearance: none; height: 6px;",
        "      border-radius: 3px; background: rgba(255, 255, 255, 0.15);",
        "      outline: none; cursor: pointer;",
        "    }",
        "    .timeline-slider::-webkit-slider-thumb {",
        "      -webkit-appearance: none; width: 15px; height: 15px;",
        "      border-radius: 50%; background: #38bdf8; cursor: pointer;",
        "      box-shadow: 0 0 10px rgba(56, 189, 248, 0.8);",
        "    }",
        "    .time-badge {",
        '      font-family: "JetBrains Mono", monospace;',
        "      font-size: 0.82rem; font-weight: 700; min-width: 110px;",
        "      text-align: right;",
        "    }",
        "    .playback-row {",
        "      display: flex; justify-content: space-between; align-items: center;",
        "    }",
        "    .play-controls { display: flex; align-items: center; gap: 6px; }",
        "    .btn-ctrl {",
        "      background: rgba(255, 255, 255, 0.08);",
        "      border: 1px solid rgba(255, 255, 255, 0.1);",
        "      color: var(--text-main); padding: 6px 12px; border-radius: 8px;",
        "      font-size: 0.8rem; font-weight: 700; cursor: pointer;",
        "    }",
        "    .btn-play {",
        "      background: #38bdf8; color: #030712; border-color: #38bdf8;",
        "      padding: 6px 16px;",
        "    }",
        "    .speed-pills {",
        "      display: flex; gap: 4px; background: rgba(255, 255, 255, 0.04);",
        "      padding: 3px; border-radius: 8px;",
        "    }",
        "    .speed-btn {",
        "      background: transparent; border: none; color: var(--text-muted);",
        "      padding: 3px 7px; border-radius: 6px; font-size: 0.72rem;",
        '      font-weight: 700; cursor: pointer; font-family: "JetBrains Mono";',
        "    }",
        "    .speed-btn.active {",
        "      background: rgba(56, 189, 248, 0.2); color: #38bdf8;",
        "    }",
        "    .phase-badge {",
        "      display: flex; align-items: center; gap: 8px; padding: 4px 10px;",
        "      border-radius: 8px; background: rgba(16, 185, 129, 0.15);",
        "      border: 1px solid rgba(16, 185, 129, 0.3);",
        '      font-family: "JetBrains Mono", monospace; font-size: 0.78rem;',
        "      font-weight: 700; color: #34d399;",
        "    }",
        "    .signal-led {",
        "      width: 9px; height: 9px; border-radius: 50%;",
        "      background: #10b981; box-shadow: 0 0 10px #10b981;",
        "    }",
        "  </style>",
        "</head>",
        "<body>",
        '  <canvas id="webgl-canvas"></canvas>',
        '  <div class="hud-layer">',
        '    <div class="header-bar">',
        '      <div class="glass-card brand-card interactive">',
        '        <div class="brand-title">',
        "          JUNCTION-SIM",
        '          <span class="brand-badge">Euro 3D Pro</span>',
        "        </div>",
        (
            f'        <div class="brand-subtitle">{scenario_name} • '
            f"{controller_name} • seed {seed}</div>"
        ),
        "      </div>",
        '      <div class="glass-card metrics-grid interactive">',
        '        <div class="metric-pill">',
        '          <span class="metric-label">Active 3D</span>',
        '          <span class="metric-value" id="hud-active-veh">0</span>',
        "        </div>",
        '        <div class="metric-pill">',
        '          <span class="metric-label">Served</span>',
        '          <span class="metric-value" id="hud-served-veh">0</span>',
        "        </div>",
        '        <div class="metric-pill">',
        '          <span class="metric-label">Avg Delay</span>',
        '          <span class="metric-value" id="hud-avg-delay">0.0 s</span>',
        "        </div>",
        '        <div class="metric-pill">',
        '          <span class="metric-label">Max Queue</span>',
        '          <span class="metric-value" id="hud-max-queue">0</span>',
        "        </div>",
        "      </div>",
        '      <div class="glass-card signals-monitor interactive">',
        '        <div class="sig-approach">',
        '          <span class="sig-title">North-South (Kuzey-Güney)</span>',
        '          <div class="sig-box">',
        '            <span class="sig-bulb red" id="hud-ns-red"></span>',
        '            <span class="sig-bulb yellow" id="hud-ns-yellow"></span>',
        '            <span class="sig-bulb green" id="hud-ns-green"></span>',
        "          </div>",
        (
            '          <span class="sig-badge badge-green" '
            'id="hud-ns-badge">GO (GREEN)</span>'
        ),
        "        </div>",
        '        <div class="sig-divider"></div>',
        '        <div class="sig-approach">',
        '          <span class="sig-title">East-West (Doğu-Batı)</span>',
        '          <div class="sig-box">',
        '            <span class="sig-bulb red" id="hud-ew-red"></span>',
        '            <span class="sig-bulb yellow" id="hud-ew-yellow"></span>',
        '            <span class="sig-bulb green" id="hud-ew-green"></span>',
        "          </div>",
        (
            '          <span class="sig-badge badge-red" '
            'id="hud-ew-badge">STOP (RED)</span>'
        ),
        "        </div>",
        "      </div>",
        '      <div class="top-right-deck interactive">',
        '        <div class="glass-card cam-modes">',
        (
            '          <button class="cam-btn active" data-cam="cinematic">'
            "Junction</button>"
        ),
        '          <button class="cam-btn" data-cam="orbit">Orbit</button>',
        '          <button class="cam-btn" data-cam="drone">Drone</button>',
        '          <button class="cam-btn" data-cam="chase">Chase</button>',
        '          <button class="cam-btn" data-cam="cockpit">Cockpit</button>',
        "        </div>",
        '        <div class="glass-card lighting-modes">',
        ('          <button class="light-btn active" data-light="day">Sunny</button>'),
        '          <button class="light-btn" data-light="sunset">Sunset</button>',
        '          <button class="light-btn" data-light="night">Night</button>',
        "        </div>",
        "      </div>",
        "    </div>",
        '    <div class="glass-card inspector-card interactive" id="inspector-card">',
        '      <div class="inspector-header">',
        '        <span class="inspector-title" id="insp-id">veh_0</span>',
        '        <button class="inspector-close" id="insp-close">✕</button>',
        "      </div>",
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Type</span>'
            '<span class="inspector-val" id="insp-type">Semi Truck</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Speed</span>'
            '<span class="inspector-val" id="insp-speed">0.0 km/h</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Acceleration</span>'
            '<span class="inspector-val" id="insp-acc">0.0 m/s²</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Heading</span>'
            '<span class="inspector-val" id="insp-heading">0°</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Turn Signal</span>'
            '<span class="inspector-val" id="insp-signal">None</span></div>'
        ),
        (
            '      <button class="inspector-btn" id="insp-follow-btn">'
            "Follow in Chase Cam</button>"
        ),
        "    </div>",
        '    <div class="glass-card bottom-control-deck interactive">',
        '      <div class="scrubber-row">',
        (
            '        <input type="range" class="timeline-slider" id="time-slider" '
            'min="0" max="100" value="0" step="0.1">'
        ),
        '        <div class="time-badge" id="time-display">00:00.0 / 00:00.0</div>',
        "      </div>",
        '      <div class="playback-row">',
        '        <div class="play-controls">',
        '          <button class="btn-ctrl btn-play" id="btn-play">Play</button>',
        '          <button class="btn-ctrl" id="btn-reset">Reset</button>',
        '          <button class="btn-ctrl" id="btn-loop">Loop: On</button>',
        "        </div>",
        '        <div class="phase-badge">',
        '          <div class="signal-led" id="phase-led"></div>',
        '          <span id="phase-label">Phase: P1</span>',
        "        </div>",
        '        <div class="speed-pills">',
        '          <button class="speed-btn" data-speed="0.25">0.25x</button>',
        '          <button class="speed-btn" data-speed="0.5">0.5x</button>',
        '          <button class="speed-btn active" data-speed="1.0">1x</button>',
        '          <button class="speed-btn" data-speed="2.0">2x</button>',
        '          <button class="speed-btn" data-speed="5.0">5x</button>',
        "        </div>",
        "      </div>",
        "    </div>",
        "  </div>",
        "  <script>",
        f"    const SIM_DATA = {json_payload};",
        """
    const canvas = document.getElementById('webgl-canvas');
    const renderer = new THREE.WebGLRenderer({
      canvas, antialias: true, powerPreference: 'high-performance'
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputEncoding = THREE.sRGBEncoding;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x60a5fa);
    scene.fog = new THREE.FogExp2(0x93c5fd, 0.0025);

    const camera = new THREE.PerspectiveCamera(
      42, window.innerWidth / window.innerHeight, 0.1, 1000
    );
    camera.position.set(0, 16, 48);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.03;
    controls.target.set(0, 2.5, -2);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x475569, 0.75);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 2.2);
    sunLight.position.set(65, 95, 60);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 280;
    sunLight.shadow.camera.left = -80;
    sunLight.shadow.camera.right = 80;
    sunLight.shadow.camera.top = 80;
    sunLight.shadow.camera.bottom = -80;
    sunLight.shadow.bias = -0.0004;
    scene.add(sunLight);

    const signalMeshes = {};
    const stopBars = {};

    function createSignboardTexture() {
      const cv = document.createElement('canvas');
      cv.width = 512;
      cv.height = 256;
      const ctx = cv.getContext('2d');
      ctx.fillStyle = '#facc15';
      ctx.fillRect(0, 0, 512, 256);
      ctx.lineWidth = 14;
      ctx.strokeStyle = '#0f172a';
      ctx.strokeRect(7, 7, 498, 242);
      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 36px sans-serif';
      ctx.fillText('Rostock 105 km', 30, 65);
      ctx.fillText('Hamburg 65 km', 30, 115);
      ctx.beginPath();
      ctx.arc(380, 128, 50, 0, Math.PI * 2);
      ctx.lineWidth = 12;
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(380, 78); ctx.lineTo(380, 30);
      ctx.moveTo(430, 128); ctx.lineTo(475, 128);
      ctx.moveTo(380, 178); ctx.lineTo(380, 226);
      ctx.moveTo(330, 128); ctx.lineTo(285, 128);
      ctx.stroke();
      return new THREE.CanvasTexture(cv);
    }

    function createWarningSignTexture(isDanger) {
      const cv = document.createElement('canvas');
      cv.width = 256;
      cv.height = 256;
      const ctx = cv.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, 256, 256);
      ctx.fillStyle = '#dc2626';
      ctx.beginPath();
      ctx.moveTo(128, 16);
      ctx.lineTo(240, 230);
      ctx.lineTo(16, 230);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.moveTo(128, 52);
      ctx.lineTo(214, 214);
      ctx.lineTo(42, 214);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 100px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(isDanger ? '!' : 'A', 128, 150);
      return new THREE.CanvasTexture(cv);
    }

    function buildEnvironment() {
      const terrainGeo = new THREE.PlaneGeometry(500, 500);
      const terrainMat = new THREE.MeshStandardMaterial({
        color: 0x15803d, roughness: 0.9, metalness: 0.05
      });
      const terrain = new THREE.Mesh(terrainGeo, terrainMat);
      terrain.rotation.x = -Math.PI / 2;
      terrain.position.y = -0.08;
      terrain.receiveShadow = true;
      scene.add(terrain);

      const asphaltMat = new THREE.MeshStandardMaterial({
        color: 0x1f242d, roughness: 0.78, metalness: 0.12
      });
      const redBikeMat = new THREE.MeshStandardMaterial({
        color: 0xb91c1c, roughness: 0.7, metalness: 0.05
      });

      const roadNS = new THREE.Mesh(new THREE.PlaneGeometry(17, 340), asphaltMat);
      roadNS.rotation.x = -Math.PI / 2;
      roadNS.receiveShadow = true;
      scene.add(roadNS);

      const roadEW = new THREE.Mesh(new THREE.PlaneGeometry(340, 17), asphaltMat);
      roadEW.rotation.x = -Math.PI / 2;
      roadEW.receiveShadow = true;
      scene.add(roadEW);

      const bikePlanes = [
        { x: 9.6, z: 0, w: 2.2, h: 340, rotZ: 0 },
        { x: -9.6, z: 0, w: 2.2, h: 340, rotZ: 0 },
        { x: 0, z: 9.6, w: 340, h: 2.2, rotZ: 0 },
        { x: 0, z: -9.6, w: 340, h: 2.2, rotZ: 0 }
      ];
      bikePlanes.forEach(bp => {
        const bm = new THREE.Mesh(new THREE.PlaneGeometry(bp.w, bp.h), redBikeMat);
        bm.rotation.x = -Math.PI / 2;
        bm.position.set(bp.x, 0.01, bp.z);
        bm.receiveShadow = true;
        scene.add(bm);
      });

      const bikeCrossingMat = new THREE.MeshStandardMaterial({
        color: 0x991b1b, roughness: 0.65
      });
      const bikeCrossings = [
        { x: 0, z: 10.5, w: 17, h: 1.8 },
        { x: 0, z: -10.5, w: 17, h: 1.8 },
        { x: 10.5, z: 0, w: 1.8, h: 17 },
        { x: -10.5, z: 0, w: 1.8, h: 17 }
      ];
      bikeCrossings.forEach(bc => {
        const bcm = new THREE.Mesh(
          new THREE.PlaneGeometry(bc.w, bc.h), bikeCrossingMat
        );
        bcm.rotation.x = -Math.PI / 2;
        bcm.position.set(bc.x, 0.02, bc.z);
        scene.add(bcm);
      });

      const sidewalkMat = new THREE.MeshStandardMaterial({
        color: 0x94a3b8, roughness: 0.75
      });
      const corners = [
        { x: 42, z: 42, w: 62, h: 62 },
        { x: -42, z: 42, w: 62, h: 62 },
        { x: 42, z: -42, w: 62, h: 62 },
        { x: -42, z: -42, w: 62, h: 62 }
      ];
      corners.forEach(c => {
        const sw = new THREE.Mesh(
          new THREE.BoxGeometry(c.w, 0.35, c.h), sidewalkMat
        );
        sw.position.set(
          c.x > 0 ? c.x + 9.5 : c.x - 9.5,
          0.16,
          c.z > 0 ? c.z + 9.5 : c.z - 9.5
        );
        sw.receiveShadow = true;
        scene.add(sw);
      });

      const whiteLineMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const yellowLineMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });

      function addDashedLine(x1, z1, x2, z2, mat, dashes = 28) {
        for (let i = 0; i < dashes; i++) {
          const t1 = i / dashes;
          const t2 = (i + 0.55) / dashes;
          const px = x1 + (x2 - x1) * ((t1 + t2) / 2);
          const pz = z1 + (z2 - z1) * ((t1 + t2) / 2);
          const len = Math.hypot(
            (x2 - x1) * 0.55 / dashes, (z2 - z1) * 0.55 / dashes
          );
          const rot = Math.atan2(x2 - x1, z2 - z1);
          const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.26, len), mat);
          dash.rotation.x = -Math.PI / 2;
          dash.rotation.z = -rot;
          dash.position.set(px, 0.035, pz);
          scene.add(dash);
        }
      }

      function addStopLine(id, x, z, width, isHorizontal) {
        const line = new THREE.Mesh(
          new THREE.PlaneGeometry(width, 0.75), whiteLineMat
        );
        line.rotation.x = -Math.PI / 2;
        if (!isHorizontal) line.rotation.z = Math.PI / 2;
        line.position.set(x, 0.035, z);
        scene.add(line);

        const glowLine = new THREE.Mesh(
          new THREE.PlaneGeometry(width, 0.5),
          new THREE.MeshBasicMaterial({ color: 0xef4444 })
        );
        glowLine.rotation.x = -Math.PI / 2;
        if (!isHorizontal) glowLine.rotation.z = Math.PI / 2;
        const offsetZ = isHorizontal ? (z > 0 ? -0.55 : 0.55) : 0;
        const offsetX = !isHorizontal ? (x > 0 ? -0.55 : 0.55) : 0;
        glowLine.position.set(x + offsetX, 0.04, z + offsetZ);
        scene.add(glowLine);
        stopBars[id] = glowLine;
      }

      function addZebraCrossing(centerX, centerZ, isHorizontal) {
        const stripes = 9;
        for (let i = 0; i < stripes; i++) {
          const offset = (i - (stripes - 1) / 2) * 1.6;
          const mesh = new THREE.Mesh(
            new THREE.PlaneGeometry(0.85, 4.4), whiteLineMat
          );
          mesh.rotation.x = -Math.PI / 2;
          if (isHorizontal) {
            mesh.rotation.z = Math.PI / 2;
            mesh.position.set(centerX + offset, 0.035, centerZ);
          } else {
            mesh.position.set(centerX, 0.035, centerZ + offset);
          }
          scene.add(mesh);
        }
      }

      addStopLine('north', 3.8, 13, 7.5, true);
      addStopLine('south', -3.8, -13, 7.5, true);
      addStopLine('east', 13, -3.8, 7.5, false);
      addStopLine('west', -13, 3.8, 7.5, false);

      addZebraCrossing(0, 16.5, true);
      addZebraCrossing(0, -16.5, true);
      addZebraCrossing(16.5, 0, false);
      addZebraCrossing(-16.5, 0, false);

      addDashedLine(0, 17, 0, 160, yellowLineMat, 28);
      addDashedLine(0, -17, 0, -160, yellowLineMat, 28);
      addDashedLine(17, 0, 160, 0, yellowLineMat, 28);
      addDashedLine(-17, 0, -160, 0, yellowLineMat, 28);

      addDashedLine(3.8, 17, 3.8, 160, whiteLineMat, 28);
      addDashedLine(-3.8, 17, -3.8, 160, whiteLineMat, 28);
      addDashedLine(3.8, -17, 3.8, -160, whiteLineMat, 28);
      addDashedLine(-3.8, -17, -3.8, -160, whiteLineMat, 28);
      addDashedLine(17, 3.8, 160, 3.8, whiteLineMat, 28);
      addDashedLine(17, -3.8, 160, -3.8, whiteLineMat, 28);
      addDashedLine(-17, 3.8, -160, 3.8, whiteLineMat, 28);
      addDashedLine(-17, -3.8, -160, -3.8, whiteLineMat, 28);

      buildBuildingsAndScenery();
      buildConstructionSite();
      buildRoadSigns();
      buildCurvedGantrySignals();
    }

    function buildBuildingsAndScenery() {
      const greenGlassMat = new THREE.MeshStandardMaterial({
        color: 0x064e3b, roughness: 0.15, metalness: 0.8
      });
      const commercial = new THREE.Mesh(
        new THREE.CylinderGeometry(28, 28, 38, 24, 1, false, 0, Math.PI * 0.75),
        greenGlassMat
      );
      commercial.position.set(48, 19, -46);
      commercial.rotation.y = Math.PI * 0.9;
      commercial.castShadow = true;
      commercial.receiveShadow = true;
      scene.add(commercial);

      const bldgDefs = [
        { x: -52, z: 52, w: 38, d: 36, h: 24, col: 0xb45309 },
        { x: 55, z: 52, w: 36, d: 32, h: 42, col: 0x1e293b }
      ];
      bldgDefs.forEach(b => {
        const mat = new THREE.MeshStandardMaterial({
          color: b.col, roughness: 0.7
        });
        const mesh = new THREE.Mesh(new THREE.BoxGeometry(b.w, b.h, b.d), mat);
        mesh.position.set(b.x, b.h / 2, b.z);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        scene.add(mesh);
      });

      const treeMat1 = new THREE.MeshStandardMaterial({
        color: 0x15803d, roughness: 0.65
      });
      const treeMat2 = new THREE.MeshStandardMaterial({
        color: 0x166534, roughness: 0.7
      });
      const treeMat3 = new THREE.MeshStandardMaterial({
        color: 0x4d7c0f, roughness: 0.65
      });
      const trunkMat = new THREE.MeshStandardMaterial({
        color: 0x451a03, roughness: 0.9
      });

      for (let i = 0; i < 36; i++) {
        const angle = (i / 36) * Math.PI * 2;
        const rad = 30 + (i % 4) * 7;
        const tx = Math.cos(angle) * rad;
        const tz = Math.sin(angle) * rad;
        if (Math.abs(tx) < 13 || Math.abs(tz) < 13) continue;

        const trunk = new THREE.Mesh(
          new THREE.CylinderGeometry(0.24, 0.36, 3.6, 8), trunkMat
        );
        trunk.position.set(tx, 1.8, tz);
        trunk.castShadow = true;
        scene.add(trunk);

        const leafMat = (i % 3 === 0) ? treeMat1 : (
          (i % 3 === 1) ? treeMat2 : treeMat3
        );
        const crown1 = new THREE.Mesh(
          new THREE.DodecahedronGeometry(2.5, 1), leafMat
        );
        crown1.position.set(tx, 4.6, tz);
        crown1.castShadow = true;
        scene.add(crown1);

        const crown2 = new THREE.Mesh(
          new THREE.DodecahedronGeometry(1.9, 1), leafMat
        );
        crown2.position.set(tx + 0.5, 6.2, tz + 0.4);
        crown2.castShadow = true;
        scene.add(crown2);
      }
    }

    function buildConstructionSite() {
      const siteGroup = new THREE.Group();
      siteGroup.position.set(-26, 0, -24);

      const cabMatYellow = new THREE.MeshStandardMaterial({
        color: 0xeab308, roughness: 0.4
      });
      const cabMatBlue = new THREE.MeshStandardMaterial({
        color: 0x0284c7, roughness: 0.4
      });
      const frameMat = new THREE.MeshStandardMaterial({
        color: 0xf8fafc, roughness: 0.3
      });

      const cab1 = new THREE.Mesh(
        new THREE.BoxGeometry(7.2, 3.1, 3.1), cabMatYellow
      );
      cab1.position.set(0, 1.55, 0);
      cab1.castShadow = true;
      siteGroup.add(cab1);

      const cab2 = new THREE.Mesh(
        new THREE.BoxGeometry(7.2, 3.1, 3.1), cabMatBlue
      );
      cab2.position.set(0, 4.65, 0);
      cab2.castShadow = true;
      siteGroup.add(cab2);

      const winGeo = new THREE.BoxGeometry(1.6, 1.2, 0.1);
      const win1 = new THREE.Mesh(winGeo, frameMat);
      win1.position.set(-1.8, 1.6, 1.6);
      siteGroup.add(win1);

      const win2 = new THREE.Mesh(winGeo, frameMat);
      win2.position.set(1.8, 1.6, 1.6);
      siteGroup.add(win2);

      const win3 = new THREE.Mesh(winGeo, frameMat);
      win3.position.set(0, 4.7, 1.6);
      siteGroup.add(win3);

      const craneGroup = new THREE.Group();
      craneGroup.position.set(-56, 0, -32);
      const craneMat = new THREE.MeshStandardMaterial({
        color: 0xf59e0b, metalness: 0.6, roughness: 0.35
      });

      const mast = new THREE.Mesh(new THREE.BoxGeometry(1.8, 56, 1.8), craneMat);
      mast.position.y = 28;
      craneGroup.add(mast);

      const jib = new THREE.Mesh(new THREE.BoxGeometry(46, 1.4, 1.4), craneMat);
      jib.position.set(14, 54, 0);
      craneGroup.add(jib);

      const counterJib = new THREE.Mesh(
        new THREE.BoxGeometry(16, 1.4, 1.4), craneMat
      );
      counterJib.position.set(-10, 54, 0);
      craneGroup.add(counterJib);

      const weight = new THREE.Mesh(
        new THREE.BoxGeometry(5, 3.5, 2.2),
        new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.9 })
      );
      weight.position.set(-14, 53, 0);
      craneGroup.add(weight);

      const hookCable = new THREE.Mesh(
        new THREE.CylinderGeometry(0.04, 0.04, 22, 6),
        new THREE.MeshBasicMaterial({ color: 0x0f172a })
      );
      hookCable.position.set(16, 42, 0);
      craneGroup.add(hookCable);

      const hookBlock = new THREE.Mesh(
        new THREE.BoxGeometry(1.2, 1.2, 0.8),
        new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.4 })
      );
      hookBlock.position.set(16, 31, 0);
      craneGroup.add(hookBlock);

      scene.add(siteGroup);
      scene.add(craneGroup);
    }

    function buildRoadSigns() {
      const steelMat = new THREE.MeshStandardMaterial({
        color: 0x94a3b8, metalness: 0.8, roughness: 0.3
      });

      const boardTex = createSignboardTexture();
      const boardMat = new THREE.MeshStandardMaterial({
        map: boardTex, roughness: 0.3
      });
      const signGroup = new THREE.Group();
      signGroup.position.set(15, 0, 24);

      const post = new THREE.Mesh(
        new THREE.CylinderGeometry(0.18, 0.22, 8.5, 12), steelMat
      );
      post.position.set(0, 4.25, 0);
      signGroup.add(post);

      const boardMesh = new THREE.Mesh(
        new THREE.BoxGeometry(7.2, 3.6, 0.18), boardMat
      );
      boardMesh.position.set(0, 7.2, 0.2);
      signGroup.add(boardMesh);
      scene.add(signGroup);

      const warnTexDanger = createWarningSignTexture(true);
      const warnTexWork = createWarningSignTexture(false);
      const dangerMat = new THREE.MeshStandardMaterial({
        map: warnTexDanger, roughness: 0.4
      });
      const workMat = new THREE.MeshStandardMaterial({
        map: warnTexWork, roughness: 0.4
      });

      const wSign1 = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 2.4), dangerMat);
      wSign1.position.set(12.5, 2.6, 18);
      wSign1.rotation.y = -Math.PI / 6;
      scene.add(wSign1);

      const wSign2 = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 2.4), workMat);
      wSign2.position.set(-13, 2.6, 18);
      wSign2.rotation.y = Math.PI / 6;
      scene.add(wSign2);
    }

    function buildCurvedGantrySignals() {
      const steelMat = new THREE.MeshStandardMaterial({
        color: 0x94a3b8, metalness: 0.75, roughness: 0.35
      });
      const housingMat = new THREE.MeshStandardMaterial({
        color: 0x09090b, roughness: 0.85
      });
      const borderMat = new THREE.MeshBasicMaterial({
        color: 0xfacc15
      });

      function createHead() {
        const hGroup = new THREE.Group();

        const backplate = new THREE.Mesh(
          new THREE.BoxGeometry(1.2, 2.9, 0.08), borderMat
        );
        backplate.position.set(0, 0, -0.22);
        hGroup.add(backplate);

        const box = new THREE.Mesh(
          new THREE.BoxGeometry(0.9, 2.6, 0.45), housingMat
        );
        box.castShadow = true;
        hGroup.add(box);

        const visorGeo = new THREE.CylinderGeometry(
          0.36, 0.36, 0.35, 12, 1, true, 0, Math.PI
        );
        const visorMat = new THREE.MeshStandardMaterial({
          color: 0x09090b, roughness: 0.85, side: THREE.DoubleSide
        });

        const vR = new THREE.Mesh(visorGeo, visorMat);
        vR.rotation.x = Math.PI / 2;
        vR.position.set(0, 0.95, 0.28);
        hGroup.add(vR);

        const vY = new THREE.Mesh(visorGeo, visorMat);
        vY.rotation.x = Math.PI / 2;
        vY.position.set(0, 0.18, 0.28);
        hGroup.add(vY);

        const vG = new THREE.Mesh(visorGeo, visorMat);
        vG.rotation.x = Math.PI / 2;
        vG.position.set(0, -0.58, 0.28);
        hGroup.add(vG);

        const lensGeo = new THREE.SphereGeometry(0.28, 16, 16);
        const rMesh = new THREE.Mesh(
          lensGeo, new THREE.MeshBasicMaterial({ color: 0xff0033 })
        );
        rMesh.position.set(0, 0.75, 0.22);
        hGroup.add(rMesh);

        const yMesh = new THREE.Mesh(
          lensGeo, new THREE.MeshBasicMaterial({ color: 0x18181b })
        );
        yMesh.position.set(0, 0, 0.22);
        hGroup.add(yMesh);

        const gMesh = new THREE.Mesh(
          lensGeo, new THREE.MeshBasicMaterial({ color: 0x18181b })
        );
        gMesh.position.set(0, -0.75, 0.22);
        hGroup.add(gMesh);

        return { group: hGroup, red: rMesh, yellow: yMesh, green: gMesh };
      }

      const configs = [
        { id: 'north', px: 9.6, pz: 13.5, hx: 2.5, hz: 13.5, rot: 0 },
        { id: 'south', px: -9.6, pz: -13.5, hx: -2.5, hz: -13.5, rot: Math.PI },
        { id: 'east', px: 13.5, pz: -9.6, hx: 13.5, hz: -2.5, rot: Math.PI / 2 },
        { id: 'west', px: -13.5, pz: 9.6, hx: -13.5, hz: 2.5, rot: -Math.PI / 2 }
      ];

      configs.forEach(cfg => {
        const post = new THREE.Mesh(
          new THREE.CylinderGeometry(0.2, 0.26, 7.5, 12), steelMat
        );
        post.position.set(cfg.px, 3.75, cfg.pz);
        post.castShadow = true;
        scene.add(post);

        const armLen = 8.5;
        const arm = new THREE.Mesh(
          new THREE.CylinderGeometry(0.14, 0.14, armLen, 12), steelMat
        );
        arm.rotation.z = Math.PI / 2;
        arm.rotation.y = cfg.rot;
        arm.position.set((cfg.px + cfg.hx) / 2, 6.9, (cfg.pz + cfg.hz) / 2);
        scene.add(arm);

        const headOver = createHead();
        headOver.group.position.set(cfg.hx, 6.0, cfg.hz);
        headOver.group.rotation.y = cfg.rot;
        scene.add(headOver.group);

        const headPost = createHead();
        headPost.group.position.set(cfg.px, 3.5, cfg.pz);
        headPost.group.rotation.y = cfg.rot;
        scene.add(headPost.group);

        const pLight = new THREE.PointLight(0x00ff66, 3.0, 32);
        pLight.position.set(cfg.hx, 6.0, cfg.hz);
        scene.add(pLight);

        signalMeshes[cfg.id] = {
          heads: [headOver, headPost],
          light: pLight,
          stopBar: stopBars[cfg.id]
        };
      });
    }

    const vehicleObjects = new Map();

    function createVehicleMesh(type, colorHex) {
      const group = new THREE.Group();

      let len = 4.4, wid = 1.9, hei = 1.4;
      const isSemi = (type === 'semi_truck');
      const isBox = (type === 'box_truck');
      const isBus = (type === 'bus');

      if (isSemi) { len = 14.8; wid = 2.5; hei = 3.6; }
      else if (isBox) { len = 7.8; wid = 2.3; hei = 2.9; }
      else if (isBus) { len = 11.2; wid = 2.45; hei = 2.8; }
      else if (type === 'suv') { len = 4.8; wid = 2.0; hei = 1.65; }
      else if (type === 'van') { len = 5.6; wid = 2.1; hei = 2.1; }
      else if (type === 'hatchback') { len = 3.9; wid = 1.8; hei = 1.35; }

      const bodyMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorHex),
        metalness: 0.65,
        roughness: 0.25
      });
      const glassMat = new THREE.MeshStandardMaterial({
        color: 0x0f172a, roughness: 0.1, metalness: 0.2
      });
      const trailerMat = new THREE.MeshStandardMaterial({
        color: 0xf1f5f9, metalness: 0.3, roughness: 0.5
      });
      const rubberMat = new THREE.MeshStandardMaterial({
        color: 0x111827, roughness: 0.95
      });
      const chromeMat = new THREE.MeshStandardMaterial({
        color: 0xe2e8f0, metalness: 0.9, roughness: 0.1
      });

      if (isSemi) {
        const cabLen = 4.2;
        const cab = new THREE.Mesh(
          new THREE.BoxGeometry(wid, hei * 0.75, cabLen), bodyMat
        );
        cab.position.set(0, hei * 0.45, len * 0.32);
        cab.castShadow = true;
        group.add(cab);

        const grille = new THREE.Mesh(
          new THREE.BoxGeometry(wid * 0.8, hei * 0.32, 0.15), chromeMat
        );
        grille.position.set(0, hei * 0.3, len * 0.32 + cabLen * 0.51);
        group.add(grille);

        const cabGlass = new THREE.Mesh(
          new THREE.BoxGeometry(wid * 0.94, hei * 0.35, 1.8), glassMat
        );
        cabGlass.position.set(0, hei * 0.68, len * 0.32 + 1.1);
        cabGlass.castShadow = true;
        group.add(cabGlass);

        const trailerLen = 10.2;
        const trailer = new THREE.Mesh(
          new THREE.BoxGeometry(wid * 1.02, hei * 0.85, trailerLen), trailerMat
        );
        trailer.position.set(0, hei * 0.55, -len * 0.15);
        trailer.castShadow = true;
        group.add(trailer);

        const skirtMat = new THREE.MeshStandardMaterial({
          color: 0x64748b, roughness: 0.5
        });
        const skirt = new THREE.Mesh(
          new THREE.BoxGeometry(wid * 0.98, hei * 0.3, trailerLen * 0.55),
          skirtMat
        );
        skirt.position.set(0, hei * 0.25, -len * 0.05);
        group.add(skirt);
      } else {
        const baseMesh = new THREE.Mesh(
          new THREE.BoxGeometry(wid, hei * 0.55, len), bodyMat
        );
        baseMesh.position.y = hei * 0.45;
        baseMesh.castShadow = true;
        group.add(baseMesh);

        const cabinLen = isBus ? len * 0.92 : (
          isBox ? len * 0.35 : len * 0.58
        );
        const cabinMesh = new THREE.Mesh(
          new THREE.BoxGeometry(wid * 0.9, hei * 0.5, cabinLen), glassMat
        );
        cabinMesh.position.y = hei * 0.85;
        cabinMesh.position.z = isBus ? 0 : (isBox ? len * 0.25 : -len * 0.05);
        cabinMesh.castShadow = true;
        group.add(cabinMesh);

        if (isBox) {
          const boxCargo = new THREE.Mesh(
            new THREE.BoxGeometry(wid * 1.02, hei * 0.8, len * 0.6), trailerMat
          );
          boxCargo.position.set(0, hei * 0.6, -len * 0.15);
          boxCargo.castShadow = true;
          group.add(boxCargo);
        }
      }

      const headMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const tailMat = new THREE.MeshBasicMaterial({ color: 0xff0033 });
      const amberMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });

      const hlLeft = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.2, 0.05), headMat
      );
      hlLeft.position.set(-wid * 0.36, hei * 0.42, len * 0.5 + 0.02);
      group.add(hlLeft);

      const hlRight = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.2, 0.05), headMat
      );
      hlRight.position.set(wid * 0.36, hei * 0.42, len * 0.5 + 0.02);
      group.add(hlRight);

      const tlLeft = new THREE.Mesh(
        new THREE.BoxGeometry(0.32, 0.2, 0.05), tailMat
      );
      tlLeft.position.set(-wid * 0.38, hei * 0.42, -len * 0.5 - 0.02);
      group.add(tlLeft);

      const tlRight = new THREE.Mesh(
        new THREE.BoxGeometry(0.32, 0.2, 0.05), tailMat
      );
      tlRight.position.set(wid * 0.38, hei * 0.42, -len * 0.5 - 0.02);
      group.add(tlRight);

      const blLeft = new THREE.Mesh(
        new THREE.BoxGeometry(0.18, 0.14, 0.05), amberMat
      );
      blLeft.position.set(-wid * 0.46, hei * 0.42, len * 0.45);
      blLeft.visible = false;
      group.add(blLeft);

      const blRight = new THREE.Mesh(
        new THREE.BoxGeometry(0.18, 0.14, 0.05), amberMat
      );
      blRight.position.set(wid * 0.46, hei * 0.42, len * 0.45);
      blRight.visible = false;
      group.add(blRight);

      const wheels = [];
      const wheelRad = (isSemi || isBus) ? 0.5 : 0.36;
      const wheelWid = (isSemi || isBus) ? 0.35 : 0.26;
      const wheelGeo = new THREE.CylinderGeometry(
        wheelRad, wheelRad, wheelWid, 16
      );
      wheelGeo.rotateZ(Math.PI / 2);

      const numWheelSets = isSemi ? 5 : 2;
      for (let w = 0; w < numWheelSets; w++) {
        const zPos = isSemi ? (
          len * 0.4 - w * (len * 0.2)
        ) : (w === 0 ? len * 0.32 : -len * 0.32);
        const canSteer = (w === 0);

        [-1, 1].forEach(side => {
          const wPivot = new THREE.Group();
          wPivot.position.set(side * wid * 0.48, wheelRad, zPos);

          const wMesh = new THREE.Mesh(wheelGeo, rubberMat);
          wMesh.castShadow = true;
          wPivot.add(wMesh);
          group.add(wPivot);

          wheels.push({ pivot: wPivot, mesh: wMesh, canSteer });
        });
      }

      return { group, wheels, tlLeft, tlRight, blLeft, blRight, bodyMat };
    }

    const trajectories = SIM_DATA.trajectories || {};
    const steps = SIM_DATA.steps || [];
    const maxDuration = SIM_DATA.metadata.duration || 60.0;

    let currentTime = 0.0;
    let isPlaying = true;
    let playbackSpeed = 1.0;
    let isLooping = true;
    let selectedVehicleId = null;
    let currentCameraMode = 'cinematic';

    buildEnvironment();

    const slider = document.getElementById('time-slider');
    slider.max = maxDuration;
    const timeDisplay = document.getElementById('time-display');
    const btnPlay = document.getElementById('btn-play');
    const btnReset = document.getElementById('btn-reset');
    const btnLoop = document.getElementById('btn-loop');
    const inspector = document.getElementById('inspector-card');
    const inspClose = document.getElementById('insp-close');
    const inspFollowBtn = document.getElementById('insp-follow-btn');

    btnPlay.addEventListener('click', () => {
      isPlaying = !isPlaying;
      btnPlay.textContent = isPlaying ? 'Pause' : 'Play';
      btnPlay.classList.toggle('btn-play', isPlaying);
    });

    btnReset.addEventListener('click', () => {
      currentTime = 0;
      updateSimulation(0);
    });

    btnLoop.addEventListener('click', () => {
      isLooping = !isLooping;
      btnLoop.textContent = 'Loop: ' + (isLooping ? 'On' : 'Off');
    });

    slider.addEventListener('input', (e) => {
      currentTime = parseFloat(e.target.value);
      updateSimulation(currentTime);
    });

    document.querySelectorAll('.speed-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.speed-btn').forEach(b => {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        playbackSpeed = parseFloat(btn.dataset.speed);
      });
    });

    document.querySelectorAll('.cam-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        setCameraMode(btn.dataset.cam);
      });
    });

    function setCameraMode(mode) {
      currentCameraMode = mode;
      document.querySelectorAll('.cam-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.cam === mode);
      });
      if (mode === 'cinematic') {
        controls.enabled = true;
        camera.position.set(0, 16, 48);
        controls.target.set(0, 2.5, -2);
      } else if (mode === 'orbit') {
        controls.enabled = true;
        controls.target.set(0, 0, 0);
      } else if (mode === 'drone') {
        controls.enabled = true;
        camera.position.set(0, 85, 45);
        controls.target.set(0, 0, 0);
      }
    }

    document.querySelectorAll('.light-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.light-btn').forEach(b => {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        setLightingMode(btn.dataset.light);
      });
    });

    function setLightingMode(mode) {
      if (mode === 'day') {
        scene.background = new THREE.Color(0x60a5fa);
        scene.fog.color = new THREE.Color(0x93c5fd);
        sunLight.color.setHex(0xfffaed);
        sunLight.intensity = 2.2;
        hemiLight.intensity = 0.75;
      } else if (mode === 'sunset') {
        scene.background = new THREE.Color(0x31102f);
        scene.fog.color = new THREE.Color(0x31102f);
        sunLight.color.setHex(0xf97316);
        sunLight.intensity = 2.4;
        hemiLight.intensity = 0.45;
      } else if (mode === 'night') {
        scene.background = new THREE.Color(0x020617);
        scene.fog.color = new THREE.Color(0x020617);
        sunLight.color.setHex(0x38bdf8);
        sunLight.intensity = 0.25;
        hemiLight.intensity = 0.18;
      }
    }

    inspClose.addEventListener('click', () => {
      inspector.style.display = 'none';
      selectedVehicleId = null;
    });

    inspFollowBtn.addEventListener('click', () => {
      if (selectedVehicleId) {
        setCameraMode('chase');
      }
    });

    function getInterpolatedState(states, t) {
      if (!states || states.length === 0) return null;
      const first = states[0];
      const last = states[states.length - 1];

      if (t < first.time || t > last.time) return null;

      let low = 0, high = states.length - 1;
      while (low <= high) {
        const mid = (low + high) >> 1;
        if (states[mid].time < t) low = mid + 1;
        else high = mid - 1;
      }

      const idx = Math.max(0, Math.min(low, states.length - 1));
      if (idx === 0) return states[0];
      const s0 = states[idx - 1];
      const s1 = states[idx];
      const alpha = (t - s0.time) / (s1.time - s0.time || 1);

      let dHeading = s1.heading - s0.heading;
      while (dHeading > Math.PI) dHeading -= Math.PI * 2;
      while (dHeading < -Math.PI) dHeading += Math.PI * 2;
      const interpHeading = s0.heading + dHeading * alpha;

      return {
        vehicle_id: s0.vehicle_id,
        x: s0.x + (s1.x - s0.x) * alpha,
        y: s0.y + (s1.y - s0.y) * alpha,
        heading: interpHeading,
        speed: s0.speed + (s1.speed - s0.speed) * alpha,
        acceleration: s0.acceleration,
        steering_angle: s0.steering_angle,
        brake_light: s1.brake_light,
        turn_signal: s1.turn_signal,
        vehicle_type: s0.vehicle_type,
        color: s0.color
      };
    }

    function updateSimulation(t) {
      slider.value = t.toFixed(1);
      const min = Math.floor(t / 60);
      const sec = (t % 60).toFixed(1);
      const maxMin = Math.floor(maxDuration / 60);
      const maxSec = (maxDuration % 60).toFixed(1);
      const curStr = `${min.toString().padStart(2, '0')}:${sec.padStart(4, '0')}`;
      const endStr = `${maxMin.toString().padStart(2, '0')}:${maxSec.padStart(4, '0')}`;
      timeDisplay.textContent = `${curStr} / ${endStr}`;

      let currentStep = steps[0];
      for (let i = 0; i < steps.length; i++) {
        if (steps[i].time <= t) currentStep = steps[i];
        else break;
      }

      if (currentStep) {
        updateSignals(currentStep);
        updateHUDMetrics(currentStep);
      }

      let activeCount = 0;
      let selectedState = null;

      for (const [vid, states] of Object.entries(trajectories)) {
        const state = getInterpolatedState(states, t);
        let veh = vehicleObjects.get(vid);

        if (!state) {
          if (veh) {
            veh.group.visible = false;
          }
          continue;
        }

        activeCount++;
        if (vid === selectedVehicleId) selectedState = state;

        if (!veh) {
          veh = createVehicleMesh(state.vehicle_type, state.color);
          veh.group.userData = { vehicleId: vid };
          scene.add(veh.group);
          vehicleObjects.set(vid, veh);
        }

        veh.group.visible = true;
        veh.group.position.set(state.x, 0, state.y);
        veh.group.rotation.y = -state.heading + Math.PI / 2;

        const brakeMat = state.brake_light ? 0xff0000 : 0x550011;
        veh.tlLeft.material.color.setHex(brakeMat);
        veh.tlRight.material.color.setHex(brakeMat);

        const blinkOn = Math.sin(t * 9) > 0;
        veh.blLeft.visible = (state.turn_signal === 'left') && blinkOn;
        veh.blRight.visible = (state.turn_signal === 'right') && blinkOn;

        veh.wheels.forEach(w => {
          w.mesh.rotation.x += state.speed * 0.04;
          if (w.canSteer) {
            w.pivot.rotation.y = state.steering_angle;
          }
        });
      }

      document.getElementById('hud-active-veh').textContent = activeCount;

      if (selectedState) {
        updateInspector(selectedState);
      }

      updateFollowCamera(selectedState);
    }

    function updateSignals(step) {
      const activePhase = step.active_phase_id;
      const state = step.signal_state;
      const isNS = activePhase === 'P1';

      const nsIsGreen = isNS && state === 'green';
      const nsIsYellow = isNS && state === 'yellow';
      const nsIsRed = !nsIsGreen && !nsIsYellow;

      const ewIsGreen = !isNS && state === 'green';
      const ewIsYellow = !isNS && state === 'yellow';
      const ewIsRed = !ewIsGreen && !ewIsYellow;

      const hudNsRed = document.getElementById('hud-ns-red');
      const hudNsYel = document.getElementById('hud-ns-yellow');
      const hudNsGrn = document.getElementById('hud-ns-green');
      const hudNsBadge = document.getElementById('hud-ns-badge');

      if (hudNsRed) {
        hudNsRed.className = 'sig-bulb red' + (nsIsRed ? ' active' : '');
        hudNsYel.className = 'sig-bulb yellow' + (nsIsYellow ? ' active' : '');
        hudNsGrn.className = 'sig-bulb green' + (nsIsGreen ? ' active' : '');
        if (nsIsGreen) {
          hudNsBadge.className = 'sig-badge badge-green';
          hudNsBadge.textContent = 'GO (GREEN)';
        } else if (nsIsYellow) {
          hudNsBadge.className = 'sig-badge badge-yellow';
          hudNsBadge.textContent = 'CLEARING (YELLOW)';
        } else {
          hudNsBadge.className = 'sig-badge badge-red';
          hudNsBadge.textContent = 'STOP (RED)';
        }
      }

      const hudEwRed = document.getElementById('hud-ew-red');
      const hudEwYel = document.getElementById('hud-ew-yellow');
      const hudEwGrn = document.getElementById('hud-ew-green');
      const hudEwBadge = document.getElementById('hud-ew-badge');

      if (hudEwRed) {
        hudEwRed.className = 'sig-bulb red' + (ewIsRed ? ' active' : '');
        hudEwYel.className = 'sig-bulb yellow' + (ewIsYellow ? ' active' : '');
        hudEwGrn.className = 'sig-bulb green' + (ewIsGreen ? ' active' : '');
        if (ewIsGreen) {
          hudEwBadge.className = 'sig-badge badge-green';
          hudEwBadge.textContent = 'GO (GREEN)';
        } else if (ewIsYellow) {
          hudEwBadge.className = 'sig-badge badge-yellow';
          hudEwBadge.textContent = 'CLEARING (YELLOW)';
        } else {
          hudEwBadge.className = 'sig-badge badge-red';
          hudEwBadge.textContent = 'STOP (RED)';
        }
      }

      const pLed = document.getElementById('phase-led');
      const pLabel = document.getElementById('phase-label');
      if (pLabel) {
        const dirName = isNS ? 'North-South' : 'East-West';
        const stName = state.toUpperCase();
        pLabel.textContent = `Phase: ${activePhase} (${dirName} • ${stName})`;
      }
      if (pLed) {
        const ledCol = state === 'green' ? '#10b981' : (
          state === 'yellow' ? '#f59e0b' : '#ef4444'
        );
        pLed.style.background = ledCol;
        pLed.style.boxShadow = `0 0 10px ${ledCol}`;
      }

      for (const [dir, sm] of Object.entries(signalMeshes)) {
        const isDirNS = (dir === 'north' || dir === 'south');
        const isGreen = (isDirNS && nsIsGreen) || (!isDirNS && ewIsGreen);
        const isYellow = (isDirNS && nsIsYellow) || (!isDirNS && ewIsYellow);

        const rCol = isGreen || isYellow ? 0x18181b : 0xff0033;
        const yCol = isYellow ? 0xffaa00 : 0x18181b;
        const gCol = isGreen ? 0x00ff66 : 0x18181b;

        sm.heads.forEach(h => {
          h.red.material.color.setHex(rCol);
          h.yellow.material.color.setHex(yCol);
          h.green.material.color.setHex(gCol);
        });

        if (isGreen) {
          sm.light.color.setHex(0x00ff66);
          sm.light.intensity = 3.5;
        } else if (isYellow) {
          sm.light.color.setHex(0xffaa00);
          sm.light.intensity = 3.0;
        } else {
          sm.light.color.setHex(0xff0033);
          sm.light.intensity = 2.5;
        }

        if (sm.stopBar) {
          const barCol = isGreen ? 0x10b981 : (
            isYellow ? 0xf59e0b : 0xef4444
          );
          sm.stopBar.material.color.setHex(barCol);
        }
      }
    }

    function updateHUDMetrics(step) {
      let maxQ = 0;
      if (step.queue_lengths) {
        for (const q of Object.values(step.queue_lengths)) {
          if (q > maxQ) maxQ = q;
        }
      }
      document.getElementById('hud-max-queue').textContent = maxQ;
      const totalServed = SIM_DATA.metadata.total_discharges || 0;
      document.getElementById('hud-served-veh').textContent = totalServed;
      const avgD = (SIM_DATA.metadata.average_delay || 0).toFixed(1);
      document.getElementById('hud-avg-delay').textContent = `${avgD} s`;
    }

    function updateInspector(st) {
      inspector.style.display = 'flex';
      document.getElementById('insp-id').textContent = st.vehicle_id;
      document.getElementById('insp-type').textContent = (
        st.vehicle_type.replace('_', ' ').toUpperCase()
      );
      const spdKmh = (st.speed * 3.6).toFixed(1);
      document.getElementById('insp-speed').textContent = `${spdKmh} km/h`;
      const accStr = st.acceleration.toFixed(2);
      document.getElementById('insp-acc').textContent = `${accStr} m/s²`;
      const degStr = (st.heading * 180 / Math.PI).toFixed(1);
      document.getElementById('insp-heading').textContent = `${degStr}°`;
      document.getElementById('insp-signal').textContent = (
        st.turn_signal.toUpperCase()
      );
    }

    function updateFollowCamera(st) {
      if (!st) return;
      if (currentCameraMode === 'chase') {
        controls.enabled = false;
        const dist = 11;
        const height = 4.8;
        const rad = -st.heading + Math.PI / 2;
        const cx = st.x - Math.sin(rad) * dist;
        const cz = st.y - Math.cos(rad) * dist;
        camera.position.set(cx, height, cz);
        camera.lookAt(st.x, 1.4, st.y);
      } else if (currentCameraMode === 'cockpit') {
        controls.enabled = false;
        const rad = -st.heading + Math.PI / 2;
        const cx = st.x + Math.sin(rad) * 0.4;
        const cz = st.y + Math.cos(rad) * 0.4;
        camera.position.set(cx, 1.6, cz);
        camera.lookAt(
          st.x + Math.sin(rad) * 25, 1.6, st.y + Math.cos(rad) * 25
        );
      }
    }

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    window.addEventListener('click', (e) => {
      if (e.target.closest('.interactive')) return;
      mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);

      const intersects = raycaster.intersectObjects(scene.children, true);
      for (const hit of intersects) {
        let p = hit.object;
        while (p && !p.userData.vehicleId) p = p.parent;
        if (p && p.userData.vehicleId) {
          selectedVehicleId = p.userData.vehicleId;
          return;
        }
      }
    });

    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space') {
        isPlaying = !isPlaying;
        btnPlay.textContent = isPlaying ? 'Pause' : 'Play';
        btnPlay.classList.toggle('btn-play', isPlaying);
      } else if (e.key === '1') setCameraMode('cinematic');
      else if (e.key === '2') setCameraMode('orbit');
      else if (e.key === '3') setCameraMode('drone');
      else if (e.key === '4') setCameraMode('chase');
      else if (e.key === '5') setCameraMode('cockpit');
      else if (e.key === 'd' || e.key === 'D') {
        const modes = ['day', 'sunset', 'night'];
        const activeBtn = document.querySelector('.light-btn.active');
        const nextIdx = (
          modes.indexOf(activeBtn.dataset.light) + 1
        ) % modes.length;
        document.querySelectorAll('.light-btn')[nextIdx].click();
      } else if (e.key === 'r' || e.key === 'R') {
        btnReset.click();
      }
    });

    let lastClock = performance.now();
    function animate(now) {
      requestAnimationFrame(animate);
      const dt = (now - lastClock) / 1000;
      lastClock = now;

      if (isPlaying) {
        currentTime += dt * playbackSpeed;
        if (currentTime > maxDuration) {
          if (isLooping) currentTime = 0;
          else {
            currentTime = maxDuration;
            isPlaying = false;
            btnPlay.textContent = 'Play';
            btnPlay.classList.remove('btn-play');
          }
        }
        updateSimulation(currentTime);
      }

      if (controls.enabled) {
        controls.update();
      }

      renderer.render(scene, camera);
    }

    updateSimulation(0);
    requestAnimationFrame(animate);
        """,
        "  </script>",
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def export_3d_html_visualizer(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    destination: str | Path | TextIO,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    step_size: float = 1.0,
    substep_dt: float = 0.2,
) -> None:
    html_content = generate_3d_html_visualizer(
        results=results,
        intersection=intersection,
        signal_plan=signal_plan,
        controller_name=controller_name,
        scenario_name=scenario_name,
        seed=seed,
        step_size=step_size,
        substep_dt=substep_dt,
    )

    if hasattr(destination, "write"):
        destination.write(html_content)
    else:
        dest_path = Path(str(destination))
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(html_content, encoding="utf-8")
