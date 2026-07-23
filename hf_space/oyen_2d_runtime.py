from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from oyen_2d_asset_bundle import materialize_asset_zip, validate_asset_bundle
from oyen_2d_builder import build_2d_blender_script, validate_asset_pack


class Oyen2DRuntimeError(RuntimeError):
    """Raised when Blender cannot prove a complete Oyen 2D render."""


def find_blender() -> str:
    configured = os.environ.get("BLENDER_EXECUTABLE", "").strip()
    candidates = [
        configured,
        shutil.which("blender") or "",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise Oyen2DRuntimeError(
        "Blender tidak ditemukan. Pastikan hf_space/packages.txt berisi paket blender."
    )


def _tail(text: str, limit: int = 14_000) -> str:
    clean = (text or "").strip()
    return clean[-limit:] if len(clean) > limit else clean


def _validate_frame(path: Path) -> None:
    image = Image.open(path).convert("RGB")
    if image.width < 300 or image.height < 300:
        raise Oyen2DRuntimeError(f"Frame QA terlalu kecil: {path.name}")
    if max(ImageStat.Stat(image).var) < 35:
        raise Oyen2DRuntimeError(f"Frame QA terlihat kosong/datar: {path.name}")


def _contact_sheet(frames: list[Path], output: Path) -> Path:
    if len(frames) < 5:
        raise Oyen2DRuntimeError(f"Frame QA hanya {len(frames)}, wajib minimal lima")
    thumbs: list[Image.Image] = []
    thumb_width = 220
    for frame in frames[:5]:
        image = Image.open(frame).convert("RGB")
        ratio = thumb_width / max(1, image.width)
        thumbs.append(
            image.resize(
                (thumb_width, max(1, round(image.height * ratio))),
                Image.Resampling.LANCZOS,
            )
        )
    gap = 10
    width = thumb_width * len(thumbs) + gap * (len(thumbs) - 1)
    height = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (width, height), (244, 235, 216))
    x = 0
    for image in thumbs:
        sheet.paste(image, (x, 0))
        x += thumb_width + gap
    sheet.save(output, quality=92)
    return output


def _marker_count(log: str, label: str) -> int:
    match = re.search(rf"{re.escape(label)}\s+(?:count|strips|frames)=(\d+)", log)
    if not match:
        raise Oyen2DRuntimeError(f"Marker Blender tidak ditemukan: {label}")
    return int(match.group(1))


def _normalise_video_output(output_dir: Path, target: Path) -> tuple[Path, str]:
    """Create the exact MP4 expected by the Space across Blender/FFmpeg versions.

    Older Debian Blender builds may append a frame range and emit a Matroska file even
    when the configured render prefix ends in ``.mp4``. The frames and H.264 stream are
    valid, so this function remuxes that movie into the stable public MP4 filename.
    """
    if target.is_file() and target.stat().st_size >= 2_048:
        return target, "MP4_NORMALIZATION exact-output-present"

    supported_suffixes = {".mkv", ".mp4", ".mov", ".avi", ".webm"}
    candidates = [
        path
        for path in output_dir.glob("oyen_2d_preview*")
        if path.is_file()
        and path != target
        and path.suffix.lower() in supported_suffixes
        and path.stat().st_size >= 2_048
    ]
    if not candidates:
        generated = ", ".join(sorted(path.name for path in output_dir.iterdir()))
        raise Oyen2DRuntimeError(
            "Blender tidak menghasilkan movie yang dapat dinormalisasi. "
            f"Isi output: {generated}"
        )

    source = max(candidates, key=lambda path: path.stat().st_size)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise Oyen2DRuntimeError(
            f"Blender menghasilkan {source.name}, tetapi ffmpeg tidak ditemukan untuk membuat MP4"
        )

    attempts = [
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            "-an",
            str(target),
        ],
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            "-an",
            str(target),
        ],
    ]
    diagnostics: list[str] = []
    for index, command in enumerate(attempts, start=1):
        target.unlink(missing_ok=True)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        diagnostics.append(
            f"attempt={index} exit={completed.returncode} stderr={_tail(completed.stderr, 1800)}"
        )
        if completed.returncode == 0 and target.is_file() and target.stat().st_size >= 2_048:
            return (
                target,
                f"MP4_NORMALIZATION source={source.name} target={target.name} "
                + " | ".join(diagnostics),
            )

    raise Oyen2DRuntimeError(
        f"Gagal menormalisasi {source.name} menjadi MP4. " + " | ".join(diagnostics)
    )


