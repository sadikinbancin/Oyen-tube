from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "oyen.2d-motion-plan.v1"
CHARACTER_NAME = "Oyen Purba 2D Test V1"
DEFAULT_FPS = 12

TRACKS = {
    "base": "01_BASE",
    "locomotion": "02_LOCOMOTION",
    "upper_overlay": "03_UPPER_BODY",
    "face_overlay": "04_FACE",
    "tail_overlay": "05_TAIL",
    "root_motion": "06_ROOT_MOTION",
    "camera": "07_CAMERA",
}

ACTION_LIBRARY: dict[str, dict[str, Any]] = {
    "OYEN_IDLE": {
        "duration_frames": 24,
        "loop": True,
        "track": "base",
        "blend": "REPLACE",
        "root_speed_limit": 0.0,
    },
    "OYEN_BLINK": {
        "duration_frames": 6,
        "loop": False,
        "track": "face_overlay",
        "blend": "REPLACE",
        "root_speed_limit": 0.0,
    },
    "OYEN_WALK_IN_PLACE": {
        "duration_frames": 12,
        "loop": True,
        "track": "locomotion",
        "blend": "REPLACE",
        "root_speed_limit": 0.7,
    },
    "OYEN_RUN_IN_PLACE": {
        "duration_frames": 8,
        "loop": True,
        "track": "locomotion",
        "blend": "REPLACE",
        "root_speed_limit": 1.3,
    },
    "OYEN_HEAD_TURN": {
        "duration_frames": 12,
        "loop": False,
        "track": "upper_overlay",
        "blend": "COMBINE",
        "root_speed_limit": 0.0,
    },
    "OYEN_WAVE": {
        "duration_frames": 24,
        "loop": False,
        "track": "upper_overlay",
        "blend": "COMBINE",
        "root_speed_limit": 0.0,
    },
    "OYEN_TAIL_WAG": {
        "duration_frames": 24,
        "loop": True,
        "track": "tail_overlay",
        "blend": "COMBINE",
        "root_speed_limit": 0.0,
    },
}

ALLOWED_EXPRESSIONS = {"NEUTRAL", "HAPPY", "ANGRY", "SURPRISED"}
ALLOWED_DIRECTIONS = {"left", "right", "none", "camera"}
AVAILABLE_SCENE_ASSETS = {"oyen"}
KNOWN_TARGETS = {
    "ayam": "chicken",
    "ikan": "fish",
    "burung": "bird",
    "tikus": "mouse",
}
FORBIDDEN_KEYS = {"python", "script", "code", "bpy", "shell", "command"}


class MotionPlanError(ValueError):
    """Raised when an AI motion plan violates the safe 2D action contract."""


def _contains_any(text: str, words: Iterable[str]) -> bool:
    return any(word in text for word in words)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def seconds_to_frame(seconds: float, fps: int = DEFAULT_FPS) -> int:
    if fps <= 0:
        raise MotionPlanError("FPS harus lebih besar dari nol")
    return max(1, round(float(seconds) * fps) + 1)


def _clip(
    action: str,
    start: float,
    end: float,
    *,
    direction: str = "none",
    distance: float = 0.0,
    intensity: float = 0.65,
) -> dict[str, Any]:
    meta = ACTION_LIBRARY[action]
    return {
        "action": action,
        "start": round(start, 3),
        "end": round(end, 3),
        "track": meta["track"],
        "direction": direction,
        "distance": round(distance, 3),
        "intensity": round(_clamp(intensity, 0.0, 1.0), 3),
    }


def _target_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    for indonesian_name, asset_name in KNOWN_TARGETS.items():
        if indonesian_name in text and asset_name not in AVAILABLE_SCENE_ASSETS:
            warnings.append(
                f"Aset {indonesian_name} belum tersedia; Oyen diarahkan ke target di luar layar, "
                "bukan dibuat sebagai karakter palsu."
            )
    return warnings


