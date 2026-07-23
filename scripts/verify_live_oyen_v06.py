from __future__ import annotations

import inspect
import json
import os
import shutil
from pathlib import Path
from typing import Any

from gradio_client import Client
from PIL import Image, ImageStat

SPACE_URL = "https://lako123-belajarh-ani.hf.space"
PROMPT = (
    "Oyen berjalan ke kanan, menoleh ke kamera, melambaikan tangan, "
    "lalu tersenyum dan mengibaskan ekornya."
)


def _client(token: str) -> Client:
    kwargs: dict[str, Any] = {"verbose": True}
    parameters = inspect.signature(Client).parameters
    if "token" in parameters:
        kwargs["token"] = token
    elif "hf_token" in parameters:
        kwargs["hf_token"] = token
    return Client(SPACE_URL, **kwargs)


def _collect_files(value: Any) -> list[Path]:
    found: list[Path] = []
    if value is None:
        return found
    if isinstance(value, dict):
        for item in value.values():
            found.extend(_collect_files(item))
        return found
    if isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_collect_files(item))
        return found
    if isinstance(value, Path):
        try:
            if value.is_file():
                found.append(value)
        except OSError:
            pass
        return found
    if isinstance(value, str):
        # Status Markdown and JSON outputs are strings too. Never treat long or
        # multiline response text as a filesystem path.
        if len(value) > 1024 or "\n" in value or "\r" in value:
            return found
        try:
            path = Path(value)
            if path.is_file():
                found.append(path)
        except (OSError, ValueError):
            pass
        return found
    candidate = getattr(value, "path", None) or getattr(value, "name", None)
    if candidate:
        found.extend(_collect_files(candidate))
    return found


def main() -> None:
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise RuntimeError("HF_TOKEN is empty")

    client = _client(token)
    probe = client.predict(api_name="/zerogpu_healthcheck")
    if "OYEN_ZEROGPU_READY" not in str(probe):
        raise RuntimeError(f"ZeroGPU compatibility probe failed: {probe}")

    result = client.predict(
        PROMPT,
        "2D Cutout Blender",
        "Oyen Purba Brand Sheet",
        3,
        "9:16",
        12,
        "360p cepat",
        False,
        api_name="/render_mp4",
    )
    print("LIVE_RESULT", repr(result)[:30000])
    if not isinstance(result, (list, tuple)) or len(result) < 8:
        raise RuntimeError(f"Unexpected result: {result}")
    if "Tahap 1–7 terverifikasi" not in str(result[0]):
        raise RuntimeError(f"Render status failed: {result[0]}")

    job = json.loads(str(result[3]))
    character = job["project"]["main_character"]
    if job.get("app_version") != "0.6.0":
        raise RuntimeError(f"Wrong app version: {job.get('app_version')}")
    if character["active_rig_layers"] < 35:
        raise RuntimeError(f"Too few layers: {character}")
    if character["bone_count"] < 25 or character["action_count"] != 7:
        raise RuntimeError(f"Invalid rig counts: {character}")

    paths = _collect_files(result)
    videos = [path for path in paths if path.suffix.lower() == ".mp4"]
    blends = [path for path in paths if path.suffix.lower() == ".blend"]
    sheets = [path for path in paths if path.suffix.lower() in {".jpg", ".jpeg"}]
    logs = [path for path in paths if path.suffix.lower() == ".log"]
    if not videos or not blends or not sheets or not logs:
        raise RuntimeError(f"Missing outputs: {paths}")

    video = max(videos, key=lambda path: path.stat().st_size)
    blend = max(blends, key=lambda path: path.stat().st_size)
    sheet = max(sheets, key=lambda path: path.stat().st_size)
    log = max(logs, key=lambda path: path.stat().st_size)
    if video.stat().st_size < 2048 or blend.stat().st_size < 10000:
        raise RuntimeError("MP4 or blend is too small")
    image = Image.open(sheet).convert("RGB")
    if sheet.stat().st_size < 2000 or max(ImageStat.Stat(image).var) < 35:
        raise RuntimeError("Contact sheet is blank or too small")

    proof = log.read_text(encoding="utf-8", errors="replace")
    for marker in (
        "OYEN_2D_ASSETS count=",
        "OYEN_2D_BONES count=",
        "OYEN_2D_ACTIONS count=7",
        "OYEN_2D_QA frames=5",
        "OYEN_2D_LIBRARY_ONLY true",
        "OYEN_2D_RENDER_SUCCESS",
    ):
        if marker not in proof:
            raise RuntimeError(f"Missing marker: {marker}")

    targets = {
        "/tmp/oyen-purba-2d-v06.mp4": video,
        "/tmp/oyen-purba-2d-v06.blend": blend,
        "/tmp/oyen-purba-2d-v06-contact-sheet.jpg": sheet,
        "/tmp/oyen-purba-2d-v06.log": log,
    }
    for target, source in targets.items():
        shutil.copy2(source, target)

    print(
        "OYEN_2D_V06_LIVE_RENDER_SUCCESS "
        f"layers={character['active_rig_layers']} "
        f"bones={character['bone_count']} "
        f"mp4={video.stat().st_size} blend={blend.stat().st_size} "
        f"sheet={sheet.stat().st_size}"
    )


if __name__ == "__main__":
    main()
