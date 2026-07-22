from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from oyen_bridge import build_blender_script


class BlenderRuntimeError(RuntimeError):
    """Raised when Blender cannot create a valid rigged Oyen preview."""


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


def _tail(text: str, limit: int = 7000) -> str:
    clean = (text or "").strip()
    return clean[-limit:] if len(clean) > limit else clean


def _prepare_script(job: dict[str, Any]) -> str:
    """Generate the portable Blender script; output paths are environment-aware."""
    return build_blender_script(job)


def render_job(
    job: dict[str, Any],
    output_root: str | Path,
    timeout: int = 300,
) -> dict[str, str | float]:
    """Run Blender headlessly and validate MP4, .blend, and the armature marker."""
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

    success_marker = "OYEN_WORKER_SUCCESS" in completed.stdout
    rig_match = re.search(r"OYEN_RIG_READY\s+bones=(\d+)", completed.stdout)
    if completed.returncode != 0 or not success_marker or not rig_match:
        details = _tail(completed.stderr or completed.stdout)
        raise BlenderRuntimeError(
            "Blender belum membuktikan bahwa armature Oyen Purba berhasil dibuat. "
            f"Log terakhir:\n{details}"
        )

    bone_count = int(rig_match.group(1))
    if bone_count < 20:
        raise BlenderRuntimeError(
            f"Armature terdeteksi tetapi hanya memiliki {bone_count} tulang; minimal 20 tulang."
        )

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
    if not blend_path.is_file() or blend_path.stat().st_size < 4096:
        raise BlenderRuntimeError(
            "MP4 ada, tetapi file .blend yang berisi armature tidak ditemukan atau kosong."
        )

    return {
        "video": str(video_path),
        "blend": str(blend_path),
        "script": str(script_path),
        "log": str(log_path),
        "elapsed_seconds": elapsed,
        "video_size_bytes": float(video_path.stat().st_size),
        "blend_size_bytes": float(blend_path.stat().st_size),
        "rig_bone_count": float(bone_count),
    }