def build_2d_motion_plan(prompt: str, duration: float, fps: int = DEFAULT_FPS) -> dict[str, Any]:
    """Convert an Indonesian prompt into a deterministic, library-only 2D motion plan.

    This local parser is deliberately conservative. A remote LLM may fill the same schema,
    but every returned plan must still pass :func:`validate_2d_motion_plan`.
    """

    clean_prompt = re.sub(r"\s+", " ", (prompt or "").strip())
    if len(clean_prompt) < 3:
        raise MotionPlanError("Prompt terlalu pendek")
    duration = _clamp(float(duration), 1.0, 12.0)
    if fps not in {12, 15, 24}:
        raise MotionPlanError("FPS 2D yang didukung: 12, 15, atau 24")

    text = clean_prompt.lower()
    clips: list[dict[str, Any]] = []
    expressions: list[dict[str, Any]] = []

    wants_run = _contains_any(text, ("berlari", "lari", "mengejar"))
    wants_walk = _contains_any(text, ("berjalan", "jalan", "melangkah")) and not wants_run
    wants_wave = _contains_any(text, ("melambai", "melambaikan", "dadah"))
    wants_look = _contains_any(text, ("menoleh", "melihat kamera", "menatap kamera", "lihat kamera"))
    wants_tail = _contains_any(text, ("ekor", "mengibaskan", "kibas"))

    locomotion_end = duration * (0.58 if wants_run or wants_walk else 0.34)
    if wants_run:
        distance = min(1.3 * locomotion_end, max(0.8, duration * 0.62))
        clips.append(
            _clip(
                "OYEN_RUN_IN_PLACE",
                0.0,
                locomotion_end,
                direction="right",
                distance=distance,
                intensity=0.88,
            )
        )
    elif wants_walk:
        distance = min(0.7 * locomotion_end, max(0.4, duration * 0.28))
        clips.append(
            _clip(
                "OYEN_WALK_IN_PLACE",
                0.0,
                locomotion_end,
                direction="right",
                distance=distance,
                intensity=0.64,
            )
        )
    else:
        clips.append(_clip("OYEN_IDLE", 0.0, duration, intensity=0.45))

    settle_start = locomotion_end if wants_run or wants_walk else 0.0
    if wants_run or wants_walk:
        clips.append(_clip("OYEN_IDLE", settle_start, duration, intensity=0.42))

    overlay_cursor = min(duration * 0.48, max(0.2, settle_start))
    if wants_look:
        look_end = min(duration, overlay_cursor + min(1.0, duration * 0.2))
        clips.append(
            _clip(
                "OYEN_HEAD_TURN",
                overlay_cursor,
                look_end,
                direction="camera",
                intensity=0.68,
            )
        )
        overlay_cursor = look_end

    if wants_wave:
        wave_start = min(duration - 0.35, max(overlay_cursor, duration * 0.52))
        wave_end = min(duration, wave_start + min(2.0, duration * 0.35))
        if wave_end > wave_start:
            clips.append(_clip("OYEN_WAVE", wave_start, wave_end, intensity=0.72))

    if wants_tail or _contains_any(text, ("senang", "gembira", "tersenyum")):
        tail_start = min(duration - 0.3, max(0.0, duration * 0.36))
        clips.append(_clip("OYEN_TAIL_WAG", tail_start, duration, intensity=0.56))

    if _contains_any(text, ("marah", "kesal", "geram")):
        expression_start = min(duration * 0.68, max(0.0, settle_start))
        if expression_start > 0:
            expressions.append({"name": "NEUTRAL", "start": 0.0, "end": expression_start})
        expressions.append({"name": "ANGRY", "start": expression_start, "end": duration})
    elif _contains_any(text, ("terkejut", "kaget")):
        expression_start = min(duration * 0.6, max(0.0, settle_start))
        if expression_start > 0:
            expressions.append({"name": "NEUTRAL", "start": 0.0, "end": expression_start})
        expressions.append({"name": "SURPRISED", "start": expression_start, "end": duration})
    elif _contains_any(text, ("senang", "gembira", "tersenyum", "tertawa")):
        expressions.append({"name": "HAPPY", "start": 0.0, "end": duration})
    else:
        expressions.append({"name": "NEUTRAL", "start": 0.0, "end": duration})

    blink_times: list[float] = []
    if not any(item["name"] == "SURPRISED" for item in expressions):
        if duration >= 2.2:
            blink_times.append(round(min(duration - 0.35, duration * 0.31), 3))
        if duration >= 5.8:
            blink_times.append(round(min(duration - 0.35, duration * 0.76), 3))

    plan = {
        "schema_version": SCHEMA_VERSION,
        "character": CHARACTER_NAME,
        "prompt": clean_prompt,
        "duration_seconds": round(duration, 3),
        "fps": fps,
        "clips": clips,
        "expressions": expressions,
        "blinks": [{"time": time_value} for time_value in blink_times],
        "camera": {
            "mode": "follow" if wants_run or wants_walk else "locked",
            "shot": "medium",
            "keep_character_visible": True,
            "safe_margin": 0.15,
        },
        "warnings": _target_warnings(text),
        "safety": {
            "library_only": True,
            "arbitrary_python_allowed": False,
            "missing_assets_use_offscreen_target": True,
        },
    }
    validate_2d_motion_plan(plan)
    return plan


