"""Real tests for the manifest validator (asset-completeness concept, PoC scale)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "manifest", Path(__file__).resolve().parents[1] / "src" / "manifest.py"
)
manifest_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest_mod)


class ManifestTests(unittest.TestCase):
    def _tmp_assets(self, names):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for n in names:
            (root / n).write_text(f"synthetic asset {n}")
        return root

    def test_valid_manifest_passes(self):
        root = self._tmp_assets(["bg.txt", "hero.txt"])
        m = {
            "assets": [
                {"path": "bg.txt", "required": True, "state": "integrated"},
                {"path": "hero.txt", "required": True, "state": "integrated"},
            ],
            "scenes": [{"id": "s1"}],
            "endings": [{"id": "e1", "scene": "s1"}],
        }
        self.assertEqual(manifest_mod.validate_manifest(m, root), [])

    def test_missing_asset_fails_closed(self):
        root = self._tmp_assets(["bg.txt"])
        m = {
            "assets": [
                {"path": "bg.txt", "required": True, "state": "integrated"},
                {"path": "ghost.txt", "required": True, "state": "integrated"},
            ],
            "scenes": [{"id": "s1"}],
            "endings": [{"id": "e1", "scene": "s1"}],
        }
        errs = manifest_mod.validate_manifest(m, root)
        self.assertTrue(any("missing asset on disk: ghost.txt" in e for e in errs), errs)

    def test_ending_referencing_undeclared_scene_fails(self):
        root = self._tmp_assets(["bg.txt"])
        m = {
            "assets": [{"path": "bg.txt", "required": True, "state": "integrated"}],
            "scenes": [{"id": "s1"}],
            "endings": [{"id": "e1", "scene": "scene_that_does_not_exist"}],
        }
        errs = manifest_mod.validate_manifest(m, root)
        self.assertTrue(any("undeclared scene" in e for e in errs), errs)

    def test_empty_manifest_fails_closed(self):
        root = self._tmp_assets([])
        errs = manifest_mod.validate_manifest({"assets": []}, root)
        self.assertTrue(any("no assets" in e for e in errs), errs)

    def test_shipped_demo_manifest_is_valid(self):
        repo = Path(__file__).resolve().parents[1]
        errs = manifest_mod.load_and_validate(
            repo / "demo" / "game.json", repo / "demo" / "assets"
        )
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
