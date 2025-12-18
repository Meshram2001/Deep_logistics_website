"""Build an India logistics network hero scene in Blender.

This script builds a *cleaner, more cinematic* hero animation than the initial prototype:
- Dark premium map base + subtle elevation
- City pins (hub pins are brighter)
- Animated connection lines (curve reveal)
- Per-state highlight glow timing (independent materials)
- A simple camera choreography (zoom/pan between key regions, then zoom-out)

How to run:
1) Put your India states SVG at: video_pipeline/assets/india_states.svg
2) Generate locations_geocoded.json:
     python video_pipeline/geocode_locations.py
3) Build the .blend:
     blender --background --python video_pipeline/blender/build_scene.py

Then render the MP4 with:
  video_pipeline/run_blender_render.ps1
"""

import json
from pathlib import Path

import bpy
from mathutils import Vector

# State IDs in the downloaded Simplemaps SVG (video_pipeline/assets/india_states.svg)
# You can extend this list if you want to highlight more states.
STATE_IDS_TO_HIGHLIGHT = [
    ("Maharashtra", "INMH"),
    ("Chhattisgarh", "INCT"),
    ("Delhi", "INDL"),
    ("Punjab", "INPB"),
    ("Uttar Pradesh", "INUP"),
    ("Haryana", "INHR"),
    ("Gujarat", "INGJ"),
]

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "india_states.svg"
LOCATIONS_PATH = ROOT / "locations_geocoded.json"

# Scene scale settings
MAP_SCALE = 22.0  # overall scale of imported SVG
MAP_Z_THICKNESS = 0.35
PIN_HEIGHT = 0.85
PIN_RADIUS = 0.075

# Animation + render defaults (website-friendly; adjust if you want 4K)
FPS = 30
DURATION_SECONDS = 16
FRAME_START = 1
FRAME_END = FRAME_START + FPS * DURATION_SECONDS
RENDER_RES_X = 1920
RENDER_RES_Y = 1080

# Hero hubs (these will look brighter + get ripple pulses)
HUB_CITIES = {
    ("Maharashtra", "Mumbai"),
    ("Maharashtra", "Pune"),
    ("Delhi", "Kashmere Gate"),
    ("Chhattisgarh", "Raipur"),
    ("Gujarat", "Rajkot"),
    ("Punjab", "Ludhiana"),
    ("Uttar Pradesh", "Noida"),
}

# Animated connections between hubs (you can add/remove edges as desired)
CONNECTIONS = [
    (("Maharashtra", "Mumbai"), ("Maharashtra", "Pune")),
    (("Maharashtra", "Mumbai"), ("Chhattisgarh", "Raipur")),
    (("Maharashtra", "Mumbai"), ("Delhi", "Kashmere Gate")),
    (("Delhi", "Kashmere Gate"), ("Punjab", "Ludhiana")),
    (("Delhi", "Kashmere Gate"), ("Uttar Pradesh", "Noida")),
    (("Maharashtra", "Mumbai"), ("Gujarat", "Rajkot")),
]

# Rough bounding box for India (used for projecting lat/lon to plane coords)
# These are approximate; tune after importing your SVG.
INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 37.5
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 97.5

# Output collection names
COL_MAP = "INDIA_MAP"
COL_PINS = "CITY_PINS"
COL_LINES = "CONNECTION_LINES"


def ensure_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_svg(svg_path: Path) -> None:
    bpy.ops.import_curve.svg(filepath=str(svg_path))


def find_state_object(imported, state_id: str):
    # Blender's SVG importer usually uses the SVG path id as the object name.
    # Be tolerant in case Blender appends suffixes like ".001".
    for o in imported:
        if o.name == state_id or o.name.startswith(state_id + ".") or state_id in o.name:
            return o
    return None


def curves_to_mesh_and_extrude(objects, thickness: float) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        # solidify
        mod = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
        mod.thickness = thickness
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.select_set(False)


