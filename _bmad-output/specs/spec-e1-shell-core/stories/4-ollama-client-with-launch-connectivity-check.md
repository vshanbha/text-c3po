---
title: 'Ollama client with launch connectivity check'
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
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** The shell from stories 1-3 never contacts Ollama, so the user cannot tell whether the local model runtime is up and CAP-2 startup probing has nothing to build on.

**Approach:** Add `text-c3po/runtimes/ollama_client` probing `127.0.0.1:11434/api/tags` at startup with stdlib HTTP only, and extend the top strip with a connected / not-running status plus a Retry action that re-probes without restart.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; `ui` never imports `runtimes` internals (AD-1/AD-2) — `app.py` wires the probe and passes plain values plus a retry callback into the strip; loopback only to `http://127.0.0.1:11434` (AD-11); models listed live from `/api/tags` with names returned verbatim; status dot always paired with a text label (color never the sole signal); recoverable probe failure renders inline in the strip, no modal dialogs (AD-12); `flet==0.86.5` exact stays untouched in `requirements.txt`; no secrets files.

**Never:** No hard-coded model names anywhere including `lfm2.5` (default rule owned by story 5); no translation service, `ChatOllama`, `JsonOutputParser`, or output-card code (owned by story 6); no model `Dropdown` or Refresh control (owned by story 5); no whisper, sounddevice, VAD, or file-pipeline code (E2/E3 scope); no new third-party dependencies (`requests` arrives in E2 — stdlib `urllib` only); no cross-imports from `live-translate/`; no changes to `streamlit_app.py`, `requirements.txt`, or `languages.py`; no restyling of Flet Material defaults.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cold launch, Ollama up | `python text-c3po/app.py` with `ollama serve` running | Top strip shows connected state (success dot + "Ollama connected") within 5s | No error expected |
| Cold launch, Ollama down | `python text-c3po/app.py` with `ollama serve` stopped | Top strip shows not-running guidance ("Ollama isn't running. Start `ollama serve`, then Retry.") within 5s | Connection refused surfaces as not-running state, never a traceback or dialog |
| Retry recovers | Tap Retry after starting `ollama serve` | State flips to connected without restart | No error expected |
| Retry still down | Tap Retry with `ollama serve` still stopped | State stays not-running with guidance intact | No error expected |
| Slow Ollama | `/api/tags` slower than the probe timeout | Treated as not-running; Retry re-probes | Timeout surfaces as not-running state, never a hang past the 5s budget |
| Malformed /api/tags body | 200 with non-JSON or missing `models` key | Treated as not-running | Parse failure surfaces as not-running state, never raw to the UI |
| Connected, zero models | 200 with empty `models` list | Still connected (empty picker is story-5 scope) | No error expected |
| Headless build | Load app module with a FakePage | Strip builds with status controls and Retry wired, no window launched | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `text-c3po/runtimes/__init__.py` -- runtimes layer marker (AD-1); EXTEND re-export with the probe entry point, still never imported by `ui/`.
- `text-c3po/runtimes/ollama_client.py` -- DOES NOT EXIST; stdlib-only (`urllib.request`/`urllib.error`, `json`) probe of `http://127.0.0.1:11434/api/tags` with a ~2s timeout (inside the CAP-2 5s budget); exposes `OLLAMA_BASE_URL`, `OLLAMA_TAGS_URL`, `PROBE_TIMEOUT_S`, plus `check_ollama()` returning a small `(connected: bool, models: list[str])` result and `list_models()` returning verbatim `/api/tags` names; never raises on refused/timeout/malformed — those yield `connected=False`.
- `text-c3po/ui/top_strip.py` -- story-2/3 strip (`build_top_strip(on_mode_change)` returning single `Row` with the mode `SegmentedButton`); EXTEND signature to accept the startup status plus a retry callback (plain values only, no `runtimes` import) and render the same row with status dot (`ft.Container` 10px circle: success green connected / warning amber not-running) + text label + Retry control (`TextButton`/link-style, visible and focused in the not-running state).
- `text-c3po/app.py` -- story-3 entry mounting strip plus once-built views with `visible` toggling; EXTEND `main()` to probe once at startup via `runtimes.ollama_client`, pass the result into `build_top_strip`, and wire Retry to re-probe and refresh only the status controls (mode-switch `visible` toggling and input preservation untouched).
- `text-c3po/ui/__init__.py` -- UI layer re-export surface; EXTEND only if the strip exposes a new status-refresh helper (still never imports `runtimes`).
- `requirements.txt` -- exact `flet==0.86.5` pin; READ-ONLY for this story (stdlib only, zero new deps).
- `streamlit_app.py`, `text-c3po/languages.py` -- READ-ONLY, must not be modified.
- `_bmad-output/specs/spec-e1-shell-core/stories/2-top-strip-with-three-mode-switching.md` -- prior-story continuity: reuse its FakePage-headless verification pattern; carry forward its residual risk (native one-window eyeball still needs a Mac run).
- `_bmad-output/specs/spec-e1-shell-core/stories/3-ship-the-23-language-constant-and-pickers.md` -- prior-story continuity: forbidden-token grep now allows `ollama` in `runtimes/ollama_client.py` + `app.py` wiring and `model` for the verbatim names list; `translat`, `whisper`, `sounddevice` stay forbidden and `lfm2.5` stays forbidden everywhere (story-5 owned).

