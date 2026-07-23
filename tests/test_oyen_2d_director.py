from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hf_space"))

from oyen_2d_director import (  # noqa: E402
    MotionPlanError,
    build_2d_motion_plan,
    build_blender_nla_script,
    compile_nla_timeline,
    load_motion_library,
    validate_2d_motion_plan,
)


class Oyen2DMotionDirectorTests(unittest.TestCase):
    def test_run_prompt_uses_library_actions_and_no_unrequested_wave(self) -> None:
        plan = build_2d_motion_plan(
            "Oyen berlari mengejar ayam, berhenti, lalu menoleh ke kamera dengan kesal.",
            6,
            12,
        )
        actions = [clip["action"] for clip in plan["clips"]]
        self.assertEqual(actions[0], "OYEN_RUN_IN_PLACE")
        self.assertIn("OYEN_HEAD_TURN", actions)
        self.assertNotIn("OYEN_WAVE", actions)
        self.assertEqual(plan["expressions"][-1]["name"], "ANGRY")
        self.assertTrue(any("ayam" in warning for warning in plan["warnings"]))
        self.assertFalse(plan["safety"]["arbitrary_python_allowed"])

    def test_wave_only_when_requested(self) -> None:
        without_wave = build_2d_motion_plan("Oyen berjalan santai dan tersenyum.", 5)
        with_wave = build_2d_motion_plan(
            "Oyen berjalan, menoleh ke kamera, lalu melambaikan tangan.", 6
        )
        self.assertNotIn("OYEN_WAVE", [item["action"] for item in without_wave["clips"]])
        self.assertIn("OYEN_WAVE", [item["action"] for item in with_wave["clips"]])

    def test_compiler_creates_fixed_tracks_root_and_face_events(self) -> None:
        plan = build_2d_motion_plan(
            "Oyen berlari, menoleh ke kamera, marah, lalu mengibaskan ekor.", 7
        )
        timeline = compile_nla_timeline(plan)
        self.assertEqual(timeline["schema_version"], "oyen.2d-nla-timeline.v1")
        self.assertTrue(timeline["camera"]["orthographic"])
        self.assertTrue(timeline["root_motion"])
        self.assertTrue(any(item["kind"] == "expression_swap" for item in timeline["face_events"]))
        self.assertTrue(any(strip["action"] == "OYEN_RUN_IN_PLACE" for strip in timeline["strips"]))

    def test_rejects_unknown_action_and_arbitrary_code_field(self) -> None:
        plan = build_2d_motion_plan("Oyen diam dan melihat kamera.", 4)
        plan["clips"][0]["action"] = "OYEN_BACKFLIP_LIAR"
        with self.assertRaises(MotionPlanError):
            validate_2d_motion_plan(plan)

        plan = build_2d_motion_plan("Oyen diam dan melihat kamera.", 4)
        plan["python"] = "import bpy"
        with self.assertRaises(MotionPlanError):
            validate_2d_motion_plan(plan)

    def test_rejects_overlapping_locomotion(self) -> None:
        plan = build_2d_motion_plan("Oyen berjalan santai.", 5)
        plan["clips"].append(
            {
                "action": "OYEN_RUN_IN_PLACE",
                "start": 0.5,
                "end": 2.0,
                "track": "locomotion",
                "direction": "right",
                "distance": 1.0,
                "intensity": 0.8,
            }
        )
        with self.assertRaises(MotionPlanError):
            validate_2d_motion_plan(plan)

    def test_generated_blender_script_is_valid_and_library_only(self) -> None:
        plan = build_2d_motion_plan(
            "Oyen berjalan, melambaikan tangan, lalu tersenyum dan mengibaskan ekor.",
            6,
        )
        script = build_blender_nla_script(plan)
        compile(script, "oyen_2d_nla_compiler.py", "exec")
        self.assertIn('ARMATURE_NAME = "Oyen_Purba_2D_Rig"', script)
        self.assertIn("OYEN_2D_NLA_SUCCESS", script)
        self.assertIn("OYEN_2D_LIBRARY_ONLY true", script)
        self.assertNotIn("exec(", script)
        self.assertNotIn("eval(", script)

    def test_manifest_matches_code_contract(self) -> None:
        manifest = load_motion_library(ROOT / "hf_space" / "oyen_2d_motion_library.json")
        self.assertTrue(manifest["policy"]["library_only"])
        self.assertFalse(manifest["policy"]["arbitrary_python_allowed"])
        json.dumps(manifest)


if __name__ == "__main__":
    unittest.main()