def create_emission_material(name: str, color=(0.15, 0.6, 1.0, 1.0), strength: float = 2.0):
    """Simple emission-only material (fast + great for glow)."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in list(nodes):
        nodes.remove(n)

    out = nodes.new(type="ShaderNodeOutputMaterial")
    emis = nodes.new(type="ShaderNodeEmission")
    emis.inputs[0].default_value = color
    emis.inputs[1].default_value = strength
    links.new(emis.outputs[0], out.inputs[0])

    # Make it easy to animate strength
    mat["emission_strength"] = strength
    return mat


def create_principled_material(
    name: str,
    base_color=(0.08, 0.12, 0.16, 1.0),
    roughness: float = 0.6,
    metallic: float = 0.15,
    emission_color=(0.0, 0.0, 0.0, 1.0),
    emission_strength: float = 0.0,
):
    """Premium-looking base material for the map."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in list(nodes):
        nodes.remove(n)

    out = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs[0].default_value = base_color
    bsdf.inputs[7].default_value = roughness
    bsdf.inputs[6].default_value = metallic
    bsdf.inputs[17].default_value = emission_color
    bsdf.inputs[18].default_value = emission_strength
    links.new(bsdf.outputs[0], out.inputs[0])

    return mat


def apply_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def latlon_to_xy(lat: float, lon: float, width: float, height: float) -> Vector:
    # Equirectangular projection into a rectangle
    x = (lon - INDIA_LON_MIN) / (INDIA_LON_MAX - INDIA_LON_MIN) * width - width / 2
    y = (lat - INDIA_LAT_MIN) / (INDIA_LAT_MAX - INDIA_LAT_MIN) * height - height / 2
    return Vector((x, y, 0.0))


def create_pin(name: str) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(radius=PIN_RADIUS, depth=PIN_HEIGHT * 0.75)
    stem = bpy.context.active_object
    stem.name = f"{name}_stem"

    bpy.ops.mesh.primitive_cone_add(radius1=PIN_RADIUS * 1.4, depth=PIN_HEIGHT * 0.45)
    head = bpy.context.active_object
    head.name = f"{name}_head"
    head.location.z += PIN_HEIGHT * 0.6

    # Join
    bpy.ops.object.select_all(action="DESELECT")
    stem.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = stem
    bpy.ops.object.join()

    pin = stem
    pin.name = name
    return pin


def keyframe_pop_in(obj: bpy.types.Object, frame_start: int) -> None:
    obj.scale = (0.0, 0.0, 0.0)
    obj.keyframe_insert(data_path="scale", frame=frame_start)

    obj.scale = (1.12, 1.12, 1.12)
    obj.keyframe_insert(data_path="scale", frame=frame_start + 8)

    obj.scale = (1.0, 1.0, 1.0)
    obj.keyframe_insert(data_path="scale", frame=frame_start + 14)


def keyframe_material_emission(mat: bpy.types.Material, strength: float, frame: int) -> None:
    # Works for the simple Emission-only node tree created above.
    nodes = mat.node_tree.nodes
    emis = None
    for n in nodes:
        if n.type == "EMISSION":
            emis = n
            break
    if emis is None:
        return

    emis.inputs[1].default_value = float(strength)
    emis.inputs[1].keyframe_insert(data_path="default_value", frame=frame)


def create_connection_curve(name: str, p0: Vector, p1: Vector, z: float) -> bpy.types.Object:
    """Create a smooth 3D curve between two points."""
    curve_data = bpy.data.curves.new(name=name, type="CURVE")
    curve_data.dimensions = "3D"

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(1)

    mid = (p0 + p1) / 2
    bump = Vector((0.0, 0.0, max(0.4, (p0 - p1).length * 0.08)))

    spline.bezier_points[0].co = Vector((p0.x, p0.y, z))
    spline.bezier_points[1].co = Vector((p1.x, p1.y, z))

    # Handles for smooth arc
    spline.bezier_points[0].handle_right = Vector((mid.x, mid.y, z)) + bump
    spline.bezier_points[0].handle_left = spline.bezier_points[0].co
    spline.bezier_points[1].handle_left = Vector((mid.x, mid.y, z)) + bump
    spline.bezier_points[1].handle_right = spline.bezier_points[1].co

    curve_data.bevel_depth = 0.03
    curve_data.bevel_resolution = 4

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.scene.collection.objects.link(obj)

    # Animate reveal using bevel factor
    curve_data.use_fill_caps = True
    curve_data.bevel_factor_start = 0.0
    curve_data.bevel_factor_end = 0.0

    return obj


