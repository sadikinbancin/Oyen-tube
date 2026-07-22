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

from direct_renderer import BlenderRenderError, render_mp4
from oyen_bridge import build_blender_script, write_worker_package

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


def _sentences(prompt: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", prompt.strip())
    return [part.strip(" -") for part in parts if part.strip(" -")]


def _build_scenes(prompt: str, duration: int, mode: str) -> list[dict[str, Any]]:
    pieces = _sentences(prompt) or [prompt]
    scene_count = max(1, min(8, round(duration / 5)))
    scene_length = duration / scene_count
    scenes: list[dict[str, Any]] = []

    for index in range(scene_count):
        start = round(index * scene_length, 2)
        end = round(min(duration, (index + 1) * scene_length), 2)
        action = pieces[index % len(pieces)]
        shot = [
            "wide establishing shot",
            "medium character shot",
            "close-up reaction",
        ][index % 3]
        scenes.append(
            {
                "scene": index + 1,
                "start_seconds": start,
                "end_seconds": end,
                "action": action,
                "camera": shot,
                "animation_note": (
                    "Use Grease Pencil layers, clear silhouettes, and pose-to-pose timing."
                    if mode == "2D Grease Pencil"
                    else "Use rig controls, IK contacts, facial poses, and smooth keyframe spacing."
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
    width, height = {
        ("9:16", "720p"): (720, 1280),
        ("9:16", "1080p"): (1080, 1920),
        ("16:9", "720p"): (1280, 720),
        ("16:9", "1080p"): (1920, 1080),
        ("1:1", "720p"): (720, 720),
        ("1:1", "1080p"): (1080, 1080),
    }[(aspect_ratio, resolution)]

    preset = STYLE_PRESETS[style]
    engine = "BLENDER_EEVEE_NEXT" if mode == "3D Blender" else "BLENDER_WORKBENCH"
    job_id = (
        f"oyen-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
        f"{uuid.uuid4().hex[:6]}"
    )

    return {
        "schema_version": "oyen.animation-job.v3",
        "app_version": APP_VERSION,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": "Oyen Animation for YouTube",
            "prompt": prompt.strip(),
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
            "engine": engine,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "output_format": "FFMPEG_MPEG4",
            "audio_enabled": bool(include_audio),
            "preview_resolution_percentage": 50,
        },
        "worker": {
            "mode": "blender_headless",
            "command": (
                "blender --background --factory-startup --enable-autoexec "
                "--python oyen_blender_scene.py"
            ),
            "expected_outputs": [
                "oyen_output/oyen_preview.blend",
                "oyen_output/oyen_preview.mp4",
            ],
        },
        "pipeline": [
            "director_plan",
            "generate_standalone_blender_script",
            "procedural_oyen_placeholder",
            "camera_and_lighting",
            "headless_blender_render",
            "video_export",
        ],
        "status": "direct_render_requested",
        "notes": [
            "V0.3 renders an MP4 directly inside the Hugging Face Space.",
            "The direct free-tier preview is capped at 15 seconds, 12 FPS, and 35% resolution.",
            "The downloadable worker package retains the full requested project settings.",
            "The current Oyen character is procedural until the final rigged model is connected.",
        ],
    }


_EMPTY_OUTPUTS = (
    None,
    None,
    None,
    "{}",
    "# Script Blender belum dibuat.",
    None,
    None,
    None,
    None,
)


@spaces.GPU(duration=300)
def create_animation_video(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> tuple[
    str,
    str | None,
    str | None,
    str | None,
    str,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
]:
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 8:
        return ("⚠️ Tulis prompt animasi yang lebih jelas.", *_EMPTY_OUTPUTS)

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
    files = write_worker_package(job, OUTPUT_DIR)
    json_text = json.dumps(job, ensure_ascii=False, indent=2)
    script_text = build_blender_script(job)

    try:
        rendered = render_mp4(job, OUTPUT_DIR / "direct_renders", timeout_seconds=285)
    except BlenderRenderError as exc:
        status = (
            f"❌ **Render MP4 gagal** — `{job['job_id']}`  \n"
            f"{exc}  \n"
            "JSON dan Worker ZIP tetap tersedia untuk pemeriksaan."
        )
        return (
            status,
            None,
            None,
            None,
            json_text,
            script_text,
            files["json"],
            files["script"],
            files["zip"],
            None,
        )

    preview_seconds = min(int(duration), 15)
    preview_fps = min(int(fps), 12)
    status = (
        f"✅ **Video MP4 berhasil dirender** — `{job['job_id']}`  \n"
        f"Preview: {preview_seconds} detik • {preview_fps} FPS • Blender headless  \n"
        "Video dapat diputar dan diunduh langsung di bawah ini."
    )
    return (
        status,
        rendered["video"],
        rendered["video"],
        rendered["blend"],
        json_text,
        script_text,
        files["json"],
        files["script"],
        files["zip"],
        rendered["log"],
    )


with gr.Blocks(title="Oyen AI Animation Studio") as demo:
    gr.Markdown(
        """
# 🐈 Oyen AI Animation Studio
**Prompt → Blender headless → video MP4**

V0.3 merender video `.mp4` langsung di Hugging Face. Worker ZIP tetap tersedia
untuk menjalankan proyek penuh pada komputer atau server Blender sendiri.
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            prompt_input = gr.Textbox(
                label="Ceritakan animasi yang ingin dibuat",
                placeholder=(
                    "Contoh: Oyen berjalan ke dapur, melihat ikan di atas meja, "
                    "melompat mengambilnya, lalu terkejut ketika piring jatuh."
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

            duration_input = gr.Slider(5, 60, value=10, step=1, label="Durasi proyek (detik)")
            with gr.Row():
                aspect_input = gr.Dropdown(
                    ["9:16", "16:9", "1:1"], value="9:16", label="Rasio video"
                )
                fps_input = gr.Slider(12, 30, value=24, step=1, label="FPS proyek")
                resolution_input = gr.Dropdown(
                    ["720p", "1080p"], value="720p", label="Resolusi proyek"
                )

            audio_input = gr.Checkbox(
                value=False,
                label="Siapkan jalur audio/dialog pada paket proyek",
            )
            generate_button = gr.Button("🎬 Render Video MP4", variant="primary")

        with gr.Column(scale=2):
            status_output = gr.Markdown("Belum ada video yang dirender.")
            video_output = gr.Video(label="Hasil Video MP4", autoplay=False)
            with gr.Row():
                mp4_file = gr.File(label="⬇️ Download MP4")
                blend_file = gr.File(label="Download file .blend")

    with gr.Accordion("File proyek dan pemeriksaan teknis", open=False):
        with gr.Tabs():
            with gr.Tab("animation_job.json"):
                json_output = gr.Code(language="json", lines=18)
            with gr.Tab("oyen_blender_scene.py"):
                script_output = gr.Code(language="python", lines=18)
        with gr.Row():
            json_file = gr.File(label="Download JSON")
            script_file = gr.File(label="Download Script Blender")
            worker_zip = gr.File(label="Download Worker ZIP")
            log_file = gr.File(label="Download render log")

    gr.Examples(
        examples=[
            [
                "Oyen mengejar ayam di halaman, terpeleset di lumpur, lalu berdiri dan berjalan pergi dengan malu.",
                "3D Blender",
                "Oyen Cartoon",
                8,
                "9:16",
                24,
                "720p",
                False,
            ],
            [
                "Oyen memasuki dapur pada malam hari, melihat ikan di meja, melompat mengambilnya, lalu berlari saat piring jatuh.",
                "3D Blender",
                "Oyen Cartoon",
                10,
                "16:9",
                24,
                "720p",
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

    gr.Markdown(
        """
### Batas preview gratis

Render langsung dibatasi maksimal **15 detik, 12 FPS, dan 35% resolusi proyek** agar
lebih stabil pada Hugging Face gratis. File JSON dan Worker ZIP tetap menyimpan pengaturan
proyek penuh sampai 60 detik. Karakter saat ini masih Oyen prosedural, belum rig final.
"""
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
            blend_file,
            json_output,
            script_output,
            json_file,
            script_file,
            worker_zip,
            log_file,
        ],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch()
