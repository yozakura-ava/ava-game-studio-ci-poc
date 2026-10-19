#!/usr/bin/env python3
"""Allowlist-first content publish gate — proof-of-capability (PoC).

Design per directive §3.3: allowlist is the PRIMARY control; denylist,
secret patterns and entropy checks are backstops. Fail-closed everywhere:
unknown/ambiguous => block.

Modes:
  --mode tree   scan the working tree (CI-side and `make validate`)
  --mode push   scan objects being pushed (reads refspecs from stdin,
                as invoked by the git pre-push hook)

Exit codes: 0 = clean, 1 = violations found (push aborted).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_PATH = ROOT / "publish" / "allowlist.json"

DENYLIST_PATTERNS = [
    "*.env", "*.env.*", "*.pem", "*.p12", "*.key", "id_rsa*", "*.sqlite",
    "*.sqlite3", "*.db-dump", "*.dump",
    "memory/**", "diary/**", "notes/**", "secrets/**",
]

SECRET_PATTERNS = [
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "API key (sk- prefix)"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
]

ENTROPY_RUN = re.compile(r"[A-Za-z0-9+/_=-]{32,}")
ENTROPY_THRESHOLD = 4.5  # bits per char

ZERO_SHA = "0" * 40


class Violation:
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason

    def __str__(self) -> str:
        return f"BLOCKED {self.path}: {self.reason}"


def load_allowlist() -> dict:
    with ALLOWLIST_PATH.open() as fh:
        return json.load(fh)


def path_allowed(path: str, allow: dict) -> bool:
    allowed = any(fnmatch.fnmatch(path, pat) for pat in allow["paths"])
    allowed = allowed or path in allow.get("explicit_files", [])
    return allowed


def type_allowed(path: str, allow: dict) -> bool:
    if path in allow.get("explicit_files", []):
        return True
    return Path(path).suffix.lower() in allow["file_types"]


def denylisted(path: str) -> bool:
    base = os.path.basename(path)
    return any(fnmatch.fnmatch(path, pat) for pat in DENYLIST_PATTERNS) or any(
        fnmatch.fnmatch(base, pat) for pat in DENYLIST_PATTERNS
    )


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    n = len(s)
    return -sum((f / n) * math.log2(f / n) for f in freq.values())


def content_violations(path: str, data: bytes) -> list[str]:
    reasons = []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["binary content in text-allowlisted path (fail-closed)"]
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            reasons.append(f"{label} pattern match")
    for run in ENTROPY_RUN.findall(text):
        if shannon_entropy(run) > ENTROPY_THRESHOLD:
            reasons.append(f"high-entropy string ({len(run)} chars, "
                           f"{shannon_entropy(run):.2f} b/c) — possible secret")
            break
    return reasons


def check_file(path: str, data: bytes, size: int, allow: dict) -> list[Violation]:
    out = []
    if denylisted(path):
        out.append(Violation(path, "denylisted path/name"))
    if not path_allowed(path, allow):
        out.append(Violation(path, "path not in allowlist"))
    if not type_allowed(path, allow):
        out.append(Violation(path, "file type not allowed"))
    if size > allow["max_bytes"]:
        out.append(Violation(path, f"file exceeds max_bytes ({size} > {allow['max_bytes']})"))
        return out
    for reason in content_violations(path, data):
        out.append(Violation(path, reason))
    return out


def scan_tree(root: Path) -> list[Violation]:
    allow = load_allowlist()
    violations = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "dist", "__pycache__")]
        for name in filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            data = full.read_bytes()
            violations.extend(check_file(rel, data, len(data), allow))
    return violations


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def scan_push() -> list[Violation]:
    allow = load_allowlist()
    violations = []
    refspecs = sys.stdin.read().strip().splitlines()
    if not refspecs:
        return [Violation("(stdin)", "push mode requires refspecs on stdin (fail-closed)")]
    for line in refspecs:
        parts = line.split()
        if len(parts) != 4:
            violations.append(Violation(line, "malformed refspec (fail-closed)"))
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == ZERO_SHA:
            continue  # ref deletion
        rev_range = local_sha if remote_sha == ZERO_SHA else f"{remote_sha}..{local_sha}"
        objects = git("rev-list", "--objects", rev_range).strip().splitlines()
        for obj in objects:
            bits = obj.split(" ", 1)
            if len(bits) != 2:
                continue  # commit objects carry no path
            sha, path = bits
            if path.endswith("/"):
                continue  # directory tree entry, not a blob
            if git("cat-file", "-t", sha).strip() != "blob":
                continue  # only blobs carry scannable content
            size = int(git("cat-file", "-s", sha).strip())
            if size > allow["max_bytes"]:
                violations.append(Violation(path, f"object exceeds max_bytes ({size})"))
                continue
            blob = subprocess.run(["git", "cat-file", "blob", sha],
                                  capture_output=True, check=True).stdout
            violations.extend(check_file(path, blob, size, allow))
    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["tree", "push"], required=True)
    args = ap.parse_args()
    violations = scan_push() if args.mode == "push" else scan_tree(ROOT)
    if violations:
        print(f"publish-gate: {len(violations)} violation(s) — BLOCKING")
        for v in violations:
            print(f"  {v}")
        return 1
    print("publish-gate: clean — all content within allowlist, no deny/secret hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