def render_2d_job(
    job: dict[str, Any],
    output_root: str | Path,
    timeout: int = 420,
) -> dict[str, str | float | int]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    job_id = str(job.get("job_id", "oyen-2d-preview"))
    work_dir = root / job_id
    output_dir = work_dir / "oyen_2d_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    asset_zip = materialize_asset_zip(root / "_asset_cache")
    bundle_proof = validate_asset_bundle()
    pack_proof = validate_asset_pack(asset_zip)
    blender = find_blender()

    script_path = work_dir / "oyen_2d_scene.py"
    log_path = work_dir / "blender_2d.log"
    script_path.write_text(build_2d_blender_script(job), encoding="utf-8")

    env = os.environ.copy()
    env["OYEN_OUTPUT_DIR"] = str(output_dir.resolve())
    env["OYEN_2D_ASSET_ZIP"] = str(asset_zip.resolve())
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
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
            encoding="utf-8",
        )
        raise Oyen2DRuntimeError(
            f"Render Blender 2D melewati batas {timeout} detik."
        ) from exc

    elapsed = time.monotonic() - started
    log = (
        f"COMMAND: {' '.join(command)}\n"
        f"EXIT_CODE: {completed.returncode}\n"
        f"ELAPSED_SECONDS: {elapsed:.2f}\n\n"
        f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
    )
    log_path.write_text(log, encoding="utf-8")

    required_markers = (
        "OYEN_2D_LIBRARY_ONLY true",
        "OYEN_2D_RENDER_SUCCESS",
        "OYEN_WORKER_SUCCESS",
    )
    if completed.returncode != 0 or any(
        marker not in completed.stdout for marker in required_markers
    ):
        raise Oyen2DRuntimeError(
            "Blender gagal membuktikan pipeline Oyen 2D Tahap 1–7.\n"
            + _tail(completed.stderr or completed.stdout)
        )

    active_layers = _marker_count(completed.stdout, "OYEN_2D_ASSETS")
    bone_count = _marker_count(completed.stdout, "OYEN_2D_BONES")
    action_count = _marker_count(completed.stdout, "OYEN_2D_ACTIONS")
    nla_strip_count = _marker_count(completed.stdout, "OYEN_2D_NLA")
    qa_count = _marker_count(completed.stdout, "OYEN_2D_QA")
    if active_layers < 35 or bone_count < 25 or action_count != 7 or qa_count < 5:
        raise Oyen2DRuntimeError(
            "Jumlah bukti Blender tidak memenuhi gate: "
            f"layer={active_layers}, bone={bone_count}, action={action_count}, qa={qa_count}"
        )

    video_path = output_dir / "oyen_2d_preview.mp4"
    video_path, normalisation_log = _normalise_video_output(output_dir, video_path)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n\n{normalisation_log}\n")

    blend_path = output_dir / "oyen_2d_preview.blend"
    if not video_path.is_file() or video_path.stat().st_size < 2_048:
        raise Oyen2DRuntimeError("MP4 Oyen 2D tidak ditemukan atau terlalu kecil")
    if not blend_path.is_file() or blend_path.stat().st_size < 10_000:
        raise Oyen2DRuntimeError("File .blend Oyen 2D tidak ditemukan atau terlalu kecil")

    qa_frames = sorted(output_dir.glob("qa_frame_*.png"))
    if len(qa_frames) < 5:
        raise Oyen2DRuntimeError(f"Blender hanya menghasilkan {len(qa_frames)} frame QA")
    for frame in qa_frames[:5]:
        _validate_frame(frame)
    contact_sheet = _contact_sheet(
        qa_frames,
        output_dir / "oyen_2d_qa_contact_sheet.jpg",
    )
    if contact_sheet.stat().st_size < 2_000:
        raise Oyen2DRuntimeError("Contact sheet QA terlalu kecil")

    return {
        "video": str(video_path),
        "blend": str(blend_path),
        "contact_sheet": str(contact_sheet),
        "script": str(script_path),
        "log": str(log_path),
        "elapsed_seconds": elapsed,
        "video_size_bytes": video_path.stat().st_size,
        "blend_size_bytes": blend_path.stat().st_size,
        "active_layer_count": active_layers,
        "bone_count": bone_count,
        "action_count": action_count,
        "nla_strip_count": nla_strip_count,
        "qa_frame_count": qa_count,
        "asset_zip_png_count": int(pack_proof["png_count"]),
        "asset_zip_bytes": int(bundle_proof["zip_bytes"]),
    }
