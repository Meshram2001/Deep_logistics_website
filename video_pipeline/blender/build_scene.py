"""Build an India logistics network hero scene in Blender.

What this script does:
- Imports an India states SVG (each state should be a separate path).
- Converts curves to meshes and gives them 3D thickness.
- Loads geocoded city pins from ../locations_geocoded.json.
- Places pin meshes on top of the map using a simple lat/lon -> XY projection.
- Adds emissive materials for glow, and basic keyframes (pins appear with scale + emission).

How to run:
1) Put your India states SVG at: video_pipeline/assets/india_states.svg
2) Generate locations_geocoded.json:
     python video_pipeline/geocode_locations.py
3) Open Blender, then run:
     blender --background --python video_pipeline/blender/build_scene.py

Note: This is a starting point. High-quality state outline glow, connection line animation,
      and camera choreography typically require additional artistic tuning.
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
MAP_Z_THICKNESS = 0.25
PIN_HEIGHT = 0.8
PIN_RADIUS = 0.08

# Rough bounding box for India (used for projecting lat/lon to plane coords)
# These are approximate; tune after importing your SVG.
INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 37.5
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 97.5

# Output collection names
COL_MAP = "INDIA_MAP"
COL_PINS = "CITY_PINS"


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

    # Basic render look (Blender 4.1 friendly defaults)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.06

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

    map_mat = create_emission_material("MapBase", color=(0.93, 0.94, 0.96, 1.0), strength=0.05)
    glow_mat = create_emission_material("StateGlow", color=(0.15, 0.6, 1.0, 1.0), strength=0.0)

    # Put map objects into map collection
    for o in imported:
        apply_material(o, map_mat)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col_map.objects.link(o)

    # Create a subtle glowing duplicate for selected states (state-wise highlight stub)
    # We animate emission strength on the duplicate.
    highlight_frame = 1
    for state_name, state_id in STATE_IDS_TO_HIGHLIGHT:
        state_obj = find_state_object(imported, state_id)
        if state_obj is None:
            continue

        dup = state_obj.copy()
        dup.data = state_obj.data.copy()
        dup.name = f"{state_id}_HIGHLIGHT"
        dup.scale = (1.002, 1.002, 1.002)
        dup.location.z += 0.01
        apply_material(dup, glow_mat)

        col_map.objects.link(dup)

        # Animate glow in/out over ~30 frames
        keyframe_material_emission(glow_mat, 0.0, highlight_frame)
        keyframe_material_emission(glow_mat, 6.0, highlight_frame + 10)
        keyframe_material_emission(glow_mat, 0.0, highlight_frame + 32)
        highlight_frame += 38

    # Determine map bounds (in object space after import)
    # We'll use all map objects combined to estimate XY size.
    min_x = min(v.co.x for o in imported for v in o.data.vertices)
    max_x = max(v.co.x for o in imported for v in o.data.vertices)
    min_y = min(v.co.y for o in imported for v in o.data.vertices)
    max_y = max(v.co.y for o in imported for v in o.data.vertices)
    width = max_x - min_x
    height = max_y - min_y

    locations = load_locations()

    pin_mat = create_emission_material("PinGlow", color=(1.0, 0.72, 0.15, 1.0), strength=6.0)

    frame = 1
    for state, cities in locations.items():
        for entry in cities:
            city = entry["city"]
            lat = entry.get("lat")
            lon = entry.get("lon")
            if lat is None or lon is None:
                continue

            pin = create_pin(f"pin_{state}_{city}".replace(" ", "_"))
            apply_material(pin, pin_mat)

            pos = latlon_to_xy(float(lat), float(lon), width, height)
            pin.location = (pos.x, pos.y, MAP_Z_THICKNESS + 0.2)

            # link to collection
            for c in pin.users_collection:
                c.objects.unlink(pin)
            col_pins.objects.link(pin)

            keyframe_pop_in(pin, frame)
            frame += 5

    # Camera + lighting (simple defaults; refine in UI)
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = (0.0, -height * 0.9, height * 0.55)
    cam.rotation_euler = (1.05, 0.0, 0.0)

    sun_data = bpy.data.lights.new(name="KeyLight", type="SUN")
    sun_data.energy = 2.5
    sun = bpy.data.objects.new(name="KeyLight", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (0.95, 0.0, 0.55)

    # Basic render settings
    scene.frame_start = 1
    scene.frame_end = max(260, frame + 40, highlight_frame + 40)
    scene.render.resolution_x = 3840
    scene.render.resolution_y = 2160
    scene.render.fps = 30

    out_blend = ROOT / "blender" / "india_network_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"Scene built and saved to {out_blend}. Open it in Blender 4.1 UI for lighting/camera tuning, then render to MP4.")


if __name__ == "__main__":
    main()
