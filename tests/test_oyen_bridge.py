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
        "project": {"prompt": "Oyen walks, jumps, and looks surprised."},
        "timeline": {
            "duration_seconds": 5,
            "fps": 12,
            "total_frames": 60,
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
            "engine": "BLENDER_WORKBENCH",
            "width": 360,
            "height": 640,
            "preview_resolution_percentage": 100,
        },
    }


class OyenBridgeTests(unittest.TestCase):
    def test_generated_script_is_valid_python_and_contains_rig(self) -> None:
        script = build_blender_script(sample_job())
        compile(script, "oyen_blender_scene.py", "exec")
        for marker in (
            "OyenPurba_Rig",
            "create_armature",
            'bone("jaw"',
            'f"tail.{index + 1:02d}"',
            "OYEN_RIG_READY",
            "OYEN_WORKER_SUCCESS",
            "bpy.ops.render.render(animation=True)",
        ):
            self.assertIn(marker, script)

    def test_rig_contains_expected_bone_groups(self) -> None:
        script = build_blender_script(sample_job())
        for bone_name in (
            "root",
            "pelvis",
            "spine",
            "head",
            "jaw",
            "upper_arm.L",
            "forearm.R",
            "thigh.L",
            "foot.R",
            "tail.01",
            "tail.05",
        ):
            self.assertIn(bone_name, script)
        self.assertIn("segmented bone-parent rig", script)
        self.assertIn("Blaze Orange", script)
        self.assertIn("FangPendant", script)

    def test_worker_zip_contains_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            files = write_worker_package(sample_job(), temp_dir)
            with zipfile.ZipFile(files["zip"]) as archive:
                names = set(archive.namelist())
                readme = archive.read("README.md").decode("utf-8")

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
        self.assertIn("Oyen Purba 3D Rig V1", readme)
        self.assertIn("lima tulang ekor", readme)


if __name__ == "__main__":
    unittest.main()
