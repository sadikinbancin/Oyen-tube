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

APP_VERSION = "0.1.1"
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
        shot = ["wide establishing shot", "medium character shot", "close-up reaction"][index % 3]
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


@spaces.GPU
def create_animation_job(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> tuple[str, str, str | None]:
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 8:
        return "⚠️ Tulis prompt animasi yang lebih jelas.", "{}", None

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
    job_id = f"oyen-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    job: dict[str, Any] = {
        "schema_version": "oyen.animation-job.v1",
        "app_version": APP_VERSION,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": "Oyen Animation for YouTube",
            "prompt": clean_prompt,
            "mode": mode,
            "style": style,
            "visual_direction": preset["look"],
            "lighting": preset["lighting"],
        },
        "timeline": {
            "duration_seconds": int(duration),
            "fps": int(fps),
            "total_frames": int(duration * fps),
            "scenes": _build_scenes(clean_prompt, int(duration), mode),
        },
        "render": {
            "engine": engine,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "output_format": "FFMPEG_MPEG4",
            "audio_enabled": bool(include_audio),
        },
        "pipeline": [
            "director_plan",
            "character_and_asset_setup",
            "rig_or_grease_pencil_setup",
            "animation",
            "camera_and_lighting",
            "render",
            "video_edit_and_export",
        ],
        "status": "planned",
        "notes": [
            "V0.1 creates a production-ready JSON plan.",
            "Blender execution will be connected in the next development stage.",
            "The generation function is ZeroGPU-compatible through @spaces.GPU.",
        ],
    }

    json_text = json.dumps(job, ensure_ascii=False, indent=2)
    output_path = OUTPUT_DIR / f"{job_id}.json"
    output_path.write_text(json_text, encoding="utf-8")

    status = (
        f"✅ **Rencana berhasil dibuat** — `{job_id}`  \n"
        f"{len(job['timeline']['scenes'])} adegan • {duration} detik • "
        f"{fps} FPS • {width}×{height}"
    )
    return status, json_text, str(output_path)


with gr.Blocks(title="Oyen AI Animation Studio") as demo:
    gr.Markdown(
        """
# 🐈 Oyen AI Animation Studio
**Prompt → storyboard → animation job JSON → Blender pipeline**

V0.1 membuat rancangan produksi animasi 2D atau 3D yang nanti dieksekusi oleh mesin Blender Oyen.
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            prompt_input = gr.Textbox(
                label="Ceritakan animasi yang ingin dibuat",
                placeholder=(
                    "Contoh: Oyen berjalan ke dapur pada malam hari, melihat ikan besar "
                    "di atas meja, lalu tersenyum licik dan melompat mengambilnya."
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

            duration_input = gr.Slider(5, 60, value=15, step=1, label="Durasi (detik)")

            with gr.Row():
                aspect_input = gr.Dropdown(
                    ["9:16", "16:9", "1:1"], value="9:16", label="Rasio video"
                )
                fps_input = gr.Slider(12, 30, value=24, step=1, label="FPS")
                resolution_input = gr.Dropdown(
                    ["720p", "1080p"], value="720p", label="Resolusi"
                )

            audio_input = gr.Checkbox(value=True, label="Siapkan jalur audio/dialog")
            generate_button = gr.Button("🚀 Buat Rencana Animasi", variant="primary")

        with gr.Column(scale=2):
            status_output = gr.Markdown("Belum ada job yang dibuat.")
            json_output = gr.Code(label="animation_job.json", language="json", lines=22)
            file_output = gr.File(label="Download JSON")

    gr.Examples(
        examples=[
            [
                "Oyen mengejar ayam di halaman, terpeleset di lumpur, lalu pura-pura tidak terjadi apa-apa.",
                "3D Blender",
                "Oyen Cartoon",
                15,
                "9:16",
                24,
                "720p",
                True,
            ],
            [
                "Seorang CEO muda memasuki ruang rapat, menemukan surat misterius, lalu menatap asistennya dengan curiga.",
                "3D Blender",
                "Drama China Modern",
                20,
                "9:16",
                24,
                "1080p",
                True,
            ],
            [
                "Oyen duduk di atap saat matahari terbenam, ekornya bergerak pelan dan burung melintas di langit.",
                "2D Grease Pencil",
                "Anime",
                12,
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
### Pipeline V0.1
GitHub menyimpan kode utama. Hugging Face menjalankan UI Gradio. ZeroGPU menangani fungsi AI yang dihias dengan `@spaces.GPU`. Render Blender tetap disiapkan sebagai worker terpisah.
"""
    )

    generate_button.click(
        fn=create_animation_job,
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
        outputs=[status_output, json_output, file_output],
    )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=4).launch()
