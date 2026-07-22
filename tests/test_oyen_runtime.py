from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
HF_SPACE = ROOT / "hf_space"
if str(HF_SPACE) not in sys.path:
    sys.path.insert(0, str(HF_SPACE))

from oyen_runtime import BlenderRuntimeError, _prepare_script, find_blender


SAMPLE_JOB = {
    "job_id": "test-job",
    "timeline": {
        "duration_seconds": 3,
        "fps": 12,
        "total_frames": 36,
        "scenes": [
            {
                "start_seconds": 0,
                "end_seconds": 3,
                "camera": "wide establishing shot",
                "action": "Oyen walks",
            }
        ],
    },
    "render": {
        "engine": "BLENDER_EEVEE_NEXT",
        "width": 360,
        "height": 640,
        "preview_resolution_percentage": 100,
    },
}


class OyenRuntimeTests(unittest.TestCase):
    def test_prepare_script_uses_runtime_output_directory(self) -> None:
        script = _prepare_script(SAMPLE_JOB)
        self.assertIn("OYEN_OUTPUT_DIR", script)
        self.assertIn("preview_resolution_percentage", script)
        self.assertIn("BLENDER_EEVEE", script)
        self.assertIn("OYEN_WORKER_SUCCESS", script)

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
