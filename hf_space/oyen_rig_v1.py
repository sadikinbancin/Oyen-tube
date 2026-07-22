from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PARTS_DIR = Path(__file__).resolve().parent / "rig_parts"
_PART_NAMES = (
    "oyen_rig_v1_01.txt",
    "oyen_rig_v1_02.txt",
    "oyen_rig_v1_03.txt",
    "oyen_rig_v1_04.txt",
    "oyen_rig_v1_04b.txt",
    "oyen_rig_v1_05.txt",
)


def _load_template() -> str:
    chunks: list[str] = []
    for name in _PART_NAMES:
        path = _PARTS_DIR / name
        if not path.is_file():
            raise FileNotFoundError(f"Oyen rig template part is missing: {path}")
        chunks.append(path.read_text(encoding="utf-8"))
    template = "".join(chunks)
    if "__JOB_JSON__" not in template:
        raise RuntimeError("Oyen rig template does not contain the job marker")
    return template


def build_rigged_script(job: dict[str, Any]) -> str:
    """Build a standalone Blender script containing Oyen Purba Motion AI V0.5."""
    job_json = json.dumps(job, ensure_ascii=False, indent=2)
    return _load_template().replace("__JOB_JSON__", job_json)
