# ava-game-studio-ci-poc

Proof-of-capability repository for the Ava Autonomous Game-Development Studio
architecture (Phase 0). Content: fully synthetic, non-personal, non-NSFW test
material only.

## What this repo demonstrates

1. **Automated repository creation** — created via GitHub CLI by the studio
   orchestrator, private by default.
2. **Scaffolding** — uniform task verbs (`make setup|validate|lint|test|build`),
   stdlib-only (zero dependencies to install in CI).
3. **Functioning CI** — `.github/workflows/ci.yml`: sanitization gate → tests →
   package + artifact, with `needs:` ordering so packaging cannot run unless
   gate and tests are green.
4. **A real passing test suite** — `tests/` exercises the publish gate's
   check functions (allowlist, denylist, secret patterns, entropy, size) and a
   miniature asset-completeness manifest validator. Fail-closed semantics.
5. **A deliberately failing test** — demonstrated on a temporary branch
   (see `docs/evidence.md`); CI went red on that branch and the branch was
   deleted. `main` is never left broken.
6. **A build artifact** — `make build` produces `dist/ava-game-studio-ci-poc.zip`;
   CI uploads it as a workflow artifact.
7. **Content sanitization before any push** — `publish/publish_gate.py`
   (allowlist-first; denylist, secret-pattern, high-entropy and size backstops;
   fail-closed on everything unknown) runs:
   - locally as a **git pre-push hook** (installed by `make setup`), scanning
     every object in the push, **and**
   - CI-side on every push and PR (tree mode).
8. **Clean-clone reproduction** — see below.

## Clean-clone reproduction

```bash
git clone <repo-url> ava-game-studio-ci-poc
cd ava-game-studio-ci-poc
make setup      # installs the pre-push publish gate
make lint       # gate + syntax compile
make test       # all unit tests
make build      # produces dist/ava-game-studio-ci-poc.zip
```

Expected: `make lint` prints `publish-gate: clean`, `make test` reports all
tests OK, `make build` reports the packaged file count and size.

## Architecture notes

- **Allowlist-first**: only paths/types listed in `publish/allowlist.json` may
  exist; anything else blocks the gate. Adding a new content class is a visible,
  reviewable manifest change.
- **Fail-closed**: unknown paths, unknown types, oversize files, undecodable
  content, ambiguous cases — all block.
- The manifest validator (`src/manifest.py`) is a miniature of the studio's
  asset-completeness gate: no release validation can pass while required assets
  are missing or endings reference undeclared scenes.

## Evidence

Run URLs, commit SHAs, and the deliberate-failure/gate-block demonstrations are
recorded in `docs/evidence.md` (kept current by the orchestrator).
