from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_V04 = ROOT / "hf_space" / "app_v04.py"
APP_V06 = ROOT / "hf_space" / "app_v06.py"


class OyenCPUZeroGPUContractTests(unittest.TestCase):
    def test_new_entrypoint_compiles(self) -> None:
        source = APP_V06.read_text(encoding="utf-8")
        compile(source, str(APP_V06), "exec")

    def test_blender_render_callback_is_cpu_only(self) -> None:
        source = APP_V06.read_text(encoding="utf-8")
        marker = "def create_animation_video("
        start = source.index(marker)
        prefix = source[max(0, start - 120):start]
        self.assertNotIn("@spaces.GPU", prefix)
        self.assertIn("render_2d_job(job, OUTPUT_DIR, timeout=420)", source)

    def test_zero_gpu_probe_remains_registered(self) -> None:
        source = APP_V06.read_text(encoding="utf-8")
        self.assertIn("@spaces.GPU(duration=1)", source)
        self.assertIn("def zerogpu_healthcheck()", source)
        shim = APP_V04.read_text(encoding="utf-8")
        self.assertIn("from app_v06 import demo", shim)


if __name__ == "__main__":
    unittest.main()