## Tasks & Acceptance

**Execution:**
- `text-c3po/runtimes/ollama_client.py` -- create the stdlib-only probe (`check_ollama()` + `list_models()` + URL/timeout constants, `connected=False` on any refused/timeout/malformed path, model names verbatim from `/api/tags`) -- the CAP-2 runtime side stories 5-6 build on.
- `text-c3po/ui/top_strip.py` -- extend `build_top_strip()` with status dot + label + Retry over plain parameters (no `runtimes` import) -- the CAP-2 strip surface wired once and reused by later stories without rework.
- `text-c3po/app.py` -- extend `main()` to probe at startup and wire Retry to re-probe plus refresh status controls -- the CAP-2 no-restart recovery path.
- `text-c3po/runtimes/__init__.py` -- extend re-exports with the probe entry point -- keeps the runtimes layer's single import surface per AD-1.

**Acceptance Criteria:**
- Given `ollama serve` running, when the app cold-launches, then the top strip shows the connected state within 5s.
- Given `ollama serve` stopped, when the app cold-launches, then the top strip shows the not-running guidance with a Retry action within 5s and no traceback or dialog.
- Given the not-running state, when the implementer starts `ollama serve` and taps Retry, then the state flips to connected without restart; when the runtime is still down and Retry is tapped, then the not-running guidance stays intact.
- Given a refused connection, a probe timeout, or a malformed `/api/tags` body, when the probe runs, then the result is not-running with no exception escaping to the UI.
- Given the finished tree, when the implementer greps under `text-c3po/`, then no import of `runtimes` appears in `ui/`, no `lfm2.5` literal exists anywhere, and no `translat`, `whisper`, or `sounddevice` symbols exist outside comments and placeholder copy.
- Given a headless environment, when the implementer loads the app module with a FakePage, then the strip plus status controls plus Retry build with Text selected and visible, with no window launched and no exception.

## Spec Change Log

## Review Triage Log

