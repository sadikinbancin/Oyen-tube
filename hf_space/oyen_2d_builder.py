from __future__ import annotations

import json
import struct
import zipfile
from pathlib import Path
from typing import Any

from oyen_2d_asset_bundle import load_embedded_manifest


def validate_asset_pack(asset_zip: str | Path) -> dict[str, Any]:
    """Validate the committed transparent PNG pack without importing Blender."""
    asset_zip = Path(asset_zip)
    if not asset_zip.is_file() or asset_zip.stat().st_size < 50_000:
        raise ValueError("ZIP aset Oyen 2D tidak ada atau terlalu kecil")
    manifest = load_embedded_manifest()
    with zipfile.ZipFile(asset_zip, "r") as archive:
        names = set(archive.namelist())
        pngs = sorted(
            name for name in names if name.startswith("layers/") and name.endswith(".png")
        )
        missing = [
            item["file"]
            for item in manifest["layers"]
            if item.get("rig_enabled", True) and item["file"] not in names
        ]
        if missing:
            raise ValueError(f"Layer PNG hilang: {missing}")
        for name in pngs:
            raw = archive.read(name)
            if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw) < 33:
                raise ValueError(f"PNG rusak: {name}")
            width, height, bit_depth, color_type = struct.unpack(">IIBB", raw[16:26])
            if width < 4 or height < 4 or bit_depth not in {8, 16}:
                raise ValueError(f"Dimensi/bit depth PNG tidak valid: {name}")
            if color_type not in {3, 4, 6}:
                raise ValueError(f"PNG tidak memiliki alpha/transparency: {name}")
            if color_type == 3 and b"tRNS" not in raw:
                raise ValueError(f"PNG palette tanpa tRNS: {name}")
    bones = manifest.get("bones", [])
    active_layers = [item for item in manifest["layers"] if item.get("rig_enabled", True)]
    if len(pngs) < 40 or len(active_layers) < 35 or len(bones) < 25:
        raise ValueError(
            f"Asset pack belum lengkap: png={len(pngs)} layer={len(active_layers)} bone={len(bones)}"
        )
    return {
        "asset_zip_bytes": asset_zip.stat().st_size,
        "png_count": len(pngs),
        "layer_count": len(manifest["layers"]),
        "active_layer_count": len(active_layers),
        "bone_count": len(bones),
    }


