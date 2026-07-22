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
        "job_id": "oyen-motion-test",
        "project": {"prompt": "Oyen runs forward then looks at the camera."},
        "motion_plan": {
            "coordinate_system": {"character_forward": "-Y", "right": "+X", "up": "+Z"},
            "clips": [
                {
                    "type": "run",
                    "start": 0.0,
                    "end": 3.5,
                    "direction": "forward",
                    "distance": 2.8,
                    "intensity": 0.9,
                    "target": "ayam",
                },
                {
                    "type": "look",
                    "start": 3.5,
                    "end": 5.0,
                    "direction": "none",
                    "distance": 0.0,
                    "intensity": 0.7,
                    "target": "camera",
                },
            ],
            "camera": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "shot": "medium",
                    "angle": "three_quarter",
                    "follow": True,
                }
            ],
        },
        "timeline": {
            "duration_seconds": 5,
            "fps": 12,
            "total_frames": 60,
        },
        "render": {
            "engine": "BLENDER_WORKBENCH",
            "width": 360,
            "height": 640,
            "aspect_ratio": "9:16",
            "preview_resolution_percentage": 100,
        },
    }


class OyenBridgeTests(unittest.TestCase):
    def test_generated_motion_rig_script_is_valid_python(self) -> None:
        script = build_blender_script(sample_job())
        compile(script, "oyen_blender_scene.py", "exec")
        self.assertIn("OYEN_MOTION_AI_SUCCESS", script)
        self.assertIn("OYEN_MOTION_PLAN_EMBEDDED", script)
        self.assertIn("Oyen_AI_Motion_Plan.json", script)
        self.assertIn("Oyen_Purba_Rig", script)
        self.assertIn('bone("root"', script)
        self.assertIn('bone(f"upper_arm.{side}"', script)
        self.assertIn('name = f"tail.{index:02d}"', script)
        self.assertIn("Oyen_Arm_IK", script)
        self.assertIn("Oyen_Leg_IK", script)
        self.assertIn("direction_vector", script)
        self.assertIn('"forward": (0.0, -1.0)', script)
        self.assertIn("key_locomotion", script)
        self.assertIn("key_jump", script)
        self.assertIn("key_angry", script)
        self.assertIn("bpy.ops.render.render(animation=True)", script)

    def test_worker_zip_contains_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            files = write_worker_package(sample_job(), temp_dir)
            with zipfile.ZipFile(files["zip"]) as archive:
                names = set(archive.namelist())
                script = archive.read("oyen_blender_scene.py").decode("utf-8")

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
        self.assertIn("Oyen Purba", script)
        self.assertIn("motion_plan", script)


if __name__ == "__main__":
    unittest.main()
