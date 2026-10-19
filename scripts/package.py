"""Build the PoC bundle artifact: dist/ava-game-studio-ci-poc.zip (stdlib only)."""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
OUT = DIST / "ava-game-studio-ci-poc.zip"

INCLUDE_DIRS = ["src", "demo", "publish", "scripts"]
INCLUDE_FILES = ["README.md", "Makefile"]

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for d in INCLUDE_DIRS:
        for path in sorted((ROOT / d).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(ROOT))
    for name in INCLUDE_FILES:
        p = ROOT / name
        if p.is_file():
            zf.write(p, name)

with zipfile.ZipFile(OUT) as zf:
    names = zf.namelist()
    assert names, "bundle is empty — build must fail closed"
    bad = zf.testzip()
    assert bad is None, f"corrupt member in bundle: {bad}"

print(f"packaged {len(names)} files -> {OUT} ({OUT.stat().st_size} bytes)")
