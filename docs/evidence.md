# PoC Evidence Record

All results from 2026-10-19. Repository: https://github.com/yozakura-ava/ava-game-studio-ci-poc (private).

## 1. Automated repository creation
- Created via GitHub CLI (`gh repo create --private --source`), private, under the
  `yozakura-ava` account. Verified via API (`gh repo view`).
- Transport note: the host SSH key authenticates to GitHub as a *different* account;
  pushes therefore use HTTPS + gh-token credential helper (repo-local config only).

## 2. CI green on `main`
- Run https://github.com/yozakura-ava/ava-game-studio-ci-poc/actions/runs/39314891636 —
  conclusion **success**, head `06b775fc61309c48f9db478fb16917777ec30936`.
- Jobs: content-sanitization gate → unit tests (15/15) → package + artifact upload,
  `needs:`-ordered so packaging cannot run unless gate and tests are green.

## 3. Deliberately failing test (temp branch, deleted after)
- Run https://github.com/yozakura-ava/ava-game-studio-ci-poc/actions/runs/39315054541 —
  conclusion **failure** (test `test_ci_must_be_able_to_fail`, message DELIBERATE).
- Branch `test/ci-failure-proof` deleted remotely and locally; `main` never broken.

## 4. Pre-push gate blocks a synthetic secret (fail-closed proof)
- Temp branch committed `demo/leak.txt` containing a runtime-constructed synthetic
  token (obviously fake, created solely for this test; never a real credential).
- Push attempt transcript:
  ```
  publish-gate: 1 violation(s) — BLOCKING
    BLOCKED demo/leak.txt: GitHub token pattern match
  error: failed to push some refs to 'https://github.com/yozakura-ava/ava-game-studio-ci-poc.git'
  ```
  Push exit 1; branch never reached the remote (`git ls-remote` shows only `main`).
  Local branch deleted immediately after the demonstration.

## 5. Sanitization ran before *every* push in this record
- The pre-push hook executed on each push; the first successful push printed
  `publish-gate: clean — all content within allowlist, no deny/secret hits` before transfer.

## 6. Additional fail-closed evidence (during development)
- The gate initially blocked its own repo scaffold: literal test fixtures tripped the
  private-key and high-entropy checks until fixtures were constructed at runtime.
- A gate bug (tree-object mishandled as blob) caused a gate crash — the push was
  **aborted**, proving fail-closed holds even when the gate itself fails.
  Fixed in commit `06b775f`.

## 7. Clean-clone reproduction
- Documented in README.md; verified locally: gate clean, 15/15 tests, package builds.
