from __future__ import annotations

import copy
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from oyen_bridge import build_blender_script


class BlenderRenderError(RuntimeError):
    """Raised when the headless Blender render does not produce a usable MP4."""


def make_preview_job(job: dict[str, Any]) -> dict[str, Any]:
    """Create a lightweight render job while preserving the full worker package job."""
    preview = copy.deepcopy(job)
    timeline = preview["timeline"]
    render = preview["render"]

    requested_duration = max(1, int(timeline.get("duration_seconds", 5)))
    requested_fps = max(1, int(timeline.get("fps", 12)))
    preview_duration = min(requested_duration, 15)
    preview_fps = min(requested_fps, 12)

    original_scenes = list(timeline.get("scenes", []))
    scene_count = max(1, min(len(original_scenes) or 1, 4))
    scene_length = preview_duration / scene_count
    preview_scenes: list[dict[str, Any]] = []

    if not original_scenes:
        original_scenes = [
            {
                "scene": 1,
                "action": preview.get("project", {}).get("prompt", "Oyen bergerak di dalam adegan."),
                "camera": "wide establishing shot",
                "animation_note": "Procedural preview animation.",
            }
        ]

    for index in range(scene_count):
        source = copy.deepcopy(original_scenes[index % len(original_scenes)])
        source["scene"] = index + 1
        source["start_seconds"] = round(index * scene_length, 3)
        source["end_seconds"] = round(min(preview_duration, (index + 1) * scene_length), 3)
        preview_scenes.append(source)

    timeline["duration_seconds"] = preview_duration
    timeline["fps"] = preview_fps
    timeline["total_frames"] = max(2, preview_duration * preview_fps)
    timeline["scenes"] = preview_scenes

    render["preview_resolution_percentage"] = min(
        int(render.get("preview_resolution_percentage", 50)), 35
    )
    preview["status"] = "direct_mp4_preview_ready"
    preview.setdefault("notes", []).append(
        "Direct Space render is capped at 15 seconds, 12 FPS, and 35% resolution for free-tier reliability."
    )
    return preview


def _resolve_blender() -> str:
    configured = os.environ.get("BLENDER_EXECUTABLE", "blender")
    if os.path.isabs(configured) and os.path.isfile(configured):
        return configured
    resolved = shutil.which(configured)
    if not resolved:
        raise BlenderRenderError(
            "Blender tidak ditemukan di runtime. Pastikan packages.txt berisi paket blender."
        )
    return resolved


def render_mp4(
    job: dict[str, Any],
    output_dir: str | Path,
    timeout_seconds: int = 300,
) -> dict[str, str]:
    """Run Blender headlessly and return paths to the generated MP4, BLEND and log."""
    blender = _resolve_blender()
    preview_job = make_preview_job(job)
    root = Path(output_dir) / str(job.get("job_id", "oyen-job"))
    render_root = root / "oyen_output"
    root.mkdir(parents=True, exist_ok=True)
    render_root.mkdir(parents=True, exist_ok=True)

    script_path = root / "oyen_blender_scene.py"
    log_path = root / "blender_render.log"
    script_path.write_text(build_blender_script(preview_job), encoding="utf-8")

    env = os.environ.copy()
    env["OYEN_OUTPUT_DIR"] = str(render_root.resolve())
    command = [
        blender,
        "--background",
        "--factory-startup",
        "--enable-autoexec",
        "--python",
        str(script_path.resolve()),
    ]

    try:
        result = subprocess.run(
            command,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BlenderRenderError(
            f"Render Blender melewati batas {timeout_seconds} detik. Coba durasi lebih pendek."
        ) from exc

    log_text = (
        f"COMMAND: {' '.join(command)}\n\n"
        f"RETURN CODE: {result.returncode}\n\n"
        f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n"
    )
    log_path.write_text(log_text, encoding="utf-8")

    video_path = render_root / "oyen_preview.mp4"
    blend_path = render_root / "oyen_preview.blend"
    success_marker = "OYEN_WORKER_SUCCESS" in result.stdout

    if result.returncode != 0 or not success_marker:
        tail = (result.stderr or result.stdout)[-1800:]
        raise BlenderRenderError(f"Blender gagal merender MP4. Log terakhir: {tail}")
    if not video_path.exists() or video_path.stat().st_size < 1024:
        raise BlenderRenderError("Blender selesai tetapi file MP4 tidak ditemukan atau kosong.")
    if not blend_path.exists():
        raise BlenderRenderError("File .blend hasil render tidak ditemukan.")

    return {
        "video": str(video_path),
        "blend": str(blend_path),
        "log": str(log_path),
        "script": str(script_path),
    }
