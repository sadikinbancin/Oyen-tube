from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gradio as gr
import spaces

from oyen_2d_asset_bundle import load_embedded_manifest
from oyen_2d_director import ACTION_LIBRARY, build_2d_motion_plan, compile_nla_timeline
from oyen_2d_runtime import Oyen2DRuntimeError, render_2d_job

APP_VERSION = "0.6.0"
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = Path(tempfile.gettempdir()) / "oyen_2d_animation_jobs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STAGE_AUDIT = json.loads(
    (HERE / "oyen_2d_stage_audit.json").read_text(encoding="utf-8")
)
LAYER_MANIFEST = load_embedded_manifest()

RESOLUTIONS = {
    ("9:16", "360p cepat"): (360, 640),
    ("9:16", "480p"): (480, 854),
    ("16:9", "360p cepat"): (640, 360),
    ("16:9", "480p"): (854, 480),
    ("1:1", "360p cepat"): (360, 360),
    ("1:1", "480p"): (480, 480),
}


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
    motion_plan = build_2d_motion_plan(prompt, float(duration), int(fps))
    compiled = compile_nla_timeline(motion_plan)
    job_id = (
        f"oyen-2d-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
        f"{uuid.uuid4().hex[:6]}"
    )
    active_layers = [
        item for item in LAYER_MANIFEST["layers"] if item.get("rig_enabled", True)
    ]
    return {
        "schema_version": "oyen.animation-job.v6",
        "app_version": APP_VERSION,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": "Oyen Purba 2D Cutout Studio",
            "prompt": prompt,
            "mode": mode,
            "style": style,
            "main_character": {
                "name": "Oyen Purba",
                "version": "Oyen Purba 2D Test V1",
                "source": "official brand sheet supplied by the project owner",
                "layer_manifest": LAYER_MANIFEST["schema_version"],
                "committed_png_count": 50,
                "active_rig_layers": len(active_layers),
                "bone_count": len(LAYER_MANIFEST["bones"]),
                "action_count": len(ACTION_LIBRARY),
            },
        },
        "stage_audit": STAGE_AUDIT,
        "motion_plan": motion_plan,
        "compiled_timeline": compiled,
        "timeline": {
            "duration_seconds": int(duration),
            "fps": int(fps),
            "total_frames": compiled["frame_end"],
        },
        "render": {
            "engine": "BLENDER_EEVEE_2D_CUTOUT",
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "output_format": "FFMPEG_MPEG4_H264",
            "audio_enabled": bool(include_audio),
        },
        "worker": {
            "mode": "huggingface_blender_headless_cpu",
            "expected_outputs": [
                "oyen_2d_preview.mp4",
                "oyen_2d_preview.blend",
                "oyen_2d_qa_contact_sheet.jpg",
                "animation_job.json",
                "blender_2d.log",
            ],
        },
        "quality_gate": {
            "code_validation_required": True,
            "asset_pack_validation_required": True,
            "five_qa_frames_required": True,
            "contact_sheet_required": True,
            "visual_review_required": True,
        },
        "status": "ready_to_render_2d_stage_1_to_7",
    }


def _zerogpu_duration(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
) -> int:
    """Reserve enough ZeroGPU time for Blender without claiming a full daily quota."""

    del prompt, mode, style, aspect_ratio, fps, resolution, include_audio
    return min(180, max(120, 75 + int(duration) * 15))


