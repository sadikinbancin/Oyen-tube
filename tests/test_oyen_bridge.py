from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hf_space"))

from oyen_bridge import build_blender_script, write_worker_package  # noqa: E402


def sample_job() -> dict:
    return {
        "job_id": "oyen-test-job",
        "timeline": {
            "duration_seconds": 5,
            "fps": 24,
            "total_frames": 120,
            "scenes": [
                {
                    "scene": 1,
                    "start_seconds": 0,
                    "end_seconds": 5,
                    "action": "Oyen walks into the kitchen.",
                    "camera": "wide establishing shot",
                }
            ],
        },
        "render": {
            "engine": "BLENDER_EEVEE_NEXT",
            "width": 720,
            "height": 1280,
        },
    }


class OyenBridgeTests(unittest.TestCase):
    def test_generated_script_is_valid_python(self) -> None:
        script = build_blender_script(sample_job())
        compile(script, "oyen_blender_scene.py", "exec")
        self.assertIn("OYEN_WORKER_SUCCESS", script)
        self.assertIn("bpy.ops.render.render(animation=True)", script)

    def test_worker_zip_contains_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            files = write_worker_package(sample_job(), temp_dir)
            with zipfile.ZipFile(files["zip"]) as archive:
                names = set(archive.namelist())

        self.assertEqual(
            names,
            {
                "animation_job.json",
                "oyen_blender_scene.py",
                "run_blender.sh",
                "run_blender.bat",
                "README.md",
            },
        )


if __name__ == "__main__":
    unittest.main()
