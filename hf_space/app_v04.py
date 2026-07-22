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

APP_VERSION = "0.4.0"
RIG_BONE_COUNT = 34
OUTPUT_DIR = Path(tempfile.gettempdir()) / "oyen_animation_jobs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE_PRESETS: dict[str, dict[str, str]] = {
    "Oyen Purba Official": {
        "look": (
            "short chubby orange tabby hero, large amber eyes, Sun Cream muzzle and belly, "
            "small friendly fangs, fang necklace, prehistoric loincloth, striped articulated tail"
        ),
        "lighting": "warm cinematic cartoon studio lighting",
    },
    "Oyen Cartoon": {
        "look": "friendly stylized cartoon, expressive face, clean rounded shapes",
        "lighting": "soft cinematic daylight",
    },
    "Semi-realistic 3D": {
        "look": "polished semi-realistic 3D animation with stable character identity",
        "lighting": "cinematic three-point lighting",
    },
}

RESOLUTIONS = {
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


def _scenes(prompt: str, duration: int) -> list[dict[str, Any]]:
    pieces = _sentences(prompt) or [prompt]
    count = max(1, min(4, round(duration / 2)))
    length = duration / count
    return [
        {
            "scene": index + 1,
            "start_seconds": round(index * length, 2),
            "end_seconds": round(min(duration, (index + 1) * length), 2),
            "action": pieces[index % len(pieces)],
            "camera": ["wide establishing shot", "medium character shot", "close-up reaction"][index % 3],
            "animation_note": "Drive the Oyen Purba armature: gait, body bounce, head, jaw, ears, limbs and tail.",
        }
        for index in range(count)
    ]


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
        "schema_version": "oyen.animation-job.v4",
        "app_version": APP_VERSION,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": "Oyen Purba Animation for YouTube",
            "prompt": prompt,
            "mode": mode,
            "style": style,
            "visual_direction": preset["look"],
            "lighting": preset["lighting"],
            "main_character": {
                "name": "Oyen Purba",
                "rig_version": "Oyen Purba 3D Rig V1",
                "armature": "Oyen_Purba_Rig",
                "bone_count": RIG_BONE_COUNT,
                "controls": [
                    "root/pelvis/spine/chest/neck/head/jaw",
                    "arms, elbows, hands, thighs, knees and feet",
                    "IK hands and feet with elbow/knee pole targets",
                    "five-bone articulated tail",
                ],
                "official_colors": {
                    "Blaze Orange": "#E8842A",
                    "Sun Cream": "#F7D89B",
                    "Deep Cocoa": "#4A2C24",
                    "Amber Eyes": "#D79223",
                    "Leaf Tail": "#2F7D70",
                },
            },
        },
        "timeline": {
            "duration_seconds": int(duration),
            "fps": int(fps),
            "total_frames": int(duration * fps),
            "scenes": _scenes(prompt, int(duration)),
        },
        "render": {
            "engine": "BLENDER_WORKBENCH",
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "output_format": "FFMPEG_MPEG4",
            "audio_enabled": bool(include_audio),
            "preview_resolution_percentage": 100,
        },
        "worker": {
            "mode": "huggingface_blender_headless_cpu",
            "expected_outputs": ["oyen_preview.blend", "oyen_preview.mp4"],
        },
        "pipeline": [
            "director_plan",
            "build_oyen_purba_character",
            "create_34_bone_armature_and_ik_controls",
            "prompt_aware_rig_animation",
            "camera_animation",
            "save_rigged_blend",
            "render_mp4",
            "validate_armature_blend_and_video",
        ],
        "status": "ready_to_render_rigged_character",
        "notes": [
            "Rig V1 uses stable segmented bone parenting for automatic rendering.",
            "The .blend file contains the editable armature and IK controls.",
            "Rig V2 will add unified retopology, deformation weights and facial shape keys.",
        ],
    }


