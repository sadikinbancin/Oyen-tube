from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from oyen_rig_v1 import build_rigged_script


def build_blender_script(job: dict[str, Any]) -> str:
    """Create the standalone Blender script for Oyen Purba Rig V1."""
    return build_rigged_script(job)


def _run_script_sh() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
BLENDER_BIN="${BLENDER_EXECUTABLE:-blender}"
"$BLENDER_BIN" --background --factory-startup --enable-autoexec --python oyen_blender_scene.py
"""


def _run_script_bat() -> str:
    return r"""@echo off
setlocal
if "%BLENDER_EXECUTABLE%"=="" (
  set "BLENDER_BIN=blender"
) else (
  set "BLENDER_BIN=%BLENDER_EXECUTABLE%"
)
"%BLENDER_BIN%" --background --factory-startup --enable-autoexec --python oyen_blender_scene.py
if errorlevel 1 exit /b %errorlevel%
echo Oyen Purba Rig V1 selesai. Periksa folder oyen_output.
"""


def _package_readme(job: dict[str, Any]) -> str:
    return f"""# Oyen Purba Rig V1

Job: `{job.get('job_id', 'unknown')}`

Paket ini membuat karakter utama **Oyen Purba** dalam Blender dengan armature sungguhan.

## Tulang dan kontrol

- root, pelvis, spine, chest, neck, head, dan jaw
- tulang telinga kiri/kanan
- lengan atas, siku, tangan, paha, lutut, dan kaki
- lima ruas tulang ekor
- kontrol IK tangan/kaki dan pole targets
- walk cycle, body bounce, head turn, ear twitch, jaw motion, tail follow-through, dan wave

## Output

```text
oyen_output/
├── oyen_preview.blend
└── oyen_preview.mp4
```

File `.blend` menyimpan armature dan dapat dibuka untuk pose atau animasi lanjutan.
"""


def write_worker_package(job: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write JSON, rigged Blender script, launchers and a ZIP bundle."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    job_id = str(job.get("job_id", "oyen-job"))
    job_path = destination / f"{job_id}.json"
    script_path = destination / f"{job_id}_blender.py"
    zip_path = destination / f"{job_id}_worker.zip"

    job_text = json.dumps(job, ensure_ascii=False, indent=2)
    script_text = build_blender_script(job)
    job_path.write_text(job_text, encoding="utf-8")
    script_path.write_text(script_text, encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("animation_job.json", job_text)
        archive.writestr("oyen_blender_scene.py", script_text)
        archive.writestr("run_blender.sh", _run_script_sh())
        archive.writestr("run_blender.bat", _run_script_bat())
        archive.writestr("README.md", _package_readme(job))

    return {"json": str(job_path), "script": str(script_path), "zip": str(zip_path)}
