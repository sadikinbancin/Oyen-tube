from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "hf_space" / "app_v04.py"


class Oyen2DSSRContractTests(unittest.TestCase):
    def test_gradio_ssr_is_disabled_for_zero_gpu_api_calls(self) -> None:
        source = APP.read_text(encoding="utf-8")
        self.assertIn("launch(ssr_mode=False)", source)
        self.assertNotIn("launch()", source)


if __name__ == "__main__":
    unittest.main()
