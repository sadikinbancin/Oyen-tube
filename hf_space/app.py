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

from oyen_bridge import build_blender_script, write_worker_package

APP_VERSION = "0.2.0"
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
    clean_prompt = prompt.strip()
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

    return {
        "schema_version": "oyen.animation-job.v2",
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
        "status": "worker_package_ready",
        "notes": [
            "V0.2 generates JSON, a standalone Blender script, and a worker ZIP.",
            "The worker follows the headless Blender execution pattern used by blender-mcp.",
            "ZeroGPU prepares files; Blender rendering runs on a local or remote Blender worker.",
            "The current character is a procedural placeholder until the final rigged Oyen model is connected.",
        ],
    }


@spaces.GPU
def create_animation_package(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> tuple[str, str, str, str | None, str | None, str | None]:
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 8:
        return (
            "⚠️ Tulis prompt animasi yang lebih jelas.",
            "{}",
            "# Script Blender belum dibuat.",
            None,
            None,
            None,
        )

    try:
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

        render = job["render"]
        status = (
            f"✅ **Paket Blender siap** — `{job['job_id']}`  \n"
            f"{len(job['timeline']['scenes'])} adegan • {duration} detik • "
            f"{fps} FPS • {render['width']}×{render['height']}  \n"
            "Unduh **Worker ZIP**, ekstrak di komputer yang memiliki Blender, lalu jalankan "
            "`run_blender.bat` atau `run_blender.sh`."
        )
        return status, json_text, script_text, files["json"], files["script"], files["zip"]
    except Exception as exc:
        return (
            f"❌ Gagal membuat paket worker: `{type(exc).__name__}: {exc}`",
            "{}",
            "# Terjadi kesalahan saat membuat script Blender.",
            None,
            None,
            None,
        )


with gr.Blocks(title="Oyen AI Animation Studio") as demo:
    gr.Markdown(
        """
# 🐈 Oyen AI Animation Studio
**Prompt → storyboard → JSON → script Blender → worker ZIP → MP4**

V0.2 menghasilkan paket worker Blender headless. Hugging Face menyiapkan instruksi dan
file; komputer atau server yang memiliki Blender menjalankan render.
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            prompt_input = gr.Textbox(
                label="Ceritakan animasi yang ingin dibuat",
                placeholder=(
                    "Contoh: Oyen berjalan ke dapur pada malam hari, melihat ikan besar "
                    "di atas meja, lalu terkejut ketika piring jatuh."
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
            generate_button = gr.Button("🚀 Buat Paket Blender", variant="primary")

        with gr.Column(scale=2):
            status_output = gr.Markdown("Belum ada paket worker yang dibuat.")
            with gr.Tabs():
                with gr.Tab("animation_job.json"):
                    json_output = gr.Code(language="json", lines=22)
                with gr.Tab("oyen_blender_scene.py"):
                    script_output = gr.Code(language="python", lines=22)

            with gr.Row():
                json_file = gr.File(label="Download JSON")
                script_file = gr.File(label="Download Script Blender")
            worker_zip = gr.File(label="⭐ Download Worker ZIP")

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
### Cara kerja V0.2

1. Buat paket dari prompt.
2. Unduh **Worker ZIP**.
3. Ekstrak ZIP pada komputer/server yang sudah dipasang Blender.
4. Jalankan `run_blender.bat` (Windows) atau `run_blender.sh` (Linux/macOS).
5. Ambil hasil dari folder `oyen_output/`.

Karakter saat ini masih placeholder prosedural untuk membuktikan jalur
**JSON → Blender headless → `.blend` + MP4**. Rig Oyen final menjadi fase berikutnya.
"""
    )

    generate_button.click(
        fn=create_animation_package,
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
            json_output,
            script_output,
            json_file,
            script_file,
            worker_zip,
        ],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch()