def _walk_values(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)


def validate_2d_motion_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise MotionPlanError("Motion plan harus berupa object JSON")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise MotionPlanError(f"Schema harus {SCHEMA_VERSION}")

    for key, _ in _walk_values(plan):
        if key.lower() in FORBIDDEN_KEYS:
            raise MotionPlanError(f"Field berbahaya tidak diizinkan: {key}")

    duration = float(plan.get("duration_seconds", 0))
    fps = int(plan.get("fps", 0))
    if not 1.0 <= duration <= 12.0:
        raise MotionPlanError("Durasi harus 1–12 detik")
    if fps not in {12, 15, 24}:
        raise MotionPlanError("FPS tidak didukung")

    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        raise MotionPlanError("Motion plan harus memiliki minimal satu Action")

    locomotion_ranges: list[tuple[float, float, str]] = []
    for clip in clips:
        if not isinstance(clip, dict):
            raise MotionPlanError("Setiap clip harus berupa object")
        action = str(clip.get("action", ""))
        if action not in ACTION_LIBRARY:
            raise MotionPlanError(f"Action tidak diizinkan: {action}")
        meta = ACTION_LIBRARY[action]
        if clip.get("track") != meta["track"]:
            raise MotionPlanError(f"Track salah untuk {action}")
        start = float(clip.get("start", -1))
        end = float(clip.get("end", -1))
        if not 0.0 <= start < end <= duration:
            raise MotionPlanError(f"Waktu clip tidak valid: {action} {start}–{end}")
        intensity = float(clip.get("intensity", -1))
        if not 0.0 <= intensity <= 1.0:
            raise MotionPlanError(f"Intensity tidak valid: {action}")
        direction = str(clip.get("direction", "none"))
        if direction not in ALLOWED_DIRECTIONS:
            raise MotionPlanError(f"Direction tidak valid: {direction}")
        distance = float(clip.get("distance", 0.0))
        clip_seconds = end - start
        max_distance = float(meta["root_speed_limit"]) * clip_seconds + 1e-6
        if distance < 0 or distance > max_distance:
            raise MotionPlanError(
                f"Root distance {distance} melampaui batas {max_distance:.3f} untuk {action}"
            )
        if meta["track"] == "locomotion":
            locomotion_ranges.append((start, end, action))

    locomotion_ranges.sort()
    for previous, current in zip(locomotion_ranges, locomotion_ranges[1:]):
        if current[0] < previous[1] - 1e-6:
            raise MotionPlanError(
                f"Locomotion bertabrakan: {previous[2]} dan {current[2]}"
            )

    expressions = plan.get("expressions", [])
    last_end = 0.0
    for expression in expressions:
        name = str(expression.get("name", ""))
        if name not in ALLOWED_EXPRESSIONS:
            raise MotionPlanError(f"Ekspresi tidak diizinkan: {name}")
        start = float(expression.get("start", -1))
        end = float(expression.get("end", -1))
        if not 0.0 <= start < end <= duration:
            raise MotionPlanError(f"Waktu ekspresi tidak valid: {name}")
        if start < last_end - 1e-6:
            raise MotionPlanError("Ekspresi tidak boleh bertumpuk")
        last_end = end

    previous_blink = -99.0
    for blink in plan.get("blinks", []):
        blink_time = float(blink.get("time", -1))
        if not 0.0 < blink_time < duration:
            raise MotionPlanError("Waktu blink berada di luar durasi")
        if blink_time - previous_blink < 1.2:
            raise MotionPlanError("Jarak antarblink minimal 1,2 detik")
        previous_blink = blink_time

    camera = plan.get("camera", {})
    if camera.get("keep_character_visible") is not True:
        raise MotionPlanError("Kamera wajib menjaga Oyen tetap terlihat")
    safe_margin = float(camera.get("safe_margin", 0.0))
    if not 0.1 <= safe_margin <= 0.3:
        raise MotionPlanError("Safe margin kamera harus 0,10–0,30")

    safety = plan.get("safety", {})
    if safety.get("library_only") is not True:
        raise MotionPlanError("Motion plan wajib library-only")
    if safety.get("arbitrary_python_allowed") is not False:
        raise MotionPlanError("Python bebas tidak diizinkan")
    return plan


