from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HF_SPACE = ROOT / "hf_space"
if str(HF_SPACE) not in sys.path:
    sys.path.insert(0, str(HF_SPACE))

from oyen_motion_ai import build_motion_plan  # noqa: E402


class OyenMotionAITests(unittest.TestCase):
    def test_indonesian_run_prompt_moves_forward_not_sideways(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            plan, provider, note = build_motion_plan(
                "Oyen berlari mengejar ayam lalu berhenti dan menoleh ke kamera.",
                5,
            )

        self.assertEqual(provider, "Local fallback")
        self.assertIn("Local prompt parser", note)
        self.assertEqual(plan["coordinate_system"]["character_forward"], "-Y")
        self.assertEqual(plan["clips"][0]["type"], "run")
        self.assertEqual(plan["clips"][0]["direction"], "forward")
        self.assertGreater(plan["clips"][0]["distance"], 0)
        self.assertNotIn("wave", [clip["type"] for clip in plan["clips"]])

    def test_wave_is_only_added_when_requested(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            plan, _, _ = build_motion_plan(
                "Oyen berjalan ke depan lalu melambaikan tangan.",
                5,
            )
        self.assertIn("wave", [clip["type"] for clip in plan["clips"]])

    def test_plan_ends_at_requested_duration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            plan, _, _ = build_motion_plan("Oyen melompat karena terkejut.", 4)
        self.assertAlmostEqual(plan["clips"][-1]["end"], 4.0)


if __name__ == "__main__":
    unittest.main()
