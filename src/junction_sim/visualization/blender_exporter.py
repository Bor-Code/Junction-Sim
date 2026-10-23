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


def generate_blender_script(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    fps: int = 24,
    substep_dt: float = 0.2,
) -> str:
    sim_data = serialize_simulation_data(
        results=results,
        intersection=intersection,
        signal_plan=signal_plan,
        controller_name=controller_name,
        scenario_name=scenario_name,
        seed=seed,
    )

    traj_engine = TrajectoryEngine(intersection=intersection, signal_plan=signal_plan)
    raw_trajectories = traj_engine.generate_vehicle_states(
        results=results, substep_dt=substep_dt
    )
    trajectories_data = export_trajectories_to_dict(raw_trajectories)
    sim_data["trajectories"] = trajectories_data

    json_payload = json.dumps(sim_data)

    lines = [
        "import math",
        "import json",
        "try:",
        "    import bpy",
        "except ImportError:",
        "    bpy = None",
        "",
        f"SIM_DATA = {json_payload}",
        f"FPS = {fps}",
        "",
        "def run_blender_setup():",
        "    if bpy is None:",
        "        return",
        "",
        "    for obj in list(bpy.data.objects):",
        "        bpy.data.objects.remove(obj, do_unlink=True)",
        "    for mesh in list(bpy.data.meshes):",
        "        bpy.data.meshes.remove(mesh, do_unlink=True)",
        "    for mat in list(bpy.data.materials):",
        "        bpy.data.materials.remove(mat, do_unlink=True)",
        "",
        "    scene = bpy.context.scene",
        "    scene.render.engine = 'CYCLES'",
        "    scene.render.fps = FPS",
        "    duration = SIM_DATA.get('metadata', {}).get('duration', 30.0)",
        "    scene.frame_start = 1",
        "    scene.frame_end = max(1, int(duration * FPS))",
        "",
        "    asphalt_mat = bpy.data.materials.new(name='Mat_Asphalt')",
        "    asphalt_mat.use_nodes = True",
        "    bsdf = asphalt_mat.node_tree.nodes.get('Principled BSDF')",
        "    if bsdf:",
        "        bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.06, 1.0)",
        "        bsdf.inputs['Roughness'].default_value = 0.85",
        "",
        "    road_mesh = bpy.data.meshes.new('RoadMesh')",
        "    road_obj = bpy.data.objects.new('RoadNetwork', road_mesh)",
        "    bpy.context.collection.objects.link(road_obj)",
        "",
        "    trajectories = SIM_DATA.get('trajectories', {})",
        "    for vid, states in trajectories.items():",
        "        if not states:",
        "            continue",
        "        vtype = states[0].get('vehicle_type', 'sedan')",
        "        vcol = states[0].get('color', '#2563eb')",
        "",
        "        c_mesh = bpy.data.meshes.new(f'Mesh_{vid}')",
        "        c_obj = bpy.data.objects.new(f'Veh_{vid}', c_mesh)",
        "        bpy.context.collection.objects.link(c_obj)",
        "",
        "        c_mat = bpy.data.materials.new(name=f'Mat_{vid}')",
        "        c_mat.use_nodes = True",
        "        c_bsdf = c_mat.node_tree.nodes.get('Principled BSDF')",
        "        if c_bsdf:",
        "            hex_clean = vcol.lstrip('#')",
        "            if len(hex_clean) == 6:",
        "                r = int(hex_clean[0:2], 16) / 255.0",
        "                g = int(hex_clean[2:4], 16) / 255.0",
        "                b = int(hex_clean[4:6], 16) / 255.0",
        "                c_bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)",
        "            c_bsdf.inputs['Metallic'].default_value = 0.7",
        "            c_bsdf.inputs['Roughness'].default_value = 0.25",
        "        c_obj.data.materials.append(c_mat)",
        "",
        "        for s in states:",
        "            t = s['time']",
        "            frame = max(1, int(t * FPS))",
        "            c_obj.location = (s['x'], s['y'], s.get('z', 0.0))",
        "            c_obj.rotation_euler = (0, 0, s['heading'])",
        "            c_obj.keyframe_insert(data_path='location', frame=frame)",
        "            c_obj.keyframe_insert(data_path='rotation_euler', frame=frame)",
        "",
        "    sun_data = bpy.data.lights.new(name='SunLight', type='SUN')",
        "    sun_data.energy = 3.5",
        "    sun_obj = bpy.data.objects.new(name='Sun', object_data=sun_data)",
        "    sun_obj.rotation_euler = (math.radians(50), math.radians(25), 0)",
        "    bpy.context.collection.objects.link(sun_obj)",
        "",
        "    cam_data = bpy.data.cameras.new(name='CinematicCam')",
        "    cam_obj = bpy.data.objects.new(name='Camera', object_data=cam_data)",
        "    cam_obj.location = (45, -45, 38)",
        "    cam_obj.rotation_euler = (",
        "        math.radians(60), 0, math.radians(45)",
        "    )",
        "    bpy.context.collection.objects.link(cam_obj)",
        "    scene.camera = cam_obj",
        "",
        "if __name__ == '__main__':",
        "    run_blender_setup()",
    ]

    return "\n".join(lines) + "\n"


def export_blender_script(
    results: Sequence[StepResult],
    intersection: Intersection,
    signal_plan: SignalPlan,
    destination: str | Path | TextIO,
    controller_name: str = "unknown",
    scenario_name: str = "custom",
    seed: int | None = None,
    fps: int = 24,
    substep_dt: float = 0.2,
) -> None:
    content = generate_blender_script(
        results=results,
        intersection=intersection,
        signal_plan=signal_plan,
        controller_name=controller_name,
        scenario_name=scenario_name,
        seed=seed,
        fps=fps,
        substep_dt=substep_dt,
    )

    if hasattr(destination, "write"):
        destination.write(content)
    else:
        dest_path = Path(str(destination))
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(content, encoding="utf-8")
