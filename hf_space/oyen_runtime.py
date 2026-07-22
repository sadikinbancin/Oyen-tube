from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from oyen_bridge import build_blender_script


class BlenderRuntimeError(RuntimeError):
    """Raised when Blender cannot create a valid Oyen preview."""


def find_blender() -> str:
    """Locate Blender installed by packages.txt or an explicit environment variable."""
    configured = os.getenv("BLENDER_EXECUTABLE", "").strip()
    candidates = [
        configured,
        shutil.which("blender") or "",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise BlenderRuntimeError(
        "Blender tidak ditemukan di Space. Pastikan packages.txt berisi paket 'blender'."
    )


def _tail(text: str, limit: int = 6000) -> str:
    clean = (text or "").strip()
    return clean[-limit:] if len(clean) > limit else clean


def _prepare_script(job: dict[str, Any]) -> str:
    """Adapt the portable worker script for the Hugging Face runtime."""
    script = build_blender_script(job)
    script = script.replace(
        'OUTPUT_ROOT = os.path.abspath("//oyen_output")',
        'OUTPUT_ROOT = os.path.abspath(os.environ.get("OYEN_OUTPUT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "oyen_output")))',
    )
    script = script.replace(
        "scene.render.resolution_percentage = 50",
        'scene.render.resolution_percentage = int(render.get("preview_resolution_percentage", 50))',
    )
    old_engine_block = '''    preferred_engine = str(render.get("engine", "BLENDER_EEVEE_NEXT"))
    available_engines = {"BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH", "CYCLES"}
    scene.render.engine = preferred_engine if preferred_engine in available_engines else "BLENDER_EEVEE_NEXT"'''
    new_engine_block = '''    preferred_engine = str(render.get("engine", "BLENDER_EEVEE_NEXT"))
    engine_candidates = [preferred_engine, "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"]
    for engine_name in engine_candidates:
        try:
            scene.render.engine = engine_name
            break
        except Exception:
            continue'''
    script = script.replace(old_engine_block, new_engine_block)
    return script


def render_job(
    job: dict[str, Any],
    output_root: str | Path,
    timeout: int = 180,
) -> dict[str, str | float]:
    """Generate a Blender script, run Blender headlessly, and return a validated MP4 path."""
    blender = find_blender()
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    job_id = str(job.get("job_id", "oyen-preview"))
    work_dir = root / job_id
    output_dir = work_dir / "oyen_output"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_path = work_dir / "oyen_blender_scene.py"
    log_path = work_dir / "blender.log"
    script_path.write_text(_prepare_script(job), encoding="utf-8")

    env = os.environ.copy()
    env["OYEN_OUTPUT_DIR"] = str(output_dir.resolve())
    env["BLENDER_USER_CONFIG"] = str((work_dir / "blender_config").resolve())
    env["BLENDER_USER_SCRIPTS"] = str((work_dir / "blender_scripts").resolve())
    env["BLENDER_USER_DATAFILES"] = str((work_dir / "blender_data").resolve())

    command = [
        blender,
        "--background",
        "--factory-startup",
        "--enable-autoexec",
        "--python",
        str(script_path.resolve()),
    ]

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(work_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        partial_stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        partial_stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\n\nSTDOUT:\n{partial_stdout}\n\nSTDERR:\n{partial_stderr}",
            encoding="utf-8",
        )
        raise BlenderRuntimeError(
            f"Render Blender melewati batas {timeout} detik. Gunakan durasi atau resolusi lebih kecil."
        ) from exc

    elapsed = time.monotonic() - started
    combined_log = (
        f"COMMAND: {' '.join(command)}\n"
        f"EXIT_CODE: {completed.returncode}\n"
        f"ELAPSED_SECONDS: {elapsed:.2f}\n\n"
        f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
    )
    log_path.write_text(combined_log, encoding="utf-8")

    if completed.returncode != 0 or "OYEN_WORKER_SUCCESS" not in completed.stdout:
        details = _tail(completed.stderr or completed.stdout)
        raise BlenderRuntimeError(f"Blender gagal merender preview. Log terakhir:\n{details}")

    video_path = output_dir / "oyen_preview.mp4"
    blend_path = output_dir / "oyen_preview.blend"
    if not video_path.is_file():
        alternatives = sorted(output_dir.glob("*.mp4"))
        if alternatives:
            video_path = alternatives[0]

    if not video_path.is_file() or video_path.stat().st_size < 1024:
        raise BlenderRuntimeError(
            "Blender selesai tetapi file MP4 tidak ditemukan atau kosong. Periksa blender.log."
        )

    return {
        "video": str(video_path),
        "blend": str(blend_path) if blend_path.is_file() else "",
        "script": str(script_path),
        "log": str(log_path),
        "elapsed_seconds": elapsed,
        "video_size_bytes": float(video_path.stat().st_size),
    }
