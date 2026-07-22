from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HF_SPACE = ROOT / "hf_space"
if str(HF_SPACE) not in sys.path:
    sys.path.insert(0, str(HF_SPACE))

from oyen_runtime import BlenderRuntimeError, _prepare_script, find_blender  # noqa: E402


SAMPLE_JOB = {
    "job_id": "test-motion-job",
    "project": {"prompt": "Oyen berlari ke depan lalu berhenti."},
    "motion_plan": {
        "coordinate_system": {"character_forward": "-Y", "right": "+X", "up": "+Z"},
        "clips": [
            {
                "type": "run",
                "start": 0.0,
                "end": 2.2,
                "direction": "forward",
                "distance": 2.0,
                "intensity": 0.9,
                "target": "",
            },
            {
                "type": "stop",
                "start": 2.2,
                "end": 3.0,
                "direction": "none",
                "distance": 0.0,
                "intensity": 0.7,
                "target": "",
            },
        ],
        "camera": [
            {
                "start": 0.0,
                "end": 3.0,
                "shot": "medium",
                "angle": "three_quarter",
                "follow": True,
            }
        ],
    },
    "timeline": {
        "duration_seconds": 3,
        "fps": 12,
        "total_frames": 36,
    },
    "render": {
        "engine": "BLENDER_WORKBENCH",
        "width": 360,
        "height": 640,
        "aspect_ratio": "9:16",
        "preview_resolution_percentage": 100,
    },
}


class OyenRuntimeTests(unittest.TestCase):
    def test_prepare_script_contains_runtime_paths_rig_and_motion_proof(self) -> None:
        script = _prepare_script(SAMPLE_JOB)
        self.assertIn("OYEN_OUTPUT_DIR", script)
        self.assertIn("preview_resolution_percentage", script)
        self.assertIn("BLENDER_WORKBENCH", script)
        self.assertIn("Oyen_Purba_Rig", script)
        self.assertIn("OYEN_MOTION_AI_SUCCESS", script)
        self.assertIn("OYEN_MOTION_PLAN_EMBEDDED", script)
        self.assertIn("Oyen_AI_Motion_Plan.json", script)
        self.assertIn("OYEN_RIG_V1_SUCCESS", script)
        self.assertIn("OYEN_RIG_BONES count=", script)
        self.assertIn("OYEN_WORKER_SUCCESS", script)
        self.assertIn('"forward": (0.0, -1.0)', script)

    def test_find_blender_accepts_explicit_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "blender"
            fake.write_text("#!/bin/sh\n", encoding="utf-8")
            with patch.dict(os.environ, {"BLENDER_EXECUTABLE": str(fake)}, clear=False):
                self.assertEqual(find_blender(), str(fake.resolve()))

    def test_find_blender_fails_cleanly(self) -> None:
        with patch.dict(os.environ, {"BLENDER_EXECUTABLE": ""}, clear=False), patch(
            "oyen_runtime.shutil.which", return_value=None
        ), patch("oyen_runtime.Path.is_file", return_value=False):
            with self.assertRaises(BlenderRuntimeError):
                find_blender()


if __name__ == "__main__":
    unittest.main()