def keyframe_curve_reveal(curve_obj: bpy.types.Object, frame_start: int, duration: int = 28):
    cd = curve_obj.data
    cd.bevel_factor_end = 0.0
    cd.keyframe_insert(data_path="bevel_factor_end", frame=frame_start)
    cd.bevel_factor_end = 1.0
    cd.keyframe_insert(data_path="bevel_factor_end", frame=frame_start + duration)


def create_pulse_ring(name: str, radius: float = 0.25) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=radius * 0.08)
    ring = bpy.context.active_object
    ring.name = name
    ring.rotation_euler = (0.0, 0.0, 0.0)
    return ring


def keyframe_pulse(ring: bpy.types.Object, mat: bpy.types.Material, frame_start: int) -> None:
    # scale pulse
    ring.scale = (0.2, 0.2, 0.2)
    ring.keyframe_insert(data_path="scale", frame=frame_start)
    ring.scale = (2.2, 2.2, 2.2)
    ring.keyframe_insert(data_path="scale", frame=frame_start + 24)

    # emission pulse
    keyframe_material_emission(mat, 18.0, frame_start)
    keyframe_material_emission(mat, 0.0, frame_start + 24)


def load_locations() -> dict:
    if not LOCATIONS_PATH.exists():
        raise RuntimeError(f"Missing {LOCATIONS_PATH}. Run geocode_locations.py first.")
    return json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))


