---
date: 2026-10-05
type: sprint-change-proposal
trigger: Dependabot — 5 open alerts on master (2 high, 3 moderate)
status: approved 2026-10-05 — owner-directed remediation; folded into spec-e4 story 10 + memlog
owner: vshanbha
decided: 2026-10-05
decisions:
  D16: A — bump transitive oauthlib to 4.0.0 and urllib3 to 2.8.0 in uv.lock
epics_impacted: [E4]
artifacts_impacted: [spec-e4-ops-eval-polish, sprint-status, uv.lock]
mode: single
---

# Sprint Change Proposal — text-c3po v2 (2026-10-05)

Triggered by the Dependabot alert banner surfaced on the 2026-10-05 push of
commit `1371657`: "GitHub found 5 vulnerabilities on vshanbha/text-c3po's
default branch (2 high, 3 moderate)." Owner-directed: fix and follow the
BMAD process.

## Section 1 — Issue Summary

**Trigger.** Dependabot reports 5 open alerts on `master` (2 high, 3
moderate). The GitHub REST Dependabot endpoint is not reachable with the
current PAT (`Resource not accessible by personal access token`, missing
`security_events` scope), so the list was reconstructed from the OSV/GitHub
advisory database against the locked dependency set. It matches the banner
exactly: 2 high + 3 moderate across two transitive packages.

**Problem statement.** Two transitive dependencies pinned in `uv.lock`
carry known advisories:

| Package | Locked | GHSA | Severity | Fixed | Issue |
|---|---|---|---|---|---|
| urllib3 | 2.7.0 | GHSA-8988-9cw3-xx77 | **high** | 2.8.0 | HTTPS proxy TLS configuration ignored/overridden |
| urllib3 | 2.7.0 | GHSA-vxq7-64xx-v4gw | **high** | 2.8.0 | `stream()`/`read_chunked()` buffers an unbounded chunk-size line |
| urllib3 | 2.7.0 | GHSA-gh4c-6fx4-qh6g | moderate | 2.8.0 | Chunked-deflate streaming can loop forever |
| oauthlib | 3.3.1 | GHSA-hj66-6f7g-4r5v | moderate | 4.0.0 | Unsafe JSONP callback injection in `RevocationEndpoint` |
| oauthlib | 3.3.1 | GHSA-xpv3-w29h-x7cv | moderate | 4.0.0 | Timing attack in PKCE `code_verifier` comparison (CWE-208) |

**Provenance.** Neither package is a direct dependency.
- `oauthlib` is pulled by `flet` (`oauthlib>=3.2.2`, no upper bound — line
  192 of `uv.lock`).
- `urllib3` is pulled by `requests` (`>=1.21.1,<3`), which arrives via the
  `langchain-ollama` → `langchain-core` → `langsmith` → `requests` chain
  (`ollama` itself depends only on httpx and pydantic).

text-c3po uses neither flet's OAuth auth flow nor `requests` at runtime
(the app is loopback-only stdlib HTTP), so both advisories are
reachable-but-unexercised in this product; they still ship in the lock and
must be remediated.

**Evidence.**
- `uv.lock:461-467` — oauthlib 3.3.1
- `uv.lock:833-839` — urllib3 2.7.0
- `uv.lock:192` — flet depends on oauthlib
- `uv.lock:726-734` — requests 2.34.2 depends on urllib3
- OSV querybatch over the exported lock: 10 advisory records → 5 distinct
  GHSA advisories after alias collapse (2 high + 3 moderate)

## Section 2 — Impact Analysis

**Epic impact.** E4 only (Ops, Eval & Polish). No product behavior, UI, or
architecture change. E1–E3 and E5 are untouched.

**Files changed (blast radius).**

| File | Change |
|---|---|
| `uv.lock` | oauthlib 3.3.1 → 4.0.0; urllib3 2.7.0 → 2.8.0 (6 insertions / 6 deletions, no other package moved) |
| `_bmad-output/planning-artifacts/epics.md` | Add E4 story 10 (and close the missing 4.9 entry) |
| `_bmad-output/specs/spec-e4-ops-eval-polish/stories.yaml` | Add story id 10 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Add `4-10-…` → done; bump `last_updated` |
| `_bmad-output/specs/spec-e4-ops-eval-polish/.memlog.md` | Append decision + event |

