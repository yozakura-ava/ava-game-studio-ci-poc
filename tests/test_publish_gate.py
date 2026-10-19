"""Real tests for the publish gate's check functions (all fixtures synthetic,
constructed at runtime; nothing forbidden is ever committed)."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "publish_gate", Path(__file__).resolve().parents[1] / "publish" / "publish_gate.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

# Synthetic token built at runtime — pattern-matching shape, obviously fake value.
# (Constructed from short pieces so no literal in this file trips the gate itself.)
SYNTHETIC_TOKEN = "ghp_" + "SYNTHETICINVALID" + "TOKEN" + "0" * 19
SYNTHETIC_KEY_BLOCK = ("-----BEGIN RSA " + "PRIVATE KEY-----").encode()


class PublishGateTests(unittest.TestCase):
    def setUp(self):
        self.allow = gate.load_allowlist()

    def test_allowlist_loads_and_is_deny_by_default(self):
        self.assertGreater(len(self.allow["paths"]), 0)
        self.assertFalse(gate.path_allowed("some/random/path.txt", self.allow))

    def test_allowed_file_passes_all_checks(self):
        data = b"# just a normal comment\nprint('hello')\n"
        self.assertEqual(gate.check_file("src/main.py", data, len(data), self.allow), [])

    def test_env_file_is_denylisted(self):
        v = gate.check_file("publish/sample.env", b"X=1", 3, self.allow)
        self.assertTrue(any("denylist" in str(x) for x in v), v)

    def test_path_outside_allowlist_blocked(self):
        v = gate.check_file("notes/leak.txt", b"hello", 5, self.allow)
        self.assertTrue(any("not in allowlist" in str(x) for x in v), v)

    def test_disallowed_file_type_blocked(self):
        v = gate.check_file("demo/assets/sprite.bin", b"\x00\x01", 2, self.allow)
        self.assertTrue(any("type not allowed" in str(x) for x in v), v)

    def test_synthetic_secret_token_blocked(self):
        content = (f"token = {SYNTHETIC_TOKEN}\n").encode()
        v = gate.check_file("demo/config.txt", content, len(content), self.allow)
        self.assertTrue(any("GitHub token" in str(x) for x in v), v)

    def test_private_key_block_blocked(self):
        content = SYNTHETIC_KEY_BLOCK + b"\nabc\n"
        v = gate.check_file("demo/key.txt", content, len(content), self.allow)
        self.assertTrue(any("private key" in str(x) for x in v), v)

    def test_high_entropy_string_blocked(self):
        # Blob assembled at runtime from short pieces so the fixture literal
        # itself cannot trip the entropy scanner on this repo's own source.
        blob = "Kv9" + "zQ7xL2mW4nR8tY6uI3oP5" + "aS1dF0gH7jK4lZ9" + "bV1cX"
        content = f"data = {blob}\n".encode()
        v = gate.check_file("demo/data.txt", content, len(content), self.allow)
        self.assertTrue(any("high-entropy" in str(x) for x in v), v)

    def test_oversize_file_blocked_fail_closed(self):
        v = gate.check_file("demo/big.txt", b"a" * 64, 2 * 1024 * 1024, self.allow)
        self.assertTrue(any("max_bytes" in str(x) for x in v), v)

    def test_tree_scan_clean_on_self(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(gate.scan_tree(root), [])


if __name__ == "__main__":
    unittest.main()
