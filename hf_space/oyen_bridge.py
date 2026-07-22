from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from oyen_rig_template_01 import PART as PART_01
from oyen_rig_template_02 import PART as PART_02
from oyen_rig_template_03 import PART as PART_03
from oyen_rig_template_04 import PART as PART_04
from oyen_rig_template_05 import PART as PART_05
from oyen_rig_template_06 import PART as PART_06
from oyen_rig_template_07 import PART as PART_07

# Marker retained for validation: OyenPurba_Rig / OYEN_RIG_READY


def build_blender_script(job: dict[str, Any]) -> str:
    """Create a standalone Blender script for Oyen Purba 3D Rig V1."""
    job_json = json.dumps(job, ensure_ascii=False, indent=2)
    template = "".join([PART_01, PART_02, PART_03, PART_04, PART_05, PART_06, PART_07])
    return template.replace("__JOB_JSON__", job_json)


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
    return f"""# Oyen Purba 3D Rig V1

Job: `{job.get('job_id', 'unknown')}`

Paket ini membuat karakter utama **Oyen Purba** dalam Blender dengan armature nyata dan render MP4.

## Tulang utama

- root, pelvis, spine, chest, neck, head, jaw
- ear.L/R dan eye.L/R
- upper_arm, forearm, hand kiri/kanan
- thigh, shin, foot kiri/kanan
- lima tulang ekor

Model V1 memakai sistem segmented bone-parent rig. Sistem ini sengaja dipilih agar stabil dan tidak rusak oleh automatic weight painting pada model prosedural. Tahap produksi berikutnya adalah mesh terpadu, retopology, dan weight painting halus.

## Menjalankan

Windows: `run_blender.bat`

Linux/macOS:

```bash
chmod +x run_blender.sh
./run_blender.sh
```

## Output

```text
oyen_output/
├── oyen_preview.blend
└── oyen_preview.mp4
```
"""


def write_worker_package(job: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write JSON, rigged Blender script, launchers, and ZIP bundle."""
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