@spaces.GPU(duration=1)
def _zerogpu_registration() -> str:
    return "ZeroGPU registered"


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
        return "⚠️ Tulis gerakan atau adegan Oyen yang lebih jelas.", None, None, "{}", None, None, None

    job = _create_job(
        clean_prompt, mode, style, int(duration), aspect_ratio, int(fps), resolution, include_audio
    )
    json_text = json.dumps(job, ensure_ascii=False, indent=2)
    job_dir = OUTPUT_DIR / job["job_id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    json_path = job_dir / "animation_job.json"
    json_path.write_text(json_text, encoding="utf-8")

    try:
        result = render_job(job, OUTPUT_DIR, timeout=300)
        video_path = str(result["video"])
        blend_path = str(result["blend"])
        log_path = str(result["log"])
        elapsed = float(result["elapsed_seconds"])
        size_mb = float(result["video_size_bytes"]) / (1024 * 1024)
        bone_count = int(result["rig_bone_count"])
        status = (
            f"✅ **Oyen Purba 3D Rig V1 selesai** — `{job['job_id']}`  \n"
            f"Armature terverifikasi: **{bone_count} tulang** • {duration} detik • {fps} FPS • "
            f"{job['render']['width']}×{job['render']['height']}  \n"
            f"Render {elapsed:.1f} detik • MP4 {size_mb:.2f} MB • `.blend` siap diedit"
        )
        return status, video_path, video_path, json_text, str(json_path), blend_path, log_path
    except BlenderRuntimeError as exc:
        return f"❌ **Render rig gagal**\n\n```text\n{exc}\n```", None, None, json_text, str(json_path), None, None
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


with gr.Blocks(title="Oyen Purba 3D Rig Studio") as demo:
    gr.Markdown(
        """
# 🐈 Oyen Purba 3D Rig Studio
**Prompt → karakter utama Oyen Purba → armature 34 tulang + IK → MP4 + `.blend`**

V0.4 memakai desain resmi Oyen Purba sebagai karakter utama tetap. Gerak tidak lagi hanya menggeser
badan: armature menggerakkan tubuh, kepala, rahang, telinga, tangan, kaki dan lima ruas ekor.

> **Rig V1:** model tersegmentasi yang dipasang pada tulang agar stabil untuk render otomatis.  
> **Target Rig V2:** mesh menyatu, retopologi, weight painting, IK/FK produksi dan shape keys wajah.
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            prompt_input = gr.Textbox(
                label="Gerakan atau adegan Oyen Purba",
                placeholder="Oyen berjalan percaya diri, melompat, terkejut melihat ikan, lalu tersenyum dan mengibaskan ekornya.",
                lines=7,
            )
            with gr.Row():
                mode_input = gr.Radio(["3D Blender"], value="3D Blender", label="Mode produksi")
                style_input = gr.Dropdown(
                    list(STYLE_PRESETS), value="Oyen Purba Official", label="Gaya visual"
                )
            duration_input = gr.Slider(3, 8, value=5, step=1, label="Durasi preview (detik)")
            with gr.Row():
                aspect_input = gr.Dropdown(["9:16", "16:9", "1:1"], value="9:16", label="Rasio")
                fps_input = gr.Radio([12, 15], value=12, label="FPS")
                resolution_input = gr.Dropdown(
                    ["360p cepat", "480p"], value="360p cepat", label="Resolusi"
                )
            audio_input = gr.Checkbox(
                value=False, label="Siapkan metadata audio/dialog (suara belum dirender)"
            )
            generate_button = gr.Button("🦴 Render Oyen Purba 3D Rig", variant="primary")

        with gr.Column(scale=2):
            status_output = gr.Markdown("Belum ada rig yang dirender.")
            video_output = gr.Video(label="Preview Oyen Purba", autoplay=False)
            mp4_file = gr.File(label="⬇️ Download Video MP4")

    with gr.Accordion("File produksi Blender", open=False):
        gr.Markdown(
            "Download `.blend`, buka di Blender, pilih **Oyen_Purba_Rig**, lalu aktifkan **In Front** "
            "untuk melihat tulangnya melalui tubuh."
        )
        json_output = gr.Code(label="animation_job.json", language="json", lines=15)
        with gr.Row():
            json_file = gr.File(label="Download JSON")
            blend_file = gr.File(label="🦴 Download Rig `.blend`")
            log_file = gr.File(label="Download log Blender")

    gr.Examples(
        examples=[
            [
                "Oyen berjalan dua langkah, menoleh ke kamera, lalu melambaikan tangan dan mengibaskan ekornya.",
                "3D Blender", "Oyen Purba Official", 3, "9:16", 12, "360p cepat", False,
            ],
            [
                "Oyen berlari mengejar ayam, berhenti mendadak, lalu menatap kamera dengan wajah kesal.",
                "3D Blender", "Oyen Purba Official", 5, "16:9", 12, "360p cepat", False,
            ],
        ],
        inputs=[
            prompt_input, mode_input, style_input, duration_input,
            aspect_input, fps_input, resolution_input, audio_input,
        ],
        label="Contoh uji rig",
    )

    generate_button.click(
        fn=create_animation_video,
        inputs=[
            prompt_input, mode_input, style_input, duration_input,
            aspect_input, fps_input, resolution_input, audio_input,
        ],
        outputs=[
            status_output, video_output, mp4_file, json_output,
            json_file, blend_file, log_file,
        ],
        api_name="render_mp4",
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, max_size=4).launch()
