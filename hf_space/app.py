from __future__ import annotations

import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gradio as gr
import spaces

from oyen_runtime import BlenderRuntimeError, render_job

APP_VERSION = "0.3.0"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "oyen_animation_jobs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE_PRESETS: dict[str, dict[str, str]] = {
    "Oyen Cartoon": {
        "look": "friendly stylized cartoon, expressive face, clean shapes",
        "lighting": "soft cinematic daylight",
    },
    "Drama China Modern": {
        "look": "modern vertical drama, elegant interior, cinematic expressions",
        "lighting": "soft key light with dramatic rim light",
    },
    "Anime": {
        "look": "anime-inspired character acting, clean outlines, expressive poses",
        "lighting": "bright cel-shaded cinematic lighting",
    },
    "Semi-realistic 3D": {
        "look": "polished semi-realistic 3D animation with stable character design",
        "lighting": "cinematic three-point lighting",
    },
}

RESOLUTIONS: dict[tuple[str, str], tuple[int, int]] = {
    ("9:16", "360p cepat"): (360, 640),
    ("9:16", "480p"): (480, 854),
    ("16:9", "360p cepat"): (640, 360),
    ("16:9", "480p"): (854, 480),
    ("1:1", "360p cepat"): (360, 360),
    ("1:1", "480p"): (480, 480),
}


def _sentences(prompt: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", prompt.strip())
    return [part.strip(" -") for part in parts if part.strip(" -")]


def _build_scenes(prompt: str, duration: int, mode: str) -> list[dict[str, Any]]:
    pieces = _sentences(prompt) or [prompt]
    scene_count = max(1, min(4, round(duration / 2)))
    scene_length = duration / scene_count
    scenes: list[dict[str, Any]] = []

    for index in range(scene_count):
        start = round(index * scene_length, 2)
        end = round(min(duration, (index + 1) * scene_length), 2)
        scenes.append(
            {
                "scene": index + 1,
                "start_seconds": start,
                "end_seconds": end,
                "action": pieces[index % len(pieces)],
                "camera": [
                    "wide establishing shot",
                    "medium character shot",
                    "close-up reaction",
                ][index % 3],
                "animation_note": (
                    "Use Grease Pencil layers and pose-to-pose timing."
                    if mode == "2D Grease Pencil"
                    else "Use smooth body, head, tail, and camera keyframes."
                ),
            }
        )
    return scenes


def _create_job(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> dict[str, Any]:
    width, height = RESOLUTIONS[(aspect_ratio, resolution)]
    preset = STYLE_PRESETS[style]
    job_id = f"oyen-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    return {
        "schema_version": "oyen.animation-job.v3",
        "app_version": APP_VERSION,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": "Oyen Animation for YouTube",
            "prompt": prompt,
            "mode": mode,
            "style": style,
            "visual_direction": preset["look"],
            "lighting": preset["lighting"],
        },
        "timeline": {
            "duration_seconds": int(duration),
            "fps": int(fps),
            "total_frames": int(duration * fps),
            "scenes": _build_scenes(prompt, int(duration), mode),
        },
        "render": {
            "engine": "BLENDER_EEVEE_NEXT",
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "output_format": "FFMPEG_MPEG4",
            "audio_enabled": bool(include_audio),
            "preview_resolution_percentage": 100,
        },
        "worker": {
            "mode": "huggingface_blender_headless",
            "expected_outputs": [
                "oyen_preview.blend",
                "oyen_preview.mp4",
            ],
        },
        "pipeline": [
            "director_plan",
            "procedural_oyen_placeholder",
            "camera_and_lighting",
            "blender_headless_render",
            "mp4_validation",
            "browser_preview_and_download",
        ],
        "status": "ready_to_render",
        "notes": [
            "V0.3 renders the MP4 directly inside the Hugging Face Space.",
            "Preview duration is intentionally limited for the free runtime.",
            "The current Oyen character is procedural until the final rig is connected.",
        ],
    }