**Files NOT changed.**
- `pyproject.toml` / `requirements.txt` — direct deps unchanged; the project
  pins direct deps only and tracks transitive resolution in `uv.lock` (D6-B).
  `test_dependency_pins_agree` still holds.
- No `src/` or `tests/` change — this is a lockfile-only remediation.

**No rollback required.** Both bumps are within constraints flet and
requests already declare; the previous lock is preserved in history.

## Section 3 — Recommended Approach

**Option 1: In-range transitive bump via `uv lock --upgrade-package`
(recommended).** Raise the two packages to their first-patched versions and
regenerate only those lock entries. oauthlib's major bump (3→4) is
permitted by flet's unbounded `>=3.2.2`; the app never calls flet auth, so
the major API surface is inert here. Effort: Low. Risk: Low.

**Option 2: Add explicit `[tool.uv]` constraints / overrides.** Force the
floor without moving the lock. Rejected: overrides are a heavier, more
surprising mechanism than simply taking the patched versions, and would
need ongoing maintenance.

**Option 3: Do nothing; document as accepted.** Rejected: the owner
directed remediation, and both advisories have patches.

Rationale: Option 1 is the minimal, constraint-respecting fix and is
reproducible (`uv sync --frozen` on a clean machine picks up the patched
lock).

## Section 4 — Detailed Change Proposal

### D16 — Bump transitive oauthlib and urllib3 to first-patched versions

- **Affected:** E4 story 10, `uv.lock`.
- **Options.**
  - **A (recommended) — in-range upgrade.** `uv lock --upgrade-package
    oauthlib --upgrade-package urllib3` → oauthlib 4.0.0, urllib3 2.8.0.
  - **B — constraint/override floor.** Pin floors in `pyproject.toml`;
    more surface, no benefit here.
  - **C — accept and document.** Contradicts the owner directive.
- **Rationale:** A is the smallest correct change and keeps the lock as the
  single transitive source of truth (D6-B).
- **Success criteria:**
  1. `oauthlib==4.0.0` and `urllib3==2.8.0` in `uv.lock`.
  2. `uv lock --check` clean; no other package version moved.
  3. `pip-audit -r <exported lock>` reports no known vulnerabilities.
  4. OSV querybatch over the exported lock reports 0 advisory hits.
  5. Unit suite green (207 passed, 6 deselected); `compileall` clean.
  6. Dependabot alerts on `master` clear after push (5 → 0).

## Section 5 — Implementation Handoff

- **Scope classification:** **Trivial** — one lockfile bump plus tracking
  updates; no replan, no code change.
- **Prerequisite:** none (owner already directed the fix).
- **Recommended story structure:** single story, E4 story 10
  (`4-10-remediate-dependabot-dependency-vulnerabilities`).
- **Owner override needed:** none.
- **Spec ownership rule:** decisions append to the owning `.memlog.md`;
  `SPEC.md` is not hand-edited (no capability change here).
- **Tracking:** add story 10 to `epics.md` + `stories.yaml`; mark
  `4-10-…` done in `sprint-status.yaml`.

## Decision register (approve / edit / skip)

| ID | Decision to make | Recommendation | Proposed downstream story |
|----|------------------|----------------|---------------------------|
| D16 | Dependency remediation approach | A — in-range bump to patched versions | E4 story 10 |

## Approval record

Approved 2026-10-05 by owner vshanbha: **D16-A — bump oauthlib to 4.0.0 and
urllib3 to 2.8.0 in `uv.lock`.** Owner directive: "Fix the vulnerabilities.
follow the BMAD process and push commits."

Next: implement the lock bump, verify (pip-audit + OSV + unit suite), review,
commit, push, and confirm the Dependabot alerts clear.
