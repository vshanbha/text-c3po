---
title: 'Scaffold Flet app shell and pinned requirements'
type: 'feature'
created: '2026-09-08'
status: 'done'
baseline_revision: 'e70869cfd7da94f8f70a146ae0cc0a3dc32e8129'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/specs/spec-e1-shell-core/SPEC.md
  - _bmad-output/planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** No Flet v2 entry exists; the repo root still carries the v1 `streamlit_app.py` + cloud requirements, so E1 has no shell to build on.

**Approach:** Scaffold the `text-c3po/` layered-monolith seed (app entry plus `ui`/`services`/`runtimes` packages) with `flet==0.86.5` pinned exact, launching to one empty window.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; `ui` never imports `runtimes` internals (AD-1/AD-2); `flet==0.86.5` exact in `requirements.txt` (NFR-6); single window minimum 960x640 per DESIGN/EXPERIENCE; no secrets files.

**Never:** No translation, Ollama, whisper, sounddevice, or language-constant code in this story (owned by stories 3-6); no cross-imports from `live-translate/`; no changes to `streamlit_app.py`; no modal dialogs or extra windows.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cold launch | `python text-c3po/app.py` with deps installed | One native Flet window opens, empty content, title set | No error expected |
| Import-only | `python -c "import text_c3po.app"` (headless CI) | Module imports without launching a window or raising | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `requirements.txt` -- v1 cloud deps (`streamlit`, `langchain-openai`); will be fully rewritten to the `flet==0.86.5` pin.
- `streamlit_app.py` -- v1 entry; READ-ONLY, must not be modified.
- `blueprint.md` -- section 3 dependency floor and section 7 Flet-churn risk; pin rationale.
- `text-c3po/` -- DOES NOT EXIST; greenfield scaffold target per ARCHITECTURE-SPINE structural seed.
- `AGENTS.md` -- repo policy: product code inside `text-c3po/`, `flet==exact` pin, no secrets.

## Tasks & Acceptance

**Execution:**
- `requirements.txt` -- rewrite to `flet==0.86.5` exact pin (plus only what the shell imports) -- removes cloud v1 deps per SPEC loopback-only constraint.
- `text-c3po/__init__.py` -- create package marker -- establishes the `text-c3po/` product root.
- `text-c3po/app.py` -- create Flet entry with `main()` + `ft.app(target=main)` guard wiring an empty single `Page` (title, 960x640 minimum) -- the CAP-1 shell later stories attach views to.
- `text-c3po/ui/__init__.py` -- create empty package marker -- reserves the UI layer per AD-1.
- `text-c3po/services/__init__.py` -- create empty package marker -- reserves the services layer per AD-1.
- `text-c3po/runtimes/__init__.py` -- create empty package marker -- reserves the runtimes layer per AD-1.

**Acceptance Criteria:**
- Given deps installed, when the implementer runs the app entry, then exactly one Flet window opens with empty content and no exception.
- Given a headless environment, when the implementer imports the app module, then the import succeeds without launching a window.
- Given the repo root, when the implementer greps for secrets/cloud deps, then `requirements.txt` contains `flet==0.86.5` exact and no `streamlit`, `langchain-openai`, or key material exists under `text-c3po/`.
- Given the scaffold, when the implementer lists `text-c3po/`, then `app.py` plus `ui/`, `services/`, `runtimes/` packages exist and `ui/` imports nothing from `runtimes/`.

## Spec Change Log

## Review Triage Log

