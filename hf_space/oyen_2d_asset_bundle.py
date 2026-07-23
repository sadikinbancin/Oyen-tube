from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PART_DIR = HERE / "oyen_2d_asset_parts"
EXPECTED_PARTS = 12
EXPECTED_SHA256 = "095f3bed0cb17e60a53fcfccf65574bb7dc601f423373769e83644e3fe7d3b49"
MANIFEST_MEMBER = "oyen_2d_layer_manifest.json"


class Oyen2DAssetError(RuntimeError):
    """Raised when the committed Oyen 2D asset bundle is incomplete or corrupted."""


def _parts() -> list[Path]:
    parts = sorted(PART_DIR.glob("oyen_2d_assets.part*.b64"))
    if len(parts) != EXPECTED_PARTS:
        raise Oyen2DAssetError(
            f"Paket aset Oyen 2D tidak lengkap: {len(parts)} dari {EXPECTED_PARTS} part"
        )
    return parts


@lru_cache(maxsize=1)
def asset_zip_bytes() -> bytes:
    encoded = "".join(path.read_text(encoding="ascii").strip() for path in _parts())
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:  # pragma: no cover - defensive corruption guard
        raise Oyen2DAssetError(f"Base64 aset Oyen 2D rusak: {exc}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise Oyen2DAssetError(
            f"Checksum aset Oyen 2D salah: {digest}; expected {EXPECTED_SHA256}"
        )
    return raw


def materialize_asset_zip(cache_dir: str | Path | None = None) -> Path:
    root = (
        Path(cache_dir)
        if cache_dir is not None
        else Path(tempfile.gettempdir()) / "oyen_2d_asset_cache"
    )
    root.mkdir(parents=True, exist_ok=True)
    target = root / "oyen_2d_assets.zip"
    raw = asset_zip_bytes()
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != EXPECTED_SHA256:
        target.write_bytes(raw)
    return target


@lru_cache(maxsize=1)
def load_embedded_manifest() -> dict[str, Any]:
    with zipfile.ZipFile(materialize_asset_zip(), "r") as archive:
        try:
            payload = archive.read(MANIFEST_MEMBER)
        except KeyError as exc:
            raise Oyen2DAssetError(
                f"Manifest {MANIFEST_MEMBER} tidak ditemukan di paket aset"
            ) from exc
    manifest = json.loads(payload.decode("utf-8"))
    if manifest.get("schema_version") != "oyen.2d-layer-manifest.v1":
        raise Oyen2DAssetError("Schema manifest aset Oyen 2D tidak valid")
    return manifest


def validate_asset_bundle() -> dict[str, Any]:
    raw = asset_zip_bytes()
    with zipfile.ZipFile(materialize_asset_zip(), "r") as archive:
        names = archive.namelist()
        pngs = sorted(
            name for name in names if name.startswith("layers/") and name.endswith(".png")
        )
        manifest = load_embedded_manifest()
        missing = [
            item["file"]
            for item in manifest.get("layers", [])
            if item.get("rig_enabled", True) and item["file"] not in names
        ]
        if missing:
            raise Oyen2DAssetError(f"Layer PNG hilang dari ZIP: {missing}")
        for name in pngs:
            payload = archive.read(name)
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise Oyen2DAssetError(f"File bukan PNG valid: {name}")
    return {
        "zip_bytes": len(raw),
        "sha256": EXPECTED_SHA256,
        "part_count": EXPECTED_PARTS,
        "png_count": len(pngs),
        "layer_count": len(manifest.get("layers", [])),
        "active_layer_count": sum(
            1 for item in manifest.get("layers", []) if item.get("rig_enabled", True)
        ),
        "bone_count": len(manifest.get("bones", [])),
    }