def compile_nla_timeline(plan: dict[str, Any]) -> dict[str, Any]:
    """Compile a validated plan into deterministic NLA/root/camera/layer events."""

    validate_2d_motion_plan(plan)
    fps = int(plan["fps"])
    duration = float(plan["duration_seconds"])
    strips: list[dict[str, Any]] = []
    root_segments: list[dict[str, Any]] = []

    for clip in plan["clips"]:
        action = clip["action"]
        meta = ACTION_LIBRARY[action]
        start_frame = seconds_to_frame(clip["start"], fps)
        end_frame = max(start_frame + 1, seconds_to_frame(clip["end"], fps))
        requested_length = end_frame - start_frame
        action_length = int(meta["duration_frames"])
        repeat = requested_length / max(1, action_length)
        if not meta["loop"]:
            repeat = 1.0
        strips.append(
            {
                "track": TRACKS[meta["track"]],
                "action": action,
                "frame_start": start_frame,
                "frame_end": end_frame,
                "repeat": round(max(1.0, repeat), 4),
                "blend_type": meta["blend"],
                "influence": round(float(clip["intensity"]), 3),
            }
        )
        if float(clip.get("distance", 0.0)) > 0:
            direction_sign = -1.0 if clip.get("direction") == "left" else 1.0
            root_segments.append(
                {
                    "bone": "CTRL_ROOT",
                    "frame_start": start_frame,
                    "frame_end": end_frame,
                    "delta_x": round(float(clip["distance"]) * direction_sign, 4),
                    "interpolation": "LINEAR",
                }
            )

    face_events: list[dict[str, Any]] = []
    for expression in plan.get("expressions", []):
        face_events.append(
            {
                "kind": "expression_swap",
                "name": expression["name"],
                "frame_start": seconds_to_frame(expression["start"], fps),
                "frame_end": seconds_to_frame(expression["end"], fps),
                "interpolation": "CONSTANT",
            }
        )
    for blink in plan.get("blinks", []):
        blink_frame = seconds_to_frame(blink["time"], fps)
        face_events.append(
            {
                "kind": "blink",
                "action": "OYEN_BLINK",
                "frame_start": blink_frame,
                "frame_end": blink_frame + ACTION_LIBRARY["OYEN_BLINK"]["duration_frames"],
                "interpolation": "CONSTANT",
            }
        )

    return {
        "schema_version": "oyen.2d-nla-timeline.v1",
        "character": CHARACTER_NAME,
        "fps": fps,
        "frame_start": 1,
        "frame_end": seconds_to_frame(duration, fps),
        "tracks": deepcopy(TRACKS),
        "strips": strips,
        "root_motion": root_segments,
        "face_events": face_events,
        "camera": {
            "mode": plan["camera"]["mode"],
            "target": "CTRL_ROOT",
            "orthographic": True,
            "keep_character_visible": True,
            "safe_margin": plan["camera"]["safe_margin"],
        },
        "warnings": list(plan.get("warnings", [])),
    }


