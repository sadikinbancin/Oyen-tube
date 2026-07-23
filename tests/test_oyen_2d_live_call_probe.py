from __future__ import annotations

import json
import time
import unittest
import urllib.error
import urllib.request


BASE = "https://lako123-belajarh-ani.hf.space"


def request(url: str, *, payload: dict | None = None, timeout: int = 60) -> tuple[int, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "oyen-v06-live-call-probe",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


class OyenV06LiveCallProbe(unittest.TestCase):
    def test_capture_live_render_error(self) -> None:
        payload = {
            "data": [
                "Oyen berjalan ke kanan, menoleh ke kamera, melambaikan tangan, lalu tersenyum dan mengibaskan ekornya.",
                "2D Cutout Blender",
                "Oyen Purba Brand Sheet",
                3,
                "9:16",
                12,
                "360p cepat",
                False,
            ]
        }
        code, body = request(f"{BASE}/gradio_api/call/render_mp4", payload=payload)
        print(f"OYEN_LIVE_CALL_POST http={code} body={body[:12000]}")
        event_id = None
        try:
            event_id = json.loads(body).get("event_id")
        except Exception:
            pass
        if event_id:
            time.sleep(2)
            code, stream = request(
                f"{BASE}/gradio_api/call/render_mp4/{event_id}",
                timeout=540,
            )
            print(f"OYEN_LIVE_CALL_STREAM http={code} body={stream[-30000:]}")
        self.assertIn(code, {0, 200, 400, 404, 408, 422, 429, 500, 502, 503, 504})


if __name__ == "__main__":
    unittest.main()