### 2026-09-08 — Review pass
- verdicts: 26 findings — high 0, medium 0, low 6, false 20, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind B1: `from runtimes`/`from ui`/`from languages` unresolvable without sys.path setup — `python text-c3po/app.py` prepends the script dir so all resolve; headless import plus main build pass.
  - `[false]` `[reject]` Blind B2: hyphen dir `text-c3po/` not a valid package for absolute imports — same script-dir resolution as B1; no rename needed, headless build OK.
  - `[false]` `[reject]` Blind B3: SegmentedButton allows multi-select while handler honors only `selected[0]` — verified flet 0.86.5 defaults `allow_empty_selection=False, allow_multiple_selection=False`; multi-select unreachable.
  - `[false]` `[reject]` Blind B4: five pickers hold unsynchronized states across modes — spec requires independent pickers built once with selections surviving switches; cross-mode sync is story-6 scope, not required.
  - `[false]` `[reject]` Blind B5: blocking `check_ollama()` on the UI thread freezes startup — `PROBE_TIMEOUT_S=2.0` inside the CAP-2 5s budget by design; no hang past budget, no async required.
  - `[false]` `[reject]` Blind B6: probe never checks HTTP status code so non-200 with shaped JSON counts connected — `urllib` raises `HTTPError` (an `Exception` subclass, verified) on non-200, caught to `None` yielding not-running.
  - `[false]` `[reject]` Blind B7: single malformed entry discards all valid names reporting not-running — spec mandates malformed body maps to not-running; strictness is the specified behavior.
  - `[false]` `[reject]` Blind B8: `app.py` discards probe model names with no picker or empty-list message — model `Dropdown`/Refresh explicitly owned by story 5 per Never; discarding is expected.
  - `[low]` `[reject]` Blind B9: `refresh_ollama_status` flips `autofocus` without moving keyboard focus — initial `autofocus=not connected` satisfies the not-running focus state; refresh focus-move unproven with no everyday harm shown and the fix adds focus-API complexity.
  - `[low]` `[reject]` Blind B10: no expand/spacing/scroll/wrap so 960x640 may clip status label and pickers — row/column render correctly; no named runtime harm shown and the fix adds layout complexity beyond spec.
  - `[false]` `[reject]` Blind B11: `app.py` imports `runtimes` directly bypassing `services` — intent-contract explicitly sanctions `app.py` wiring the probe with plain values into the strip; `ui/` never imports `runtimes` verified clean.
  - `[false]` `[reject]` Blind B12: `__init__` docstrings advertise whisper/audio/process/session/translation/VAD/harness that do not exist — aspirational layer docs with no runtime harm; vague messiness with no named caller divergence.
  - `[false]` `[reject]` Blind B13: `LANGUAGES` mutable with no freeze/guard — static literal copied verbatim from blueprint 2.1 with no dynamic input path; loudly failing on never-shown corruption is correct (same as story 3 E4).
  - `[false]` `[reject]` Blind B14: source+target both default `en` (English-to-English, no auto-detect) — spec mandates `en` defaults with no `auto` entry until E2/E3; story-4 out of scope.
  - `[false]` `[reject]` Blind B15: `requirements.txt` holds only `flet==0.86.5` with no run docs — rewrite hunk is story-1 work predating this baseline; this story's Never freezes the file and the pin verifies `0.86.5`.
  - `[false]` `[reject]` Edge E1: mode value missing from views dict blanks the window — SegmentedButton only yields its own segment values with `allow_empty_selection=False` (verified default); no reachable outside value.
  - `[false]` `[reject]` Edge E2: mode event without control crashes handler — framework `on_change` contract always delivers a ControlEvent with control; defensive getattr adds branching for an unreachable case.
  - `[false]` `[reject]` Edge E3: strip built without retry callback leaves Retry inert — `app.py` always passes `on_retry`; `None` occurs only in isolation, never on the app path.
  - `[false]` `[reject]` Edge E4: `strip.data` missing refs leaves status stale — strip is always built by `build_top_strip` which sets `data={dot,label,retry}`; no reachable missing-refs path on the app wiring.
  - `[false]` `[reject]` Edge E5: default `en` absent from LANGUAGES blanks pickers — `en` present verified among 23 verbatim entries; empty/absent unreachable from the static literal.
  - `[false]` `[reject]` Edge E6: LANGUAGES entry missing code/name raises KeyError — same static literal guarded upstream; no reachable malformed-entry path.
  - `[false]` `[reject]` Edge E7: double-tap Retry overlaps blocking probes freezing the UI — single-threaded Flet runs probes sequentially within the 2s budget; no concurrent overlap path.
  - `[low]` `[reject]` Edge E8: unbounded `/api/tags` body exhausts memory/time — local loopback model list is small with no attacker path; read-limit fix adds branching for an unlikely everyday encounter.
  - `[low]` `[reject]` Verif V1: probe failure contract has no asserting check — real committed-coverage gap, but headless matrix asserts refused/timeout/malformed/missing-key yield `(False,[])`, empty yields `(True,[])`, verbatim names pass 11/11 plus live probe `True`; committed-test fix rejected for the runner-less reason (no test files exist; spec file list enumerates product files only).
  - `[low]` `[reject]` Verif V2: strip/Retry refresh wiring has no asserting check — real committed-coverage gap, but headless matrix asserts dot/label/Retry/autofocus both states plus `refresh_ollama_status` both directions and `main` headless build 5/5 passing; committed-test fix rejected for the same runner-less reason.
  - `[low]` `[reject]` Intent audit divergences (live-window, fault-injection, headless-import, path-resolution, file-freeze, autofocus extra) — descriptive only; live probe `True` with 5 models, mocked faults 16/16, headless build OK, script-dir resolution works, frozen-file hunks predate baseline, initial autofocus satisfies; process constraints honored (bmad-dev handoffs, /tmp-only temps, no commit).

