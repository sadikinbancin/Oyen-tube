from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hf_space"))

from direct_renderer import render_mp4


job = {
    "job_id": "oyen-smoke",
    "project": {
        "prompt": "Oyen berjalan pelan lalu menoleh ke kamera.",
        "mode": "3D Blender",
        "style": "Oyen Cartoon",
    },
    "timeline": {
        "duration_seconds": 1,
        "fps": 4,
        "total_frames": 4,
        "scenes": [
            {
                "scene": 1,
                "start_seconds": 0,
                "end_seconds": 1,
                "action": "Oyen berjalan pelan lalu menoleh ke kamera.",
                "camera": "medium character shot",
                "animation_note": "Smoke test",
            }
        ],
    },
    "render": {
        "engine": "BLENDER_EEVEE_NEXT",
        "width": 640,
        "height": 360,
        "aspect_ratio": "16:9",
        "output_format": "FFMPEG_MPEG4",
        "audio_enabled": False,
        "preview_resolution_percentage": 35,
    },
    "notes": [],
}

with tempfile.TemporaryDirectory(prefix="oyen-smoke-") as temp_dir:
    result = render_mp4(job, temp_dir, timeout_seconds=180)
    video = Path(result["video"])
    blend = Path(result["blend"])
    assert video.exists(), result
    assert video.stat().st_size > 1024, video.stat().st_size
    assert blend.exists(), result
    print(f"OYEN_SMOKE_MP4_SUCCESS: {video} ({video.stat().st_size} bytes)")
