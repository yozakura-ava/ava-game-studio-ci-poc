"""Minimal game-content manifest validator (PoC scale).

Demonstrates the studio's asset-completeness concept in miniature:
a manifest is invalid if it references assets missing from disk, or
declares endings that reference undeclared scenes. Fail-closed.
"""
from __future__ import annotations

import json
from pathlib import Path


def validate_manifest(manifest: dict, asset_root: Path) -> list[str]:
    errors: list[str] = []
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        return ["manifest declares no assets (fail-closed)"]

    for asset in assets:
        rel = asset.get("path")
        if not rel:
            errors.append("asset entry missing 'path'")
            continue
        target = asset_root / rel
        if not target.is_file():
            errors.append(f"missing asset on disk: {rel}")
        if asset.get("required", True) and asset.get("state") != "integrated":
            errors.append(f"required asset not integrated: {rel} (state={asset.get('state')!r})")

    scenes = {s.get("id") for s in manifest.get("scenes", []) if isinstance(s, dict)}
    endings = [e for e in manifest.get("endings", []) if isinstance(e, dict)]
    if not endings:
        errors.append("manifest declares no endings (fail-closed)")
    for ending in endings:
        if ending.get("scene") not in scenes:
            errors.append(f"ending references undeclared scene: {ending.get('scene')!r}")
    return errors


def load_and_validate(manifest_path: Path, asset_root: Path) -> list[str]:
    with manifest_path.open() as fh:
        return validate_manifest(json.load(fh), asset_root)
