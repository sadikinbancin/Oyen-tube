from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hf_space"))

from direct_renderer import _runtime_script, make_preview_job


def sample_job(duration: int = 60, fps: int = 24) -> dict:
    return {
        "job_id": "oyen-test",
        "project": {"prompt": "Oyen berjalan lalu melompat."},
        "timeline": {
            "duration_seconds": duration,
            "fps": fps,
            "total_frames": duration * fps,
            "scenes": [
                {
                    "scene": index + 1,
                    "start_seconds": index * 5,
                    "end_seconds": (index + 1) * 5,
                    "action": f"Gerakan {index + 1}",
                    "camera": "wide establishing shot",
                }
                for index in range(8)
            ],
        },
        "render": {
            "engine": "BLENDER_EEVEE_NEXT",
            "width": 720,
            "height": 1280,
            "preview_resolution_percentage": 50,
        },
        "notes": [],
    }


class DirectRendererTests(unittest.TestCase):
    def test_preview_is_capped_for_free_tier(self) -> None:
        preview = make_preview_job(sample_job())
        self.assertEqual(preview["timeline"]["duration_seconds"], 15)
        self.assertEqual(preview["timeline"]["fps"], 12)
        self.assertEqual(preview["timeline"]["total_frames"], 180)
        self.assertLessEqual(len(preview["timeline"]["scenes"]), 4)
        self.assertEqual(preview["render"]["preview_resolution_percentage"], 35)

    def test_runtime_script_supports_space_output_and_old_eevee(self) -> None:
        script = _runtime_script(make_preview_job(sample_job(5, 12)))
        self.assertIn("OYEN_OUTPUT_DIR", script)
        self.assertIn('"BLENDER_EEVEE"', script)
        self.assertIn("preview_resolution_percentage", script)
        self.assertIn("OYEN_WORKER_SUCCESS", script)


if __name__ == "__main__":
    unittest.main()