### 2026-09-08 — Review pass
- verdicts: 15 findings — high 0, medium 0, low 4, false 11, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: v1 entry left uninstallable after dep removal — spec mandates rewrite to flet pin with streamlit_app.py READ-ONLY; leaving v1 uninstallable is intended E1 replacement, not a defect.
  - `[false]` `[reject]` Blind: requirements lacks future v2 deps — spec Never forbids Ollama/whisper/sounddevice/language code in story 1; adding them would violate scope.
  - `[false]` `[reject]` Blind: app.py adds no root control/placeholder — spec requires empty single window; blank Page with no controls is the acceptance.
  - `[false]` `[reject]` Blind: no initial width/height, only mins — spec Tasks require title + 960x640 minimum only; DESIGN states minimum, not initial size.
  - `[false]` `[reject]` Blind: no run/smoke command or doc update — spec task list has no run-command deliverable; AGENTS.md TODO(E1) is future work for later stories.
  - `[false]` `[reject]` Blind: layer markers lack import guard/test — empty markers contain zero imports so ui-imports-runtimes violation cannot occur; guard would add unneeded complexity.
  - `[false]` `[reject]` Blind: no mic/file-upload/TCC/BlackHole handling — spec Never forbids whisper/sounddevice in story 1 (stories 3-6 own them); requesting them violates scope.
  - `[false]` `[reject]` Edge E1: page.window None crash — Page.window is non-optional Window with default_factory in flet 0.86.5 (verified in installed source); None case unreachable on desktop target.
  - `[false]` `[reject]` Edge E2: bare ImportError on missing flet — matrix expects ImportError to surface, which bare import satisfies (ModuleNotFoundError subclass); friendly wrapper would add branching beyond spec.
  - `[false]` `[reject]` Edge E3: ft.app display/port failure unhandled — display-unavailable is environment failure outside cold-launch matrix; loud traceback is correct behavior, not a defect.
  - `[false]` `[reject]` Edge E4: tiny display smaller than 960x640 overflows — 960x640 minimum is a DESIGN requirement; clamping to smaller would violate it.
  - `[low]` `[reject]` Edge E5 + Verif Other: literal import text_c3po.app fails on hyphen dir — real wording mismatch, but fix is a spec-matrix edit (path-based load already verified intent); rejected per no-spec-edit rule, flagged for story 2+ matrix correction.
  - `[low]` `[reject]` Verif V1: no committed automated title/size check — FakePage wiring check ran manually and passed (title, 960x640, update once); committing test infra adds new files beyond the 6-file task list in a repo with no test runner, more than a direct correction.
  - `[low]` `[reject]` Verif V2: verification hardcodes pin instead of reading requirements.txt — file was read directly (contains exactly flet==0.86.5) plus dry-run resolves 11 pkgs; changing commands to -r is a spec edit, rejected per no-spec-edit rule.
  - `[low]` `[reject]` Intent divergences R1/R4 runtime-vs-text (hyphen vs underscore, min vs initial, no execution trace) — descriptive only; code implements the policy-consistent readings (hyphen fs path, replace deps, empty markers, min-only, __main__ guard) with manual runtime checks noted above.

## Verification

**Commands:**
- `uv pip install --system --dry-run 'flet==0.86.5'` -- expected: resolves `flet==0.86.5` (verified 2026-09-08, 11 packages).
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.
- `python3 -c "import ast; ast.parse(open('text-c3po/app.py').read())"` -- expected: parses clean.

## Auto Run Result

Status: blocked
Blocking condition: no subagents

### Attempt 2026-09-08 (resume with task permission allow)

Status: blocked
Blocking condition: no subagents
Intent: folder-plus-id dispatch spec_folder=_bmad-output/specs/spec-e1-shell-core story_id=1; resume implementation per existing spec.
Action: set status in-progress, launched one synchronous implementation subagent per step-03 handoff. Launch rejected.
Exact tool error (verbatim):
Subagent failed (task_id: ses_f7e1bf2a1ffeVL7VIUGTkzX0p9): The user rejected permission to use this specific tool call.
Observed on disk (read, not executed): text-c3po/__init__.py, text-c3po/app.py, text-c3po/ui/__init__.py, text-c3po/services/__init__.py, text-c3po/runtimes/__init__.py exist as untracked files; requirements.txt reads flet==0.86.5. Implementation verification (install deps, headless launch) not run — blocked before Verify.

### Attempt 2026-09-08 (resume — implement plus verify plus review)

Status: done
Intent: folder-plus-id dispatch spec_folder=_bmad-output/specs/spec-e1-shell-core story_id=1; explicit resume overrides stale blocked status, implement plus verify then review.
Summary: scaffold verified complete per spec task list; 4-layer review triaged with zero patches, zero loopbacks.
Files changed:
- requirements.txt — v1 cloud deps replaced with exact flet==0.86.5.
- text-c3po/__init__.py — package marker.
- text-c3po/app.py — Flet entry main() + ft.app guard, title text-c3po, 960x640 mins, empty content.
- text-c3po/ui/__init__.py, services/__init__.py, runtimes/__init__.py — empty AD-1 layer markers.
- Removed stray text-c3po/.memlog.md scratch and __pycache__ dirs (non-spec artifacts).
Review breakdown: 15 findings — 11 false/reject (scope-excluded or refuted, incl. Page.window non-optional), 4 low/reject (hyphen import wording, missing committed title/size and pin-file tests, intent divergences — fixes would edit spec or add test files beyond the 6-file list in a repo with no runner). Patches applied: none. Deferred: none. Follow-up review recommended: false (zero patched entries).
Verification: uv pip install --system --dry-run 'flet==0.86.5' resolves 11 to install; uv run --with flet prints 0.86.5; ast.parse clean; importlib headless load with FakePage asserts title/mins/update once; grep for streamlit/langchain-openai/secrets under text-c3po/ clean.
Residual risks: native one-window eyeball not run headless (recommend python text-c3po/app.py on Mac); matrix literal import text_c3po.app needs wording correction in a later story (hyphen dir is policy, import verified via path load).