@spaces.GPU(duration=_zerogpu_duration)
def create_animation_video(
    prompt: str,
    mode: str,
    style: str,
    duration: int,
    aspect_ratio: str,
    fps: int,
    resolution: str,
    include_audio: bool,
):
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 8:
        return (
            "⚠️ Tulis adegan Oyen yang lebih jelas.",
            None,
            None,
            "{}",
            None,
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
        bool(include_audio),
    )
    json_text = json.dumps(job, ensure_ascii=False, indent=2)
    job_dir = OUTPUT_DIR / job["job_id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    json_path = job_dir / "animation_job.json"
    json_path.write_text(json_text, encoding="utf-8")

    try:
        result = render_2d_job(job, OUTPUT_DIR, timeout=420)
        actions = [clip["action"] for clip in job["motion_plan"]["clips"]]
        warnings = job["motion_plan"].get("warnings", [])
        warning_text = "\n\n⚠️ " + " | ".join(warnings) if warnings else ""
        status = (
            f"✅ **Oyen Purba 2D V1 selesai — Tahap 1–7 terverifikasi** "
            f"`{job['job_id']}`  \n"
            f"🧩 **{result['active_layer_count']} layer aktif** dari "
            f"**{result['asset_zip_png_count']} PNG committed** • "
            f"🦴 **{result['bone_count']} bone** • "
            f"🎬 **{result['action_count']} Action**  \n"
            f"🧠 Motion Director library-only: `{', '.join(actions)}` • "
            f"NLA **{result['nla_strip_count']} strip** • "
            f"QA **{result['qa_frame_count']} frame**  \n"
            f"🎞️ {duration} detik • {fps} FPS • "
            f"{job['render']['width']}×{job['render']['height']} • "
            f"render {float(result['elapsed_seconds']):.1f} detik"
            f"{warning_text}\n\n"
            "**Status teknis:** kode, asset pack, rig, Action, NLA, `.blend`, "
            "contact sheet, dan MP4 lolos. Periksa contact sheet untuk menilai "
            "kualitas visual sebelum produksi panjang."
        )
        return (
            status,
            str(result["video"]),
            str(result["video"]),
            json_text,
            str(json_path),
            str(result["blend"]),
            str(result["contact_sheet"]),
            str(result["log"]),
        )
    except Oyen2DRuntimeError as exc:
        return (
            f"❌ **Pipeline Oyen 2D Tahap 1–7 gagal**\n\n```text\n{exc}\n```",
            None,
            None,
            json_text,
            str(json_path),
            None,
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
            None,
        )


with gr.Blocks(title="Oyen Purba 2D Cutout Studio") as demo:
    gr.Markdown(
        """
# 🐈 Oyen Purba 2D Cutout Studio
**Brand sheet → PNG transparan → pivot → bone cutout → 7 Action → AI Motion Director → QA → MP4 + `.blend`**

Versi uji coba ini menjalankan **Tahap 1 sampai Tahap 7** sebagai satu pipeline.
AI hanya memilih Action resmi; AI tidak boleh membuat kode Blender bebas atau
mengarang karakter pengganti.
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            prompt_input = gr.Textbox(
                label="Adegan Oyen Purba",
                placeholder=(
                    "Oyen berjalan ke kanan, menoleh ke kamera, melambaikan tangan, "
                    "lalu tersenyum dan mengibaskan ekornya."
                ),
                lines=6,
            )
            with gr.Row():
                mode_input = gr.Radio(
                    ["2D Cutout Blender"],
                    value="2D Cutout Blender",
                    label="Mode produksi",
                )
                style_input = gr.Dropdown(
                    ["Oyen Purba Brand Sheet"],
                    value="Oyen Purba Brand Sheet",
                    label="Aset karakter",
                )
            duration_input = gr.Slider(
                3,
                8,
                value=6,
                step=1,
                label="Durasi preview (detik)",
            )
            with gr.Row():
                aspect_input = gr.Dropdown(
                    ["9:16", "16:9", "1:1"], value="9:16", label="Rasio"
                )
                fps_input = gr.Radio([12, 15], value=12, label="FPS")
                resolution_input = gr.Dropdown(
                    ["360p cepat", "480p"],
                    value="360p cepat",
                    label="Resolusi",
                )
            audio_input = gr.Checkbox(
                value=False,
                label="Metadata audio/dialog saja (audio belum dirender)",
            )
            generate_button = gr.Button(
                "🧠 Susun Motion 2D + Render Blender", variant="primary"
            )

        with gr.Column(scale=2):
            status_output = gr.Markdown("Belum ada render 2D.")
            video_output = gr.Video(label="Preview Oyen Purba 2D", autoplay=False)
            mp4_file = gr.File(label="⬇️ Video MP4")

    contact_sheet = gr.Image(
        label="QA Contact Sheet — wajib diperiksa", type="filepath"
    )

    with gr.Accordion("File produksi dan bukti Tahap 1–7", open=False):
        json_output = gr.Code(
            label="animation_job.json + stage audit + motion plan",
            language="json",
            lines=20,
        )
        with gr.Row():
            json_file = gr.File(label="JSON")
            blend_file = gr.File(label="Rig 2D `.blend`")
            log_file = gr.File(label="Log Blender")

    gr.Examples(
        examples=[
            [
                "Oyen berjalan ke kanan, menoleh ke kamera, melambaikan tangan, lalu tersenyum dan mengibaskan ekornya.",
                "2D Cutout Blender",
                "Oyen Purba Brand Sheet",
                6,
                "9:16",
                12,
                "360p cepat",
                False,
            ],
            [
                "Oyen berlari ke kanan, berhenti, menoleh ke kamera dengan wajah kesal.",
                "2D Cutout Blender",
                "Oyen Purba Brand Sheet",
                5,
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
        label="Contoh uji pipeline 2D",
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
            contact_sheet,
            log_file,
        ],
        api_name="render_mp4",
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, max_size=4).launch(ssr_mode=False)