def build_2d_blender_script(job: dict[str, Any]) -> str:
    """Build a standalone Blender script for the Oyen Purba 2D cutout pipeline."""
    payload = json.dumps(job, ensure_ascii=False, sort_keys=True)
    template = r'''from __future__ import annotations

import json
import math
import os
import zipfile
from pathlib import Path

import bpy

JOB = json.loads(__JOB_JSON__)
OUTPUT_DIR = Path(os.environ["OYEN_OUTPUT_DIR"])
ASSET_ZIP = Path(os.environ["OYEN_2D_ASSET_ZIP"])
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR = OUTPUT_DIR / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(ASSET_ZIP, "r") as archive:
    archive.extractall(ASSET_DIR)
MANIFEST = json.loads((ASSET_DIR / "oyen_2d_layer_manifest.json").read_text(encoding="utf-8"))
TIMELINE = JOB["compiled_timeline"]
PLAN = JOB["motion_plan"]
CANVAS = MANIFEST["canvas"]
W = float(CANVAS["width"])
H = float(CANVAS["height"])
PPU = float(CANVAS["pixels_per_unit"])


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.cameras,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def pixel_to_world(point):
    x, y = float(point[0]), float(point[1])
    return ((x - W / 2.0) / PPU, (H - y) / PPU)


def set_alpha_mode(material):
    try:
        material.surface_render_method = "DITHERED"
    except Exception:
        pass
    try:
        material.blend_method = "BLEND"
    except Exception:
        pass
    try:
        material.use_transparency_overlap = False
    except Exception:
        pass
    try:
        material.show_transparent_back = True
    except Exception:
        pass


def create_sprite_material(name, image_path):
    image = bpy.data.images.load(str(image_path), check_existing=True)
    try:
        image.alpha_mode = "STRAIGHT"
    except Exception:
        pass
    material = bpy.data.materials.new(name=f"MAT_{name}")
    material.use_nodes = True
    set_alpha_mode(material)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    texture = nodes.new("ShaderNodeTexImage")
    mix = nodes.new("ShaderNodeMixShader")
    texture.image = image
    texture.interpolation = "Linear"
    emission.inputs["Strength"].default_value = 1.0
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    return material


def create_layer(layer):
    name = layer["name"]
    bone_name = layer["bone"]
    bone_spec = next(item for item in MANIFEST["bones"] if item["name"] == bone_name)
    px, py = [float(value) for value in bone_spec["pivot"]]
    x0, y0, x1, y1 = [float(value) for value in layer["bbox"]]
    left = (x0 - px) / PPU
    right = (x1 - px) / PPU
    bottom = (py - y1) / PPU
    top = (py - y0) / PPU
    vertices = [
        (left, 0.0, bottom),
        (right, 0.0, bottom),
        (right, 0.0, top),
        (left, 0.0, top),
    ]
    mesh = bpy.data.meshes.new(f"MESH_{name}")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_values = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for loop in mesh.loops:
        uv_layer.data[loop.index].uv = uv_values[loop.vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    wx, wz = pixel_to_world(bone_spec["pivot"])
    obj.location = (wx, float(layer["depth"]), wz)
    obj.data.materials.append(
        create_sprite_material(name, ASSET_DIR / layer["file"])
    )
    visible = bool(layer.get("default_visible", True))
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    obj["oyen_layer_group"] = layer.get("group", "")
    obj["oyen_layer_bone"] = bone_name
    return obj


def create_armature():
    arm_data = bpy.data.armatures.new("Oyen_Purba_2D_Rig_Data")
    arm = bpy.data.objects.new("Oyen_Purba_2D_Rig", arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    created = {}
    for spec in MANIFEST["bones"]:
        bone = arm_data.edit_bones.new(spec["name"])
        hx, hz = pixel_to_world(spec["pivot"])
        tx, tz = pixel_to_world(spec.get("tail", [spec["pivot"][0], spec["pivot"][1] - 16]))
        if abs(tx - hx) + abs(tz - hz) < 0.03:
            tz = hz + 0.16
        bone.head = (hx, 0.0, hz)
        bone.tail = (tx, 0.0, tz)
        bone.use_connect = False
        created[spec["name"]] = bone
    for spec in MANIFEST["bones"]:
        parent = spec.get("parent")
        if parent:
            created[spec["name"]].parent = created[parent]
    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in arm.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    face = arm.pose.bones.get("CTRL_FACE")
    if face is not None:
        face["blink"] = 0.0
        face["expression"] = "NEUTRAL"
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.show_in_front = True
    arm["oyen_pipeline"] = "2d-cutout-v06"
    arm["library_only"] = True
    return arm


def parent_layers(arm, objects):
    for layer in MANIFEST["layers"]:
        if not layer.get("rig_enabled", True):
            continue
        obj = objects.get(layer["name"])
        if obj is None:
            continue
        world = obj.matrix_world.copy()
        obj.parent = arm
        obj.parent_type = "BONE"
        obj.parent_bone = layer["bone"]
        obj.matrix_world = world


def reset_pose(arm):
    for bone in arm.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def key_rot(bone, frame, degrees):
    bone.rotation_mode = "XYZ"
    bone.rotation_euler[1] = math.radians(float(degrees))
    bone.keyframe_insert(data_path="rotation_euler", index=1, frame=frame)


def key_loc(bone, frame, x=0.0, z=0.0):
    bone.location = (float(x), 0.0, float(z))
    bone.keyframe_insert(data_path="location", frame=frame)


def key_scale(bone, frame, x=1.0, z=1.0):
    bone.scale = (float(x), 1.0, float(z))
    bone.keyframe_insert(data_path="scale", frame=frame)


def set_action_interpolation(action, interpolation="BEZIER"):
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = interpolation


def new_action(arm, name):
    reset_pose(arm)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = action
    return action


def build_actions(arm):
    actions = []

    action = new_action(arm, "OYEN_IDLE")
    body = arm.pose.bones["CTRL_BODY"]
    chest = arm.pose.bones["B_CHEST"]
    head = arm.pose.bones["CTRL_HEAD"]
    for frame, z, chest_deg, head_deg in [
        (1, 0.00, 0.0, 0.0), (7, 0.018, 1.2, 0.8), (13, 0.0, 0.0, 0.0),
        (19, -0.010, -0.8, -0.6), (25, 0.0, 0.0, 0.0),
    ]:
        key_loc(body, frame, z=z)
        key_rot(chest, frame, chest_deg)
        key_rot(head, frame, head_deg)
    set_action_interpolation(action)
    actions.append(action)

    action = new_action(arm, "OYEN_BLINK")
    face = arm.pose.bones["CTRL_FACE"]
    for frame, value in [(1, 0.0), (2, 0.0), (3, 1.0), (4, 1.0), (5, 0.0), (6, 0.0)]:
        face["blink"] = value
        face.keyframe_insert(data_path='["blink"]', frame=frame)
    set_action_interpolation(action, "CONSTANT")
    actions.append(action)

    action = new_action(arm, "OYEN_WALK_IN_PLACE")
    body = arm.pose.bones["CTRL_BODY"]
    pelvis = arm.pose.bones["B_PELVIS"]
    arm_l = arm.pose.bones["B_UPPER_ARM_L"]
    arm_r = arm.pose.bones["B_UPPER_ARM_R"]
    thigh_l = arm.pose.bones["B_THIGH_L"]
    thigh_r = arm.pose.bones["B_THIGH_R"]
    shin_l = arm.pose.bones["B_SHIN_L"]
    shin_r = arm.pose.bones["B_SHIN_R"]
    walk_values = [
        (1, 0.00, 2, -14, 14, 18, -18, 5, 18),
        (4, -0.030, 0, -7, 7, 8, -8, 22, 12),
        (7, 0.018, -2, 0, 0, -5, 5, 25, 5),
        (10, -0.020, 0, 7, -7, -8, 8, 12, 22),
        (13, 0.00, 2, 14, -14, -18, 18, 18, 5),
    ]
    for frame, z, pelvis_deg, al, ar, tl, tr, sl, sr in walk_values:
        key_loc(body, frame, z=z)
        key_rot(pelvis, frame, pelvis_deg)
        key_rot(arm_l, frame, al)
        key_rot(arm_r, frame, ar)
        key_rot(thigh_l, frame, tl)
        key_rot(thigh_r, frame, tr)
        key_rot(shin_l, frame, sl)
        key_rot(shin_r, frame, sr)
    set_action_interpolation(action)
    actions.append(action)

    action = new_action(arm, "OYEN_RUN_IN_PLACE")
    body = arm.pose.bones["CTRL_BODY"]
    chest = arm.pose.bones["B_CHEST"]
    arm_l = arm.pose.bones["B_UPPER_ARM_L"]
    arm_r = arm.pose.bones["B_UPPER_ARM_R"]
    thigh_l = arm.pose.bones["B_THIGH_L"]
    thigh_r = arm.pose.bones["B_THIGH_R"]
    shin_l = arm.pose.bones["B_SHIN_L"]
    shin_r = arm.pose.bones["B_SHIN_R"]
    run_values = [
        (1, 0.00, 7, -32, 32, 35, -25, 5, 35),
        (3, -0.055, 9, -18, 18, 18, -12, 35, 28),
        (5, 0.025, 8, 0, 0, -8, 8, 45, 10),
        (7, 0.070, 6, 28, -28, -25, 35, 35, 5),
        (9, 0.00, 7, 32, -32, -25, 35, 35, 5),
    ]
    for frame, z, chest_deg, al, ar, tl, tr, sl, sr in run_values:
        key_loc(body, frame, z=z)
        key_rot(chest, frame, chest_deg)
        key_rot(arm_l, frame, al)
        key_rot(arm_r, frame, ar)
        key_rot(thigh_l, frame, tl)
        key_rot(thigh_r, frame, tr)
        key_rot(shin_l, frame, sl)
        key_rot(shin_r, frame, sr)
    set_action_interpolation(action)
    actions.append(action)

    action = new_action(arm, "OYEN_HEAD_TURN")
    head = arm.pose.bones["CTRL_HEAD"]
    ear_l = arm.pose.bones["B_EAR_L"]
    ear_r = arm.pose.bones["B_EAR_R"]
    for frame, degree, x in [(1, 0.0, 0.0), (4, -2.0, -0.012), (9, 8.0, 0.025), (12, 4.0, 0.012)]:
        key_rot(head, frame, degree)
        key_loc(head, frame, x=x)
    for frame, degree in [(1, 0.0), (6, 0.0), (8, 2.5), (12, 1.0)]:
        key_rot(ear_l, frame, degree)
        key_rot(ear_r, frame, -degree)
    set_action_interpolation(action)
    actions.append(action)

    action = new_action(arm, "OYEN_WAVE")
    body = arm.pose.bones["CTRL_BODY"]
    head = arm.pose.bones["CTRL_HEAD"]
    upper = arm.pose.bones["B_UPPER_ARM_L"]
    fore = arm.pose.bones["B_FOREARM_L"]
    hand = arm.pose.bones["B_HAND_L"]
    for frame, upper_deg, fore_deg, hand_deg, body_deg, head_deg in [
        (1, 0, 0, 0, 0, 0), (6, 35, 45, 0, -1, 1), (10, 48, 70, -12, -2, 2),
        (14, 48, 65, 15, -2, 2), (18, 48, 70, -15, -2, 2),
        (22, 48, 65, 15, -2, 2), (25, 0, 0, 0, 0, 0),
    ]:
        key_rot(upper, frame, upper_deg)
        key_rot(fore, frame, fore_deg)
        key_rot(hand, frame, hand_deg)
        key_rot(body, frame, body_deg)
        key_rot(head, frame, head_deg)
    set_action_interpolation(action)
    actions.append(action)

    action = new_action(arm, "OYEN_TAIL_WAG")
    tail1 = arm.pose.bones["B_TAIL_01"]
    tail2 = arm.pose.bones["B_TAIL_02"]
    tail3 = arm.pose.bones["B_TAIL_03"]
    for frame, a, b, c in [(1, 0, 0, 0), (7, 12, 5, 0), (13, 0, 16, 8), (19, -12, 0, 20), (25, 0, -16, 0)]:
        key_rot(tail1, frame, a)
        key_rot(tail2, frame, b)
        key_rot(tail3, frame, c)
    set_action_interpolation(action)
    actions.append(action)

    arm.animation_data.action = None
    reset_pose(arm)
    return actions


def build_nla(arm):
    animation_data = arm.animation_data_create()
    animation_data.action = None
    for track in list(animation_data.nla_tracks):
        animation_data.nla_tracks.remove(track)
    track_map = {}
    for track_name in TIMELINE["tracks"].values():
        track = animation_data.nla_tracks.new()
        track.name = track_name
        track_map[track_name] = track
    for item in TIMELINE["strips"]:
        action = bpy.data.actions.get(item["action"])
        if action is None:
            raise RuntimeError(f"Action tidak ditemukan: {item['action']}")
        strip = track_map[item["track"]].strips.new(
            item["action"], int(item["frame_start"]), action
        )
        strip.blend_type = item["blend_type"]
        strip.influence = float(item["influence"])
        strip.repeat = float(item["repeat"])
        strip.frame_end = int(item["frame_end"])
        strip.extrapolation = "NOTHING"
    return sum(len(track.strips) for track in animation_data.nla_tracks)


def build_root_motion(arm):
    segments = TIMELINE.get("root_motion", [])
    if not segments:
        return 0.0
    action = bpy.data.actions.new("OYEN_ROOT_MOTION_JOB")
    action.use_fake_user = True
    arm.animation_data.action = action
    root = arm.pose.bones["CTRL_ROOT"]
    current_x = 0.0
    key_loc(root, 1, x=current_x)
    for segment in segments:
        key_loc(root, int(segment["frame_start"]), x=current_x)
        current_x += float(segment["delta_x"])
        key_loc(root, int(segment["frame_end"]), x=current_x)
    set_action_interpolation(action, "LINEAR")
    arm.animation_data.action = None
    track = arm.animation_data.nla_tracks.new()
    track.name = TIMELINE["tracks"]["root_motion"]
    strip = track.strips.new(action.name, 1, action)
    strip.frame_end = int(TIMELINE["frame_end"])
    strip.blend_type = "ADD"
    strip.extrapolation = "NOTHING"
    return current_x


def set_visible(obj, frame, visible):
    obj.hide_render = not bool(visible)
    obj.hide_viewport = not bool(visible)
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)


def active_face_names(expression):
    config = MANIFEST["face_sets"].get(expression, MANIFEST["face_sets"]["NEUTRAL"])
    result = set(config.get("eyes", []))
    if config.get("mouth"):
        result.add(config["mouth"])
    return result


def expression_at_frame(frame):
    current = "NEUTRAL"
    for event in TIMELINE.get("face_events", []):
        if event.get("kind") == "expression_swap" and int(event["frame_start"]) <= frame < int(event["frame_end"]):
            current = event["name"]
    return current


def build_face_animation(objects):
    face_objects = {
        item["name"]: objects[item["name"]]
        for item in MANIFEST["layers"]
        if item.get("group") == "face" and item.get("rig_enabled", True) and item["name"] in objects
    }
    neutral = active_face_names("NEUTRAL")
    for name, obj in face_objects.items():
        set_visible(obj, 1, name in neutral)
    for event in TIMELINE.get("face_events", []):
        if event.get("kind") != "expression_swap":
            continue
        frame = int(event["frame_start"])
        active = active_face_names(event["name"])
        for name, obj in face_objects.items():
            set_visible(obj, frame, name in active)
    closed = set(MANIFEST["face_sets"]["BLINK"]["eyes"])
    for event in TIMELINE.get("face_events", []):
        if event.get("kind") != "blink":
            continue
        start = int(event["frame_start"])
        close_frame = min(start + 1, int(TIMELINE["frame_end"]))
        open_frame = min(start + 3, int(TIMELINE["frame_end"]))
        expression = expression_at_frame(start)
        base = active_face_names(expression)
        for name, obj in face_objects.items():
            set_visible(obj, start, name in base)
            set_visible(obj, close_frame, name in (base - {n for n in base if n.startswith("eye_")}) or name in closed)
            set_visible(obj, open_frame, name in base)
    for obj in face_objects.values():
        if obj.animation_data and obj.animation_data.action:
            for curve in obj.animation_data.action.fcurves:
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"


def create_camera(root_end_x):
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Oyen_2D_Camera_Data")
    camera = bpy.data.objects.new("Oyen_2D_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    aspect = JOB["render"]["aspect_ratio"]
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 4.8 if aspect == "9:16" else (4.1 if aspect == "1:1" else 3.8)
    camera.location = (0.0, -10.0, 1.62)
    camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    camera.keyframe_insert(data_path="location", frame=1)
    if TIMELINE["camera"]["mode"] == "follow" and TIMELINE.get("root_motion"):
        current_x = 0.0
        for segment in TIMELINE["root_motion"]:
            camera.location.x = current_x
            camera.keyframe_insert(data_path="location", frame=int(segment["frame_start"]))
            current_x += float(segment["delta_x"])
            camera.location.x = current_x
            camera.keyframe_insert(data_path="location", frame=int(segment["frame_end"]))
    if camera.animation_data and camera.animation_data.action:
        for curve in camera.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
    scene.camera = camera
    return camera


def create_ground_shadow(arm):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=12, location=(0.0, 0.28, 0.13))
    shadow = bpy.context.object
    shadow.name = "Oyen_Ground_Shadow"
    shadow.scale = (0.72, 0.16, 0.075)
    material = bpy.data.materials.new("MAT_Oyen_Ground_Shadow")
    material.use_nodes = True
    set_alpha_mode(material)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    mix = nodes.new("ShaderNodeMixShader")
    emission.inputs["Color"].default_value = (0.08, 0.04, 0.02, 1.0)
    emission.inputs["Strength"].default_value = 0.7
    mix.inputs[0].default_value = 0.82
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    shadow.data.materials.append(material)
    world = shadow.matrix_world.copy()
    shadow.parent = arm
    shadow.parent_type = "BONE"
    shadow.parent_bone = "CTRL_ROOT"
    shadow.matrix_world = world
    return shadow


def configure_scene():
    scene = bpy.context.scene
    scene.frame_start = int(TIMELINE["frame_start"])
    scene.frame_end = int(TIMELINE["frame_end"])
    scene.render.fps = int(TIMELINE["fps"])
    scene.render.resolution_x = int(JOB["render"]["width"])
    scene.render.resolution_y = int(JOB["render"]["height"])
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.040, 0.025)
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.filepath = str(OUTPUT_DIR / "oyen_2d_preview.mp4")
    scene["oyen_2d_stage_audit"] = json.dumps(JOB["stage_audit"], ensure_ascii=False)
    scene["oyen_2d_motion_plan"] = json.dumps(PLAN, ensure_ascii=False)
    scene["oyen_2d_nla_timeline"] = json.dumps(TIMELINE, ensure_ascii=False)
    for name, value in (
        ("Oyen_2D_Stage_Audit.json", JOB["stage_audit"]),
        ("Oyen_2D_Motion_Plan.json", PLAN),
        ("Oyen_2D_NLA_Timeline.json", TIMELINE),
        ("Oyen_2D_Animation_Job.json", JOB),
    ):
        text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
        text.clear()
        text.write(json.dumps(value, ensure_ascii=False, indent=2))
    return scene


def render_qa(scene):
    frames = sorted(set([
        scene.frame_start,
        max(scene.frame_start, round(scene.frame_end * 0.25)),
        max(scene.frame_start, round(scene.frame_end * 0.50)),
        max(scene.frame_start, round(scene.frame_end * 0.75)),
        scene.frame_end,
    ]))
    while len(frames) < 5:
        frames.append(scene.frame_end)
    old_format = scene.render.image_settings.file_format
    old_path = scene.render.filepath
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    for index, frame in enumerate(frames[:5]):
        scene.frame_set(int(frame))
        scene.render.filepath = str(OUTPUT_DIR / f"qa_frame_{index:02d}_f{int(frame):04d}.png")
        bpy.ops.render.render(write_still=True)
    scene.render.image_settings.file_format = old_format
    scene.render.filepath = old_path
    return frames[:5]


clear_scene()
scene = configure_scene()
objects = {}
for layer in MANIFEST["layers"]:
    if layer.get("rig_enabled", True):
        objects[layer["name"]] = create_layer(layer)
armature = create_armature()
parent_layers(armature, objects)
actions = build_actions(armature)
nla_count = build_nla(armature)
root_end_x = build_root_motion(armature)
build_face_animation(objects)
create_camera(root_end_x)
create_ground_shadow(armature)
qa_frames = render_qa(scene)

blend_path = OUTPUT_DIR / "oyen_2d_preview.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
scene.render.image_settings.file_format = "FFMPEG"
scene.render.filepath = str(OUTPUT_DIR / "oyen_2d_preview.mp4")
scene.frame_set(scene.frame_start)
bpy.ops.render.render(animation=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

print(f"OYEN_2D_ASSETS count={len(objects)}")
print(f"OYEN_2D_BONES count={len(armature.data.bones)}")
print(f"OYEN_2D_ACTIONS count={len(actions)}")
print(f"OYEN_2D_NLA strips={nla_count}")
print(f"OYEN_2D_QA frames={len(qa_frames)}")
print("OYEN_2D_LIBRARY_ONLY true")
print("OYEN_2D_RENDER_SUCCESS")
print("OYEN_WORKER_SUCCESS")
'''
    return template.replace("__JOB_JSON__", repr(payload))
