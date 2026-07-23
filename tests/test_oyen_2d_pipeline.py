from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "hf_space"
sys.path.insert(0, str(HF))

from oyen_2d_asset_bundle import (  # noqa: E402
    EXPECTED_PARTS,
    load_embedded_manifest,
    materialize_asset_zip,
    validate_asset_bundle,
)
from oyen_2d_builder import build_2d_blender_script, validate_asset_pack  # noqa: E402
from oyen_2d_director import ACTION_LIBRARY, build_2d_motion_plan, compile_nla_timeline  # noqa: E402


class Oyen2DPipelineTests(unittest.TestCase):
    def test_stage_audit_has_seven_implemented_stages(self) -> None:
        audit = json.loads(
            (HF / "oyen_2d_stage_audit.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(audit["stages"]), 7)
        self.assertTrue(
            all(item["status"] == "implemented" for item in audit["stages"].values())
        )
        self.assertTrue(audit["render_gate"]["requires_mp4"])
        self.assertTrue(audit["render_gate"]["requires_blend"])

    def test_committed_asset_parts_decode_and_match_embedded_manifest(self) -> None:
        parts = sorted((HF / "oyen_2d_asset_parts").glob("*.b64"))
        self.assertEqual(len(parts), EXPECTED_PARTS)
        with tempfile.TemporaryDirectory() as tmp:
            asset_zip = materialize_asset_zip(tmp)
            proof = validate_asset_pack(asset_zip)
        bundle = validate_asset_bundle()
        manifest = load_embedded_manifest()
        self.assertGreaterEqual(proof["png_count"], 40)
        self.assertGreaterEqual(proof["active_layer_count"], 35)
        self.assertGreaterEqual(proof["bone_count"], 25)
        self.assertEqual(bundle["png_count"], proof["png_count"])
        self.assertEqual(manifest["schema_version"], "oyen.2d-layer-manifest.v1")

    def test_builder_compiles_library_only_stage_1_to_7_script(self) -> None:
        prompt = (
            "Oyen berjalan ke kanan, menoleh ke kamera, melambaikan tangan, "
            "lalu tersenyum dan mengibaskan ekornya."
        )
        plan = build_2d_motion_plan(prompt, 6, 12)
        timeline = compile_nla_timeline(plan)
        audit = json.loads(
            (HF / "oyen_2d_stage_audit.json").read_text(encoding="utf-8")
        )
        job = {
            "job_id": "unit-v06",
            "motion_plan": plan,
            "compiled_timeline": timeline,
            "stage_audit": audit,
            "render": {"width": 360, "height": 640, "aspect_ratio": "9:16"},
        }
        script = build_2d_blender_script(job)
        compile(script, "oyen_2d_scene.py", "exec")
        self.assertEqual(len(ACTION_LIBRARY), 7)
        for action in ACTION_LIBRARY:
            self.assertIn(action, script)
        for marker in (
            "Oyen_Purba_2D_Rig",
            "OYEN_2D_ASSETS count=",
            "OYEN_2D_BONES count=",
            "OYEN_2D_ACTIONS count=",
            "OYEN_2D_NLA strips=",
            "OYEN_2D_QA frames=",
            "OYEN_2D_LIBRARY_ONLY true",
            "OYEN_2D_RENDER_SUCCESS",
        ):
            self.assertIn(marker, script)
        self.assertNotIn('Oyen_Purba_Rig"', script)

    def test_prompt_compiles_requested_actions_and_forward_root_motion(self) -> None:
        plan = build_2d_motion_plan(
            "Oyen berjalan ke kanan, menoleh ke kamera, melambaikan tangan dan mengibaskan ekornya.",
            6,
            12,
        )
        actions = [item["action"] for item in plan["clips"]]
        self.assertIn("OYEN_WALK_IN_PLACE", actions)
        self.assertIn("OYEN_HEAD_TURN", actions)
        self.assertIn("OYEN_WAVE", actions)
        self.assertIn("OYEN_TAIL_WAG", actions)
        timeline = compile_nla_timeline(plan)
        self.assertTrue(timeline["root_motion"])
        self.assertGreater(timeline["root_motion"][0]["delta_x"], 0)
        self.assertEqual(timeline["camera"]["mode"], "follow")

    def test_space_entrypoint_has_zerogpu_decorator(self) -> None:
        source = (HF / "app_v04.py").read_text(encoding="utf-8")
        self.assertIn("import spaces", source)
        self.assertIn("@spaces.GPU(duration=_zerogpu_duration)", source)
        self.assertIn("def create_animation_video(", source)
        self.assertIn('api_name="render_mp4"', source)
        self.assertNotIn('request_space_hardware', source)


if __name__ == "__main__":
    unittest.main()