## Verification

**Commands:**
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['text-c3po/runtimes/ollama_client.py', 'text-c3po/ui/top_strip.py', 'text-c3po/app.py', 'text-c3po/runtimes/__init__.py']]"` -- expected: parses clean.
- `python3 -c "import sys; sys.path.insert(0, 'text-c3po'); from runtimes.ollama_client import check_ollama; print(check_ollama())"` -- expected: prints a connected result with the live model names while `ollama serve` runs.
- `grep -rn "runtimes" text-c3po/ui/ || true` -- expected: no matches.
- `grep -rniE "lfm2\.5|translat|whisper|sounddevice" text-c3po/ || true` -- expected: no matches.
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.

## Auto Run Result

Status: done
Intent: folder-plus-id dispatch spec_folder=_bmad-output/specs/spec-e1-shell-core story_id=4; implement plus verify plus review per the story spec (resume: implementation, verify, matrix audit, and three reviews recorded; verification-gap completed this pass with all four layers re-run fresh since no persisted triage existed on disk).
Summary: Ollama stdlib probe plus top-strip connected/not-running status with no-restart Retry, verified complete per spec; 4-layer review triaged with zero patches, zero loopbacks.
Files changed:
- text-c3po/runtimes/ollama_client.py — new stdlib-only probe (`check_ollama()` + `list_models()` + `OLLAMA_BASE_URL`/`OLLAMA_TAGS_URL`/`PROBE_TIMEOUT_S=2.0`, `connected=False` on refused/timeout/malformed, verbatim names from `/api/tags`).
- text-c3po/ui/top_strip.py — extended `build_top_strip()` with status dot + label + always-visible Retry over plain parameters (no `runtimes` import) plus `refresh_ollama_status()` in-place updater.
- text-c3po/app.py — extended `main()` to probe at startup and wire Retry to re-probe plus refresh status controls.
- text-c3po/runtimes/__init__.py — extended re-exports with the probe entry point.
- (context in review diff only, owned by stories 1-3: requirements.txt pin, languages.py, language_pickers.py, text/live/file views, package markers — untouched by this story.)
Review breakdown: 26 findings — 20 false/reject (import resolution, hyphen package, selection defaults, picker sync, 2s-budget blocking, HTTPError catch, strict-malformed, model discard, services bypass, docstring surface, LANGUAGES static, en defaults, requirements freeze, mode/control/data guards, double-tap overlap — each refuted against verified flet 0.86.5 behavior, stdlib semantics, and SPEC constraints) and 6 low/reject (autofocus refresh nuance, layout clip, unbounded-body read, V1/V2 committed-coverage gaps, intent-audit note — headless coverage ran and passed, but committing test files would exceed the spec's enumerated file list in a repo with no test runner). Patches applied: none. Deferred: none. Follow-up review recommended: false (zero patched entries).
Verification: ast.parse clean on all 4 files; live `check_ollama()` returns `(True, [...5 models...])` with `ollama serve` running; `grep -rn runtimes text-c3po/ui/` clean; forbidden-token grep shows only docstring/placeholder hits (`translator`/`translation`/`whisper_client` on `__init__` line 1s, no `lfm2.5` literal in code); `uv run --with flet` prints 0.86.5; independent headless matrix `/tmp/story4_matrix_check.py` 16/16 rows OK (refused/timeout/malformed/missing-key to `(False,[])`, empty to `(True,[])`, verbatim names, loopback URL, 2s budget, stdlib-only, strip connected/not-running dot/label/Retry, refresh both directions, `main` headless build).
Residual risks: native one-window eyeball not run headless (recommend `python text-c3po/app.py` on Mac with `ollama serve` stopped/started plus Retry, same carry-forward as stories 1-3); no committed automated test (repo has no runner; per-story headless re-verification is the standing practice).
Finalization note: the skill's commit step was skipped per the explicit `never commit` dispatch constraint; reviewed files remain uncommitted by design.
