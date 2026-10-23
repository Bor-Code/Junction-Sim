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

    traj_engine = TrajectoryEngine(intersection=intersection, signal_plan=signal_plan)
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
        "  <title>Junction-Sim 3D Photorealistic Simulation</title>",
        '  <link rel="preconnect" href="https://fonts.googleapis.com">',
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'  <link href="{font_url}" rel="stylesheet">',
        f'  <script src="{three_cdn}"></script>',
        f'  <script src="{orbit_cdn}"></script>',
        "  <style>",
        "    :root {",
        "      --bg-glass: rgba(15, 23, 42, 0.78);",
        "      --border-glass: rgba(255, 255, 255, 0.12);",
        "      --accent-blue: #38bdf8;",
        "      --accent-emerald: #10b981;",
        "      --accent-amber: #f59e0b;",
        "      --accent-rose: #f43f5e;",
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
        "      justify-content: space-between; padding: 20px; z-index: 10;",
        "    }",
        "    .interactive { pointer-events: auto; }",
        "    .glass-card {",
        "      background: var(--bg-glass); backdrop-filter: blur(16px);",
        "      -webkit-backdrop-filter: blur(16px);",
        "      border: 1px solid var(--border-glass); border-radius: 14px;",
        "      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);",
        "    }",
        "    .header-bar {",
        "      display: flex; justify-content: space-between;",
        "      align-items: flex-start; gap: 16px;",
        "    }",
        "    .brand-card {",
        "      padding: 14px 20px; display: flex;",
        "      flex-direction: column; gap: 4px;",
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
        "      font-size: 0.8rem; color: var(--text-muted);",
        '      font-family: "JetBrains Mono", monospace;',
        "    }",
        "    .metrics-grid {",
        "      display: grid; grid-template-columns: repeat(4, auto);",
        "      gap: 10px; padding: 10px 14px;",
        "    }",
        "    .metric-pill {",
        "      display: flex; flex-direction: column; padding: 6px 12px;",
        "      border-radius: 8px; background: rgba(255, 255, 255, 0.03);",
        "      border: 1px solid rgba(255, 255, 255, 0.06);",
        "    }",
        "    .metric-label {",
        "      font-size: 0.68rem; color: var(--text-muted);",
        "      text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600;",
        "    }",
        "    .metric-value {",
        "      font-size: 1.05rem; font-weight: 700;",
        '      font-family: "JetBrains Mono", monospace; color: #f1f5f9;',
        "    }",
        "    .top-right-deck {",
        "      display: flex; flex-direction: column; gap: 12px;",
        "      align-items: flex-end;",
        "    }",
        "    .cam-modes, .lighting-modes {",
        "      display: flex; gap: 6px; padding: 6px;",
        "    }",
        "    .cam-btn, .light-btn {",
        "      background: transparent; border: 1px solid transparent;",
        "      color: var(--text-muted); padding: 6px 12px; border-radius: 8px;",
        "      font-size: 0.8rem; font-weight: 600; cursor: pointer;",
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
        "      position: absolute; left: 20px; bottom: 120px; width: 290px;",
        "      padding: 16px; display: none; flex-direction: column; gap: 10px;",
        "    }",
        "    .inspector-header {",
        "      display: flex; justify-content: space-between; align-items: center;",
        "    }",
        "    .inspector-title {",
        "      font-size: 0.95rem; font-weight: 700;",
        '      font-family: "JetBrains Mono", monospace; color: #38bdf8;',
        "    }",
        "    .inspector-close {",
        "      background: none; border: none; color: var(--text-muted);",
        "      font-size: 1.1rem; cursor: pointer; padding: 2px;",
        "    }",
        "    .inspector-row {",
        "      display: flex; justify-content: space-between;",
        "      font-size: 0.78rem; padding: 3px 0;",
        "      border-bottom: 1px solid rgba(255, 255, 255, 0.04);",
        "    }",
        "    .inspector-key { color: var(--text-muted); }",
        "    .inspector-val {",
        "      font-weight: 600;",
        '      font-family: "JetBrains Mono", monospace;',
        "    }",
        "    .inspector-btn {",
        "      margin-top: 6px; background: linear-gradient(135deg, #2563eb, #3b82f6);",
        "      border: none; color: white; padding: 7px 12px; border-radius: 8px;",
        "      font-size: 0.75rem; font-weight: 700; cursor: pointer;",
        "    }",
        "    .bottom-control-deck {",
        "      display: flex; flex-direction: column; gap: 10px;",
        "      width: 100%; max-width: 900px; margin: 0 auto; padding: 14px 20px;",
        "    }",
        "    .scrubber-row { display: flex; align-items: center; gap: 12px; }",
        "    .timeline-slider {",
        "      flex: 1; -webkit-appearance: none; height: 6px;",
        "      border-radius: 3px; background: rgba(255, 255, 255, 0.15);",
        "      outline: none; cursor: pointer;",
        "    }",
        "    .timeline-slider::-webkit-slider-thumb {",
        "      -webkit-appearance: none; width: 16px; height: 16px;",
        "      border-radius: 50%; background: #38bdf8; cursor: pointer;",
        "      box-shadow: 0 0 10px rgba(56, 189, 248, 0.8);",
        "    }",
        "    .time-badge {",
        '      font-family: "JetBrains Mono", monospace;',
        "      font-size: 0.85rem; font-weight: 700; min-width: 120px;",
        "      text-align: right;",
        "    }",
        "    .playback-row {",
        "      display: flex; justify-content: space-between; align-items: center;",
        "    }",
        "    .play-controls { display: flex; align-items: center; gap: 8px; }",
        "    .btn-ctrl {",
        "      background: rgba(255, 255, 255, 0.08);",
        "      border: 1px solid rgba(255, 255, 255, 0.1);",
        "      color: var(--text-main); padding: 7px 14px; border-radius: 8px;",
        "      font-size: 0.82rem; font-weight: 700; cursor: pointer;",
        "    }",
        "    .btn-play {",
        "      background: #38bdf8; color: #030712; border-color: #38bdf8;",
        "      padding: 7px 18px;",
        "    }",
        "    .speed-pills {",
        "      display: flex; gap: 4px; background: rgba(255, 255, 255, 0.04);",
        "      padding: 3px; border-radius: 8px;",
        "    }",
        "    .speed-btn {",
        "      background: transparent; border: none; color: var(--text-muted);",
        "      padding: 4px 8px; border-radius: 6px; font-size: 0.75rem;",
        '      font-weight: 700; cursor: pointer; font-family: "JetBrains Mono";',
        "    }",
        "    .speed-btn.active {",
        "      background: rgba(56, 189, 248, 0.2); color: #38bdf8;",
        "    }",
        "    .phase-badge {",
        "      display: flex; align-items: center; gap: 8px; padding: 5px 12px;",
        "      border-radius: 8px; background: rgba(16, 185, 129, 0.15);",
        "      border: 1px solid rgba(16, 185, 129, 0.3);",
        '      font-family: "JetBrains Mono", monospace; font-size: 0.8rem;',
        "      font-weight: 700; color: #34d399;",
        "    }",
        "    .signal-led {",
        "      width: 10px; height: 10px; border-radius: 50%;",
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
        '          <span class="brand-badge">3D Photorealistic</span>',
        "        </div>",
        (
            f'        <div class="brand-subtitle">{scenario_name} \u2022 '
            f"{controller_name} \u2022 seed {seed}</div>"
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
        '      <div class="top-right-deck interactive">',
        '        <div class="glass-card cam-modes">',
        '          <button class="cam-btn active" data-cam="orbit">Orbit</button>',
        '          <button class="cam-btn" data-cam="drone">Drone</button>',
        '          <button class="cam-btn" data-cam="chase">Chase</button>',
        '          <button class="cam-btn" data-cam="cockpit">Cockpit</button>',
        '          <button class="cam-btn" data-cam="cctv">CCTV</button>',
        "        </div>",
        '        <div class="glass-card lighting-modes">',
        '          <button class="light-btn active" data-light="day">Sunny</button>',
        '          <button class="light-btn" data-light="sunset">Sunset</button>',
        '          <button class="light-btn" data-light="night">Night</button>',
        "        </div>",
        "      </div>",
        "    </div>",
        '    <div class="glass-card inspector-card interactive" id="inspector-card">',
        '      <div class="inspector-header">',
        '        <span class="inspector-title" id="insp-id">veh_0</span>',
        '        <button class="inspector-close" id="insp-close">\u2715</button>',
        "      </div>",
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Type</span>'
            '<span class="inspector-val" id="insp-type">Sedan</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Speed</span>'
            '<span class="inspector-val" id="insp-speed">0.0 km/h</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Acceleration</span>'
            '<span class="inspector-val" id="insp-acc">0.0 m/s\u00b2</span></div>'
        ),
        (
            '      <div class="inspector-row">'
            '<span class="inspector-key">Heading</span>'
            '<span class="inspector-val" id="insp-heading">0\u00b0</span></div>'
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
    scene.background = new THREE.Color(0x87ceeb);
    scene.fog = new THREE.FogExp2(0x87ceeb, 0.0035);

    const camera = new THREE.PerspectiveCamera(
      50, window.innerWidth / window.innerHeight, 0.1, 1000
    );
    camera.position.set(45, 38, 48);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    controls.target.set(0, 0, 0);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.6);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 1.8);
    sunLight.position.set(60, 80, 50);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 250;
    sunLight.shadow.camera.left = -60;
    sunLight.shadow.camera.right = 60;
    sunLight.shadow.camera.top = 60;
    sunLight.shadow.camera.bottom = -60;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    const streetLights = [];
    const signalMeshes = {};

    function buildEnvironment() {
      const terrainGeo = new THREE.PlaneGeometry(350, 350);
      const terrainMat = new THREE.MeshStandardMaterial({
        color: 0x1e293b, roughness: 0.9, metalness: 0.1
      });
      const terrain = new THREE.Mesh(terrainGeo, terrainMat);
      terrain.rotation.x = -Math.PI / 2;
      terrain.position.y = -0.05;
      terrain.receiveShadow = true;
      scene.add(terrain);

      const asphaltMat = new THREE.MeshStandardMaterial({
        color: 0x18181b, roughness: 0.85, metalness: 0.15
      });

      const roadNS = new THREE.Mesh(new THREE.PlaneGeometry(16, 260), asphaltMat);
      roadNS.rotation.x = -Math.PI / 2;
      roadNS.receiveShadow = true;
      scene.add(roadNS);

      const roadEW = new THREE.Mesh(new THREE.PlaneGeometry(260, 16), asphaltMat);
      roadEW.rotation.x = -Math.PI / 2;
      roadEW.receiveShadow = true;
      scene.add(roadEW);

      const sidewalkMat = new THREE.MeshStandardMaterial({
        color: 0x334155, roughness: 0.8
      });
      const corners = [
        { x: 38, z: 38, w: 60, h: 60 },
        { x: -38, z: 38, w: 60, h: 60 },
        { x: 38, z: -38, w: 60, h: 60 },
        { x: -38, z: -38, w: 60, h: 60 }
      ];

      corners.forEach(c => {
        const sw = new THREE.Mesh(
          new THREE.BoxGeometry(c.w, 0.35, c.h), sidewalkMat
        );
        sw.position.set(
          c.x > 0 ? c.x + 8 : c.x - 8,
          0.15,
          c.z > 0 ? c.z + 8 : c.z - 8
        );
        sw.receiveShadow = true;
        scene.add(sw);
      });

      const whiteLineMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const yellowLineMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });

      function addDashedLine(x1, z1, x2, z2, mat, dashes = 12) {
        for (let i = 0; i < dashes; i++) {
          const t1 = i / dashes;
          const t2 = (i + 0.6) / dashes;
          const px = x1 + (x2 - x1) * ((t1 + t2) / 2);
          const pz = z1 + (z2 - z1) * ((t1 + t2) / 2);
          const len = Math.hypot((x2 - x1) * 0.6 / dashes, (z2 - z1) * 0.6 / dashes);
          const rot = Math.atan2(x2 - x1, z2 - z1);
          const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.25, len), mat);
          dash.rotation.x = -Math.PI / 2;
          dash.rotation.z = -rot;
          dash.position.set(px, 0.02, pz);
          scene.add(dash);
        }
      }

      function addStopLine(x, z, width, isHorizontal) {
        const line = new THREE.Mesh(
          new THREE.PlaneGeometry(width, 0.6), whiteLineMat
        );
        line.rotation.x = -Math.PI / 2;
        if (!isHorizontal) line.rotation.z = Math.PI / 2;
        line.position.set(x, 0.02, z);
        scene.add(line);
      }

      function addZebraCrossing(centerX, centerZ, isHorizontal) {
        const stripes = 8;
        for (let i = 0; i < stripes; i++) {
          const offset = (i - (stripes - 1) / 2) * 1.5;
          const mesh = new THREE.Mesh(
            new THREE.PlaneGeometry(0.8, 3.8), whiteLineMat
          );
          mesh.rotation.x = -Math.PI / 2;
          if (isHorizontal) {
            mesh.rotation.z = Math.PI / 2;
            mesh.position.set(centerX + offset, 0.02, centerZ);
          } else {
            mesh.position.set(centerX, 0.02, centerZ + offset);
          }
          scene.add(mesh);
        }
      }

      addStopLine(3.5, 12, 7, true);
      addStopLine(-3.5, -12, 7, true);
      addStopLine(12, -3.5, 7, false);
      addStopLine(-12, 3.5, 7, false);

      addZebraCrossing(0, 15, true);
      addZebraCrossing(0, -15, true);
      addZebraCrossing(15, 0, false);
      addZebraCrossing(-15, 0, false);

      addDashedLine(0, 16, 0, 120, yellowLineMat, 20);
      addDashedLine(0, -16, 0, -120, yellowLineMat, 20);
      addDashedLine(16, 0, 120, 0, yellowLineMat, 20);
      addDashedLine(-16, 0, -120, 0, yellowLineMat, 20);

      addDashedLine(3.5, 16, 3.5, 120, whiteLineMat, 20);
      addDashedLine(-3.5, 16, -3.5, 120, whiteLineMat, 20);
      addDashedLine(3.5, -16, 3.5, -120, whiteLineMat, 20);
      addDashedLine(-3.5, -16, -3.5, -120, whiteLineMat, 20);
      addDashedLine(16, 3.5, 120, 3.5, whiteLineMat, 20);
      addDashedLine(16, -3.5, 120, -3.5, whiteLineMat, 20);
      addDashedLine(-16, 3.5, -120, 3.5, whiteLineMat, 20);
      addDashedLine(-16, -3.5, -120, -3.5, whiteLineMat, 20);

      buildTreesAndLamps();
      buildTrafficSignals();
    }

    function buildTreesAndLamps() {
      const treePositions = [
        { x: 14, z: 22 }, { x: 22, z: 14 }, { x: 22, z: 22 },
        { x: -14, z: 22 }, { x: -22, z: 14 }, { x: -22, z: 22 },
        { x: 14, z: -22 }, { x: 22, z: -14 }, { x: 22, z: -22 },
        { x: -14, z: -22 }, { x: -22, z: -14 }, { x: -22, z: -22 }
      ];

      const trunkMat = new THREE.MeshStandardMaterial({
        color: 0x451a03, roughness: 0.9
      });
      const foliageMat = new THREE.MeshStandardMaterial({
        color: 0x15803d, roughness: 0.6
      });

      treePositions.forEach(p => {
        const trunk = new THREE.Mesh(
          new THREE.CylinderGeometry(0.3, 0.4, 2.8, 8), trunkMat
        );
        trunk.position.set(p.x, 1.4, p.z);
        trunk.castShadow = true;
        scene.add(trunk);

        const fol = new THREE.Mesh(
          new THREE.DodecahedronGeometry(1.8, 1), foliageMat
        );
        fol.position.set(p.x, 3.5, p.z);
        fol.castShadow = true;
        scene.add(fol);
      });

      const lampPositions = [
        { x: 10, z: 10 }, { x: -10, z: 10 },
        { x: 10, z: -10 }, { x: -10, z: -10 }
      ];

      const metalMat = new THREE.MeshStandardMaterial({
        color: 0x475569, metalness: 0.8, roughness: 0.3
      });
      const lampGlowMat = new THREE.MeshStandardMaterial({
        color: 0xfef08a, emissive: 0xfef08a, emissiveIntensity: 0.8
      });

      lampPositions.forEach(p => {
        const pole = new THREE.Mesh(
          new THREE.CylinderGeometry(0.12, 0.16, 7, 8), metalMat
        );
        pole.position.set(p.x, 3.5, p.z);
        pole.castShadow = true;
        scene.add(pole);

        const bulb = new THREE.Mesh(
          new THREE.SphereGeometry(0.35, 12, 12), lampGlowMat
        );
        bulb.position.set(p.x, 7.1, p.z);
        scene.add(bulb);

        const pLight = new THREE.PointLight(0xfef08a, 0, 25);
        pLight.position.set(p.x, 7, p.z);
        scene.add(pLight);
        streetLights.push({ light: pLight, bulb });
      });
    }

    function buildTrafficSignals() {
      const metalMat = new THREE.MeshStandardMaterial({
        color: 0x1e293b, metalness: 0.7, roughness: 0.4
      });
      const darkHousingMat = new THREE.MeshStandardMaterial({
        color: 0x09090b, roughness: 0.8
      });

      const heads = [
        { id: 'north', x: 8.5, z: 12.5, rot: 0 },
        { id: 'south', x: -8.5, z: -12.5, rot: Math.PI },
        { id: 'east', x: 12.5, z: -8.5, rot: Math.PI / 2 },
        { id: 'west', x: -12.5, z: 8.5, rot: -Math.PI / 2 }
      ];

      heads.forEach(h => {
        const pole = new THREE.Mesh(
          new THREE.CylinderGeometry(0.15, 0.2, 6, 8), metalMat
        );
        pole.position.set(h.x, 3, h.z);
        pole.castShadow = true;
        scene.add(pole);

        const arm = new THREE.Mesh(
          new THREE.CylinderGeometry(0.1, 0.1, 5, 8), metalMat
        );
        arm.rotation.z = Math.PI / 2;
        arm.rotation.y = h.rot;
        arm.position.set(h.x, 5.8, h.z);
        scene.add(arm);

        const box = new THREE.Mesh(
          new THREE.BoxGeometry(0.6, 1.6, 0.45), darkHousingMat
        );
        box.position.set(h.x, 5.8, h.z);
        box.rotation.y = h.rot;
        box.castShadow = true;
        scene.add(box);

        const redMat = new THREE.MeshStandardMaterial({
          color: 0x3f0e0e, roughness: 0.3
        });
        const yelMat = new THREE.MeshStandardMaterial({
          color: 0x3d2900, roughness: 0.3
        });
        const grnMat = new THREE.MeshStandardMaterial({
          color: 0x06301a, roughness: 0.3
        });

        const lensGeo = new THREE.SphereGeometry(0.16, 16, 16);

        const rMesh = new THREE.Mesh(lensGeo, redMat);
        rMesh.position.set(0, 0.5, 0.22);
        box.add(rMesh);

        const yMesh = new THREE.Mesh(lensGeo, yelMat);
        yMesh.position.set(0, 0, 0.22);
        box.add(yMesh);

        const gMesh = new THREE.Mesh(lensGeo, grnMat);
        gMesh.position.set(0, -0.5, 0.22);
        box.add(gMesh);

        const light = new THREE.PointLight(0x10b981, 0, 18);
        light.position.set(h.x, 5.8, h.z);
        scene.add(light);

        signalMeshes[h.id] = { red: rMesh, yellow: yMesh, green: gMesh, light };
      });
    }

    const vehicleObjects = new Map();

    function createVehicleMesh(type, colorHex) {
      const group = new THREE.Group();

      let len = 4.2, wid = 1.9, hei = 1.35;
      if (type === 'suv') { len = 4.6; wid = 2.0; hei = 1.6; }
      else if (type === 'van') { len = 5.2; wid = 2.1; hei = 1.9; }
      else if (type === 'bus') { len = 9.5; wid = 2.4; hei = 2.6; }
      else if (type === 'hatchback') { len = 3.8; wid = 1.8; hei = 1.3; }

      const bodyMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorHex),
        metalness: 0.65,
        roughness: 0.25
      });
      const glassMat = new THREE.MeshStandardMaterial({
        color: 0x0f172a, roughness: 0.1, metalness: 0.2
      });
      const wheelRubberMat = new THREE.MeshStandardMaterial({
        color: 0x171717, roughness: 0.9
      });

      const baseMesh = new THREE.Mesh(
        new THREE.BoxGeometry(wid, hei * 0.55, len), bodyMat
      );
      baseMesh.position.y = hei * 0.45;
      baseMesh.castShadow = true;
      group.add(baseMesh);

      const cabinLen = type === 'bus' ? len * 0.9 : len * 0.55;
      const cabinMesh = new THREE.Mesh(
        new THREE.BoxGeometry(wid * 0.88, hei * 0.5, cabinLen), glassMat
      );
      cabinMesh.position.y = hei * 0.85;
      cabinMesh.position.z = type === 'bus' ? 0 : -len * 0.05;
      cabinMesh.castShadow = true;
      group.add(cabinMesh);

      const headMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const tailMat = new THREE.MeshBasicMaterial({ color: 0xff0033 });
      const amberMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });

      const hlLeft = new THREE.Mesh(
        new THREE.BoxGeometry(0.28, 0.18, 0.05), headMat
      );
      hlLeft.position.set(-wid * 0.36, hei * 0.45, len * 0.5 + 0.01);
      group.add(hlLeft);

      const hlRight = new THREE.Mesh(
        new THREE.BoxGeometry(0.28, 0.18, 0.05), headMat
      );
      hlRight.position.set(wid * 0.36, hei * 0.45, len * 0.5 + 0.01);
      group.add(hlRight);

      const tlLeft = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.18, 0.05), tailMat
      );
      tlLeft.position.set(-wid * 0.36, hei * 0.45, -len * 0.5 - 0.01);
      group.add(tlLeft);

      const tlRight = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.18, 0.05), tailMat
      );
      tlRight.position.set(wid * 0.36, hei * 0.45, -len * 0.5 - 0.01);
      group.add(tlRight);

      const blLeft = new THREE.Mesh(
        new THREE.BoxGeometry(0.15, 0.12, 0.05), amberMat
      );
      blLeft.position.set(-wid * 0.42, hei * 0.45, len * 0.48);
      blLeft.visible = false;
      group.add(blLeft);

      const blRight = new THREE.Mesh(
        new THREE.BoxGeometry(0.15, 0.12, 0.05), amberMat
      );
      blRight.position.set(wid * 0.42, hei * 0.45, len * 0.48);
      blRight.visible = false;
      group.add(blRight);

      const wheels = [];
      const wheelGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.25, 16);
      wheelGeo.rotateZ(Math.PI / 2);

      const wOffsets = [
        { x: -wid * 0.48, z: len * 0.32, steer: true },
        { x: wid * 0.48, z: len * 0.32, steer: true },
        { x: -wid * 0.48, z: -len * 0.32, steer: false },
        { x: wid * 0.48, z: -len * 0.32, steer: false }
      ];

      wOffsets.forEach(wo => {
        const wPivot = new THREE.Group();
        wPivot.position.set(wo.x, 0.35, wo.z);

        const wMesh = new THREE.Mesh(wheelGeo, wheelRubberMat);
        wMesh.castShadow = true;
        wPivot.add(wMesh);

        group.add(wPivot);
        wheels.push({ pivot: wPivot, mesh: wMesh, canSteer: wo.steer });
      });

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
    let currentCameraMode = 'orbit';

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
      if (mode === 'orbit') {
        controls.enabled = true;
        controls.target.set(0, 0, 0);
      } else if (mode === 'drone') {
        controls.enabled = true;
        camera.position.set(0, 75, 45);
        controls.target.set(0, 0, 0);
      } else if (mode === 'cctv') {
        controls.enabled = false;
        camera.position.set(16, 12, 16);
        camera.lookAt(0, 1, 0);
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
        scene.background = new THREE.Color(0x87ceeb);
        scene.fog.color = new THREE.Color(0x87ceeb);
        sunLight.color.setHex(0xfffaed);
        sunLight.intensity = 1.8;
        hemiLight.intensity = 0.6;
        streetLights.forEach(sl => { sl.light.intensity = 0; });
      } else if (mode === 'sunset') {
        scene.background = new THREE.Color(0x31102f);
        scene.fog.color = new THREE.Color(0x31102f);
        sunLight.color.setHex(0xf97316);
        sunLight.intensity = 2.2;
        hemiLight.intensity = 0.4;
        streetLights.forEach(sl => { sl.light.intensity = 0.4; });
      } else if (mode === 'night') {
        scene.background = new THREE.Color(0x020617);
        scene.fog.color = new THREE.Color(0x020617);
        sunLight.color.setHex(0x38bdf8);
        sunLight.intensity = 0.2;
        hemiLight.intensity = 0.15;
        streetLights.forEach(sl => { sl.light.intensity = 1.8; });
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
      if (t < states[0].time || t > states[states.length - 1].time) return null;

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

      return {
        vehicle_id: s0.vehicle_id,
        x: s0.x + (s1.x - s0.x) * alpha,
        y: s0.y + (s1.y - s0.y) * alpha,
        heading: s0.heading + (s1.heading - s0.heading) * alpha,
        speed: s0.speed + (s1.speed - s0.speed) * alpha,
        acceleration: s0.acceleration,
        steering_angle: s0.steering_angle,
        brake_light: s0.brake_light,
        turn_signal: s0.turn_signal,
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

      const pLed = document.getElementById('phase-led');
      const pLabel = document.getElementById('phase-label');
      pLabel.textContent = `Phase: ${activePhase} (${state.toUpperCase()})`;

      if (state === 'green') {
        pLed.style.background = '#10b981';
        pLed.style.boxShadow = '0 0 10px #10b981';
      } else if (state === 'yellow') {
        pLed.style.background = '#f59e0b';
        pLed.style.boxShadow = '0 0 10px #f59e0b';
      } else {
        pLed.style.background = '#ef4444';
        pLed.style.boxShadow = '0 0 10px #ef4444';
      }

      const isNS = activePhase === 'P1';
      for (const [dir, sm] of Object.entries(signalMeshes)) {
        const isDirNS = (dir === 'north' || dir === 'south');
        const isDirEW = (dir === 'east' || dir === 'west');
        const isGreen = (isDirNS && isNS && state === 'green') ||
                        (isDirEW && !isNS && state === 'green');
        const isYellow = (isDirNS && isNS && state === 'yellow') ||
                         (isDirEW && !isNS && state === 'yellow');

        sm.red.material.color.setHex(isGreen || isYellow ? 0x2b0808 : 0xff1111);
        sm.yellow.material.color.setHex(isYellow ? 0xf59e0b : 0x2b1d00);
        sm.green.material.color.setHex(isGreen ? 0x10b981 : 0x032414);

        if (isGreen) {
          sm.light.color.setHex(0x10b981);
          sm.light.intensity = 1.4;
        } else if (isYellow) {
          sm.light.color.setHex(0xf59e0b);
          sm.light.intensity = 1.2;
        } else {
          sm.light.color.setHex(0xef4444);
          sm.light.intensity = 0.8;
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
        st.vehicle_type.toUpperCase()
      );
      const spdKmh = (st.speed * 3.6).toFixed(1);
      document.getElementById('insp-speed').textContent = `${spdKmh} km/h`;
      const accStr = st.acceleration.toFixed(2);
      document.getElementById('insp-acc').textContent = `${accStr} m/s\u00b2`;
      const degStr = (st.heading * 180 / Math.PI).toFixed(1);
      document.getElementById('insp-heading').textContent = `${degStr}\u00b0`;
      document.getElementById('insp-signal').textContent = (
        st.turn_signal.toUpperCase()
      );
    }

    function updateFollowCamera(st) {
      if (!st) return;
      if (currentCameraMode === 'chase') {
        controls.enabled = false;
        const dist = 9;
        const height = 4.2;
        const rad = -st.heading + Math.PI / 2;
        const cx = st.x - Math.sin(rad) * dist;
        const cz = st.y - Math.cos(rad) * dist;
        camera.position.set(cx, height, cz);
        camera.lookAt(st.x, 1.2, st.y);
      } else if (currentCameraMode === 'cockpit') {
        controls.enabled = false;
        const rad = -st.heading + Math.PI / 2;
        const cx = st.x + Math.sin(rad) * 0.4;
        const cz = st.y + Math.cos(rad) * 0.4;
        camera.position.set(cx, 1.35, cz);
        camera.lookAt(
          st.x + Math.sin(rad) * 20, 1.35, st.y + Math.cos(rad) * 20
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
      } else if (e.key === '1') setCameraMode('orbit');
      else if (e.key === '2') setCameraMode('drone');
      else if (e.key === '3') setCameraMode('chase');
      else if (e.key === '4') setCameraMode('cockpit');
      else if (e.key === '5') setCameraMode('cctv');
      else if (e.key === 'd' || e.key === 'D') {
        const modes = ['day', 'sunset', 'night'];
        const activeBtn = document.querySelector('.light-btn.active');
        const nextIdx = (modes.indexOf(activeBtn.dataset.light) + 1) % modes.length;
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