def main() -> None:
    clear_scene()

    if not SVG_PATH.exists():
        raise RuntimeError(
            f"Missing {SVG_PATH}. Put an India states SVG there (each state as separate path)."
        )

    # Collections
    col_map = ensure_collection(COL_MAP)
    col_pins = ensure_collection(COL_PINS)
    col_lines = ensure_collection(COL_LINES)

    # Render look (Blender 4.1 / EEVEE)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.08
    # Some settings vary slightly across Blender builds; keep this robust.
    try:
        scene.eevee.use_gtao = True
    except Exception:
        pass

    try:
        scene.view_settings.view_transform = "Filmic"
    except Exception:
        pass

    try:
        scene.view_settings.look = "High Contrast"
    except Exception:
        pass

    # Dark world background
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.01, 0.015, 0.02, 1.0)
        bg.inputs[1].default_value = 1.0

    # Import SVG
    import_svg(SVG_PATH)
    imported = list(bpy.context.selected_objects)
    if not imported:
        raise RuntimeError("SVG import produced no objects.")

    # Ensure selection + active object for operators in background mode
    bpy.ops.object.select_all(action="DESELECT")
    for o in imported:
        o.select_set(True)
        o.scale = (MAP_SCALE, MAP_SCALE, MAP_SCALE)
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    curves_to_mesh_and_extrude(imported, MAP_Z_THICKNESS)

    map_mat = create_principled_material(
        "MapBase",
        base_color=(0.05, 0.09, 0.14, 1.0),
        roughness=0.65,
        metallic=0.10,
        emission_color=(0.01, 0.05, 0.09, 1.0),
        emission_strength=0.35,
    )

    # Put map objects into map collection
    for o in imported:
        apply_material(o, map_mat)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col_map.objects.link(o)

    # Create a subtle glowing duplicate for selected states (per-state glow material so timing is independent)
    highlight_frame = FRAME_START
    for state_name, state_id in STATE_IDS_TO_HIGHLIGHT:
        state_obj = find_state_object(imported, state_id)
        if state_obj is None:
            continue

        dup = state_obj.copy()
        dup.data = state_obj.data.copy()
        dup.name = f"{state_id}_HIGHLIGHT"
        dup.scale = (1.002, 1.002, 1.002)
        dup.location.z += 0.02

        glow_mat = create_emission_material(
            f"StateGlow_{state_id}",
            color=(0.12, 0.65, 1.0, 1.0),
            strength=0.0,
        )
        apply_material(dup, glow_mat)
        col_map.objects.link(dup)

        # Animate glow in/out
        keyframe_material_emission(glow_mat, 0.0, highlight_frame)
        keyframe_material_emission(glow_mat, 9.0, highlight_frame + 12)
        keyframe_material_emission(glow_mat, 0.0, highlight_frame + 44)
        highlight_frame += 60

    # Determine map bounds (in object space after import)
    # We'll use all map objects combined to estimate XY size.
    min_x = min(v.co.x for o in imported for v in o.data.vertices)
    max_x = max(v.co.x for o in imported for v in o.data.vertices)
    min_y = min(v.co.y for o in imported for v in o.data.vertices)
    max_y = max(v.co.y for o in imported for v in o.data.vertices)
    width = max_x - min_x
    height = max_y - min_y

    locations = load_locations()

    pin_normal_mat = create_emission_material(
        "PinNormal",
        color=(0.95, 0.78, 0.25, 1.0),
        strength=5.5,
    )
    pin_hub_mat = create_emission_material(
        "PinHub",
        color=(1.0, 0.25, 0.18, 1.0),
        strength=9.0,
    )
    line_mat = create_emission_material(
        "RouteLine",
        color=(0.20, 0.75, 1.0, 1.0),
        strength=3.5,
    )

    pins_by_key = {}
    frame = FRAME_START
    for state, cities in locations.items():
        for entry in cities:
            city = entry["city"]
            lat = entry.get("lat")
            lon = entry.get("lon")
            if lat is None or lon is None:
                continue

            key = (state, city)
            pin = create_pin(f"pin_{state}_{city}".replace(" ", "_"))

            if key in HUB_CITIES:
                apply_material(pin, pin_hub_mat)
            else:
                apply_material(pin, pin_normal_mat)

            pos = latlon_to_xy(float(lat), float(lon), width, height)
            pin.location = (pos.x, pos.y, MAP_Z_THICKNESS + 0.22)

            # link to collection
            for c in list(pin.users_collection):
                c.objects.unlink(pin)
            col_pins.objects.link(pin)

            keyframe_pop_in(pin, frame)
            pins_by_key[key] = (pin, pos)

            # Stagger pin reveals slightly faster for a smoother flow
            frame += 3

    # Connection lines between hubs
    line_frame = FRAME_START + 20
    for i, (a, b) in enumerate(CONNECTIONS):
        if a not in pins_by_key or b not in pins_by_key:
            continue
        _pin_a, pos_a = pins_by_key[a]
        _pin_b, pos_b = pins_by_key[b]
        curve = create_connection_curve(
            name=f"route_{a[1]}_to_{b[1]}".replace(" ", "_"),
            p0=pos_a,
            p1=pos_b,
            z=MAP_Z_THICKNESS + 0.30,
        )
        apply_material(curve, line_mat)
        for c in list(curve.users_collection):
            c.objects.unlink(curve)
        col_lines.objects.link(curve)
        keyframe_curve_reveal(curve, line_frame + i * 22, duration=28)

    # Pulse rings on hub cities
    pulse_frame = FRAME_START + 10
    for key in HUB_CITIES:
        if key not in pins_by_key:
            continue
        pin, pos = pins_by_key[key]
        ring = create_pulse_ring(f"pulse_{key[1]}".replace(" ", "_"), radius=0.22)
        ring_mat = create_emission_material(
            f"PulseRing_{key[0]}_{key[1]}".replace(" ", "_"),
            color=(0.20, 0.75, 1.0, 1.0),
            strength=0.0,
        )
        apply_material(ring, ring_mat)
        ring.location = (pos.x, pos.y, MAP_Z_THICKNESS + 0.24)

        for c in list(ring.users_collection):
            c.objects.unlink(ring)
        col_pins.objects.link(ring)

        # Loop pulses (2-3 pulses across the whole animation)
        keyframe_pulse(ring, ring_mat, pulse_frame)
        keyframe_pulse(ring, ring_mat, pulse_frame + 140)
        keyframe_pulse(ring, ring_mat, pulse_frame + 280)
        pulse_frame += 12

    # Camera + lighting
    # We animate an Empty (focus) and use Track-To for a smooth, cinematic pan/zoom.
    focus = bpy.data.objects.new("CAM_FOCUS", None)
    bpy.context.scene.collection.objects.link(focus)
    focus.empty_display_type = "SPHERE"
    focus.empty_display_size = 0.6

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 42
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 2.2
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # Track to focus
    track = cam.constraints.new(type="TRACK_TO")
    track.target = focus
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    # Try to focus on the map center initially
    focus.location = (0.0, 0.0, MAP_Z_THICKNESS)

    def set_cam_key(frame_idx: int, focus_xy: Vector, cam_offset: Vector):
        focus.location = (focus_xy.x, focus_xy.y, MAP_Z_THICKNESS)
        focus.keyframe_insert(data_path="location", frame=frame_idx)
        cam.location = (
            focus_xy.x + cam_offset.x,
            focus_xy.y + cam_offset.y,
            cam_offset.z,
        )
        cam.keyframe_insert(data_path="location", frame=frame_idx)

    # Camera story beats (focus points)
    points = [
        ("Maharashtra", "Mumbai"),
        ("Chhattisgarh", "Raipur"),
        ("Delhi", "Kashmere Gate"),
        ("Punjab", "Ludhiana"),
        ("Gujarat", "Rajkot"),
    ]

    # Offsets: slightly tilted top-down perspective
    close_offset = Vector((0.0, -height * 0.38, height * 0.28))
    mid_offset = Vector((0.0, -height * 0.55, height * 0.40))
    far_offset = Vector((0.0, -height * 0.92, height * 0.70))

    # Default fallback
    center = Vector((0.0, 0.0, 0.0))

    f0 = pins_by_key.get(points[0], (None, center))[1]
    f1 = pins_by_key.get(points[1], (None, center))[1]
    f2 = pins_by_key.get(points[2], (None, center))[1]
    f3 = pins_by_key.get(points[3], (None, center))[1]
    f4 = pins_by_key.get(points[4], (None, center))[1]

    set_cam_key(FRAME_START, f0, close_offset)
    set_cam_key(FRAME_START + 90, f1, close_offset)
    set_cam_key(FRAME_START + 180, f2, close_offset)
    set_cam_key(FRAME_START + 270, f3, close_offset)
    set_cam_key(FRAME_START + 340, f4, close_offset)
    set_cam_key(FRAME_END - 40, Vector((0.0, 0.0, 0.0)), far_offset)
    set_cam_key(FRAME_END, Vector((0.0, 0.0, 0.0)), far_offset)

    # DOF focus
    cam_data.dof.focus_object = focus

    # Lights: key + rim + fill
    sun_data = bpy.data.lights.new(name="KeyLight", type="SUN")
    sun_data.energy = 2.4
    sun = bpy.data.objects.new(name="KeyLight", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (0.85, 0.0, 0.65)

    rim_data = bpy.data.lights.new(name="RimLight", type="AREA")
    rim_data.energy = 350
    rim_data.size = 12
    rim = bpy.data.objects.new(name="RimLight", object_data=rim_data)
    bpy.context.scene.collection.objects.link(rim)
    rim.location = (0.0, height * 0.5, height * 0.9)
    rim.rotation_euler = (0.75, 0.0, 3.14)

    fill_data = bpy.data.lights.new(name="FillLight", type="AREA")
    fill_data.energy = 180
    fill_data.size = 16
    fill = bpy.data.objects.new(name="FillLight", object_data=fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (0.0, -height * 0.55, height * 0.55)
    fill.rotation_euler = (1.15, 0.0, 0.0)

    # Render settings
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.resolution_x = RENDER_RES_X
    scene.render.resolution_y = RENDER_RES_Y
    scene.render.fps = FPS

    out_blend = ROOT / "blender" / "india_network_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"Scene built and saved to {out_blend}. Open it in Blender 4.1 UI for lighting/camera tuning, then render to MP4.")


if __name__ == "__main__":
    main()