def _gpu_duration(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> int:
    del prompt, mode, style, aspect_ratio, include_audio
    base = 70 + int(duration) * int(fps) // 2
    if resolution == "480p":
        base += 25
    return min(180, max(90, base))


@spaces.GPU(duration=_gpu_duration)
def create_animation_video(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> tuple[str, str | None, str | None, str, str | None, str | None, str | None]:
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 8:
        return (
            "⚠️ Tulis cerita animasi yang lebih jelas.",
            None,
            None,
            "{}",
            None,
            None,
            None,
        )

    job = _create_job(
        clean_prompt,
        mode,
        style,
        int(duration),
        aspect_ratio,
        int(fps),
        resolution,
        include_audio,
    )
    json_text = json.dumps(job, ensure_ascii=False, indent=2)
    job_dir = OUTPUT_DIR / job["job_id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    json_path = job_dir / "animation_job.json"
    json_path.write_text(json_text, encoding="utf-8")

    try:
        result = render_job(job, OUTPUT_DIR, timeout=175)
        video_path = str(result["video"])
        blend_path = str(result["blend"]) if result.get("blend") else None
        log_path = str(result["log"])
        elapsed = float(result["elapsed_seconds"])
        size_mb = float(result["video_size_bytes"]) / (1024 * 1024)
        status = (
            f"✅ **Video MP4 selesai** — `{job['job_id']}`  \n"
            f"{duration} detik • {fps} FPS • {job['render']['width']}×{job['render']['height']}  \n"
            f"Render {elapsed:.1f} detik • MP4 {size_mb:.2f} MB"
        )
        return (
            status,
            video_path,
            video_path,
            json_text,
            str(json_path),
            blend_path,
            log_path,
        )
    except BlenderRuntimeError as exc:
        return (
            f"❌ **Render gagal**\n\n```text\n{exc}\n```",
            None,
            None,
            json_text,
            str(json_path),
            None,
            None,
        )
    except Exception as exc:
        return (
            f"❌ **Kesalahan tidak terduga:** `{type(exc).__name__}: {exc}`",
            None,
            None,
            json_text,
            str(json_path),
            None,
            None,
        )


with gr.Blocks(title="Oyen AI Animation Studio") as demo:
    gr.Markdown(
        """
# 🐈 Oyen AI Animation Studio
**Prompt → Blender headless → video MP4 langsung**

V0.3 merender preview Blender di Hugging Face. Untuk menjaga runtime gratis tetap stabil,
preview dibatasi **3–8 detik**, **12–15 FPS**, dan maksimal **480p**.
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            prompt_input = gr.Textbox(
                label="Ceritakan animasi yang ingin dibuat",
                placeholder=(
                    "Contoh: Oyen berjalan ke dapur, melihat ikan di meja, "
                    "lalu terkejut ketika piring jatuh dan berlari membawa ikan."
                ),
                lines=7,
            )
            with gr.Row():
                mode_input = gr.Radio(
                    ["3D Blender", "2D Grease Pencil"],
                    value="3D Blender",
                    label="Mode animasi",
                )
                style_input = gr.Dropdown(
                    list(STYLE_PRESETS),
                    value="Oyen Cartoon",
                    label="Gaya visual",
                )

            duration_input = gr.Slider(3, 8, value=5, step=1, label="Durasi preview (detik)")

            with gr.Row():
                aspect_input = gr.Dropdown(
                    ["9:16", "16:9", "1:1"], value="9:16", label="Rasio video"
                )
                fps_input = gr.Radio([12, 15], value=12, label="FPS preview")
                resolution_input = gr.Dropdown(
                    ["360p cepat", "480p"], value="360p cepat", label="Resolusi preview"
                )

            audio_input = gr.Checkbox(
                value=False,
                label="Siapkan metadata audio/dialog (suara belum dirender pada V0.3)",
            )
            generate_button = gr.Button("🎬 Render Video MP4", variant="primary")

        with gr.Column(scale=2):
            status_output = gr.Markdown("Belum ada video yang dirender.")
            video_output = gr.Video(label="Preview MP4", autoplay=False)
            mp4_file = gr.File(label="⬇️ Download Video MP4")

    with gr.Accordion("File teknis Blender", open=False):
        json_output = gr.Code(label="animation_job.json", language="json", lines=16)
        with gr.Row():
            json_file = gr.File(label="Download JSON")
            blend_file = gr.File(label="Download .blend")
            log_file = gr.File(label="Download log Blender")

    gr.Examples(
        examples=[
            [
                "Oyen berjalan ke dapur, melihat ikan besar di meja, lalu melompat dan berlari ketika piring jatuh.",
                "3D Blender",
                "Oyen Cartoon",
                5,
                "9:16",
                12,
                "360p cepat",
                False,
            ],
            [
                "Oyen mengejar ayam di halaman, terpeleset, lalu bangkit dan pura-pura tidak terjadi apa-apa.",
                "3D Blender",
                "Oyen Cartoon",
                6,
                "16:9",
                12,
                "360p cepat",
                False,
            ],
        ],
        inputs=[
            prompt_input,
            mode_input,
            style_input,
            duration_input,
            aspect_input,
            fps_input,
            resolution_input,
            audio_input,
        ],
        label="Contoh prompt",
    )

    generate_button.click(
        fn=create_animation_video,
        inputs=[
            prompt_input,
            mode_input,
            style_input,
            duration_input,
            aspect_input,
            fps_input,
            resolution_input,
            audio_input,
        ],
        outputs=[
            status_output,
            video_output,
            mp4_file,
            json_output,
            json_file,
            blend_file,
            log_file,
        ],
        api_name="render_mp4",
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, max_size=4).launch()