def build_blender_nla_script(plan: dict[str, Any]) -> str:
    """Return a standalone Blender compiler script for an existing 2D rig/action file.

    The generated script never contains model-authored Python. It is a fixed template with
    validated JSON data embedded as a literal.
    """

    timeline = compile_nla_timeline(plan)
    plan_json = json.dumps(plan, ensure_ascii=False, sort_keys=True)
    timeline_json = json.dumps(timeline, ensure_ascii=False, sort_keys=True)
    return f'''from __future__ import annotations

import json
import bpy

PLAN = json.loads({plan_json!r})
TIMELINE = json.loads({timeline_json!r})
ARMATURE_NAME = "Oyen_Purba_2D_Rig"
ROOT_BONE = "CTRL_ROOT"

armature = bpy.data.objects.get(ARMATURE_NAME)
if armature is None or armature.type != "ARMATURE":
    raise RuntimeError("Oyen_Purba_2D_Rig belum tersedia")

animation_data = armature.animation_data_create()
for track in list(animation_data.nla_tracks):
    animation_data.nla_tracks.remove(track)

track_map = {{}}
for track_name in TIMELINE["tracks"].values():
    track = animation_data.nla_tracks.new()
    track.name = track_name
    track_map[track_name] = track

for item in TIMELINE["strips"]:
    action = bpy.data.actions.get(item["action"])
    if action is None:
        raise RuntimeError(f"Action tidak ditemukan: {{item['action']}}")
    strip = track_map[item["track"]].strips.new(
        item["action"], item["frame_start"], action
    )
    strip.frame_end = item["frame_end"]
    strip.repeat = item["repeat"]
    strip.blend_type = item["blend_type"]
    strip.influence = item["influence"]
    strip.extrapolation = "NOTHING"

root = armature.pose.bones.get(ROOT_BONE)
if root is None:
    raise RuntimeError("CTRL_ROOT tidak ditemukan")
root_x = float(root.location.x)
for segment in TIMELINE["root_motion"]:
    root.location.x = root_x
    root.keyframe_insert(data_path="location", frame=segment["frame_start"])
    root_x += segment["delta_x"]
    root.location.x = root_x
    root.keyframe_insert(data_path="location", frame=segment["frame_end"])

scene = bpy.context.scene
scene.render.fps = TIMELINE["fps"]
scene.frame_start = TIMELINE["frame_start"]
scene.frame_end = TIMELINE["frame_end"]
scene["oyen_2d_motion_plan"] = json.dumps(PLAN, ensure_ascii=False)
scene["oyen_2d_nla_timeline"] = json.dumps(TIMELINE, ensure_ascii=False)

text = bpy.data.texts.get("Oyen_2D_Motion_Plan.json") or bpy.data.texts.new("Oyen_2D_Motion_Plan.json")
text.clear()
text.write(json.dumps(PLAN, ensure_ascii=False, indent=2))

print(f"OYEN_2D_NLA_SUCCESS strips={{len(TIMELINE['strips'])}}")
print("OYEN_2D_LIBRARY_ONLY true")
'''


def load_motion_library(path: str | Path) -> dict[str, Any]:
    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    if parsed.get("schema_version") != "oyen.2d-motion-library.v1":
        raise MotionPlanError("Motion library schema tidak valid")
    actions = parsed.get("actions", {})
    if set(actions) != set(ACTION_LIBRARY):
        raise MotionPlanError("Isi motion library tidak sama dengan kontrak Action")
    return parsed
