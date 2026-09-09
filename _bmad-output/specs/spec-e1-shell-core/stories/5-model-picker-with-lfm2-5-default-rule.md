---
title: 'Model picker with lfm2.5 default rule'
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

**Problem:** The shell probes Ollama at startup but discards the model names, so the user cannot pick which installed model serves translations and CAP-4 has no picker to build on.

**Approach:** Add a top-strip model `Dropdown` bound verbatim to `/api/tags` output plus a Refresh action, preselecting `lfm2.5` when present else the first available model; mid-session changes apply to the next call only.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; `ui` never imports `runtimes` internals (AD-1/AD-2) — `app.py` passes plain model lists plus callbacks into the strip; loopback only to `http://127.0.0.1:11434` (AD-11); picker lists exactly what `/api/tags` returns at probe time with names verbatim and no filtering; default rule is prefix-match on `lfm2.5` (covers `lfm2.5:latest` and bare `lfm2.5`) else first available; model is an opaque runtime string with no other model-specific branches (AD-6); status dot always paired with a text label; recoverable failures render inline, no modal dialogs (AD-12); `flet==0.86.5` exact stays untouched in `requirements.txt`; no secrets files.

**Never:** No translation service, `ChatOllama`, `JsonOutputParser`, or output-card code (owned by story 6); no hard-coded model names anywhere except the single `lfm2.5` default-rule constant; no whisper, sounddevice, VAD, or file-pipeline code (E2/E3 scope); no new third-party dependencies (stdlib `urllib` + installed `flet` only); no cross-imports from `live-translate/`; no changes to `streamlit_app.py`, `requirements.txt`, or `languages.py`; no restyling of Flet Material defaults.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cold launch, lfm2.5 present | `python text-c3po/app.py` with `/api/tags` containing `lfm2.5:latest` + others | Model Dropdown lists exactly the returned names verbatim; `lfm2.5:latest` preselected | No error expected |
| Cold launch, lfm2.5 absent | `/api/tags` returns names with no `lfm2.5` prefix | Dropdown lists all names verbatim; first available preselected | No error expected |
| Cold launch, Ollama down | `ollama serve` stopped | Not-running status + guidance intact; model Dropdown empty with no selection, Refresh still available | Refused/timeout surfaces as empty list, never a traceback or dialog |
| Cold launch, zero models | 200 with empty `models` list | Still connected; model Dropdown empty with no selection | No error expected |
| Refresh adds a model | Tap Refresh after pulling a new model | Dropdown options re-list exactly the fresh `/api/tags` names; existing selection kept when still present, else default rule re-applies | Probe failure keeps prior options + selection intact |
| Malformed /api/tags body | 200 with non-JSON or missing `models` key | Treated as not-running with empty options; prior selection preserved on Refresh-failure path | Parse failure surfaces as empty options, never raw to the UI |
| Mid-session change | Pick a different model after launch | Picker value updates; no retroactive effect — story 6 reads the current value only at next-call time | No error expected |
| Headless build | Load app module with a FakePage | Strip builds with mode toggle + status + model Dropdown + Refresh wired, no window launched | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `text-c3po/runtimes/ollama_client.py` -- live stdlib probe (`check_ollama()` -> `(connected, models)`, `list_models()` verbatim names, `OLLAMA_BASE_URL`/`OLLAMA_TAGS_URL` loopback, `PROBE_TIMEOUT_S=2.0`); EXTEND with the single default-rule constant (`DEFAULT_MODEL_PREFIX = "lfm2.5"`) plus a pure `pick_default_model(models)` helper (prefix-match first `lfm2.5*` hit else `models[0]` else `None`); still never raises, still stdlib-only.
- `text-c3po/ui/model_picker.py` -- DOES NOT EXIST; pure-UI builder taking plain `list[str]` only (never imports `runtimes`): `build_model_dropdown(models, selected)` returning `ft.Dropdown(label="Model", options=[DropdownOption(key=name, text=name)...], value=selected)` plus `refresh_model_options(dropdown, models, selected)` updating options/value in place; no `lfm2.5` literal here (default arrives as the `selected` argument).
- `text-c3po/ui/top_strip.py` -- story-4 strip (`build_top_strip(on_mode_change, ollama_connected, on_retry)` returning single `Row` with toggle + dot + label + Retry, `strip.data` holding refs, `refresh_ollama_status()` in-place updater); EXTEND signature with `models`, `selected_model`, `on_model_change`, `on_refresh_models` plain params and mount the `Dropdown` + Refresh control (`TextButton`/`IconButton`) in the same row; expose `refresh_model_picker(strip, models, selected)` or reuse `strip.data` refs so `app.py` refreshes picker without rebuild.
- `text-c3po/app.py` -- story-4 entry probing once at startup via `runtimes.ollama_client` and wiring Retry to re-probe + `refresh_ollama_status`; EXTEND `main()` to keep the probe's model list, compute `pick_default_model()`, pass list + selection + `on_model_change` (stores current pick for story 6, no retroactive call) + `on_refresh_models` (re-probe, refresh status AND picker in place) into `build_top_strip`; mode-switch `visible` toggling and input preservation untouched.
- `text-c3po/ui/__init__.py` -- UI re-export surface (`build_top_strip`, `refresh_ollama_status`, view + language-picker builders; never imports `runtimes`); EXTEND re-exports with the model-picker builders only.
- `text-c3po/runtimes/__init__.py` -- runtimes re-export surface; EXTEND with `DEFAULT_MODEL_PREFIX` + `pick_default_model` (still never imported by `ui/`).
- `text-c3po/ui/language_pickers.py` -- story-3 `Dropdown` builder pattern (`ft.DropdownOption(key, text)`, `value` default); REUSE as the visual/structural pattern for the model dropdown (model names use key=name, text=name verbatim).
- `requirements.txt` -- exact `flet==0.86.5` pin; READ-ONLY for this story (no new deps).
- `streamlit_app.py`, `text-c3po/languages.py` -- READ-ONLY, must not be modified.
- `_bmad-output/specs/spec-e1-shell-core/stories/4-ollama-client-with-launch-connectivity-check.md` -- prior-story continuity: reuse its FakePage-headless verification pattern and its `check_ollama` never-raises contract; carry forward its residual risk (native one-window eyeball still needs a Mac run).
- `_bmad-output/specs/spec-e1-shell-core/stories/3-ship-the-23-language-constant-and-pickers.md` -- prior-story continuity: forbidden-token grep now allows `model` for the picker plus the single `lfm2.5` default constant in `runtimes/ollama_client.py` only; `translat`, `whisper`, `sounddevice` stay forbidden.

## Tasks & Acceptance

**Execution:**
- `text-c3po/runtimes/ollama_client.py` -- add `DEFAULT_MODEL_PREFIX` + pure `pick_default_model(models)` (prefix-match `lfm2.5*` else first else `None`) -- the CAP-4/AD-6 default rule story 6 and the harness reuse.
- `text-c3po/ui/model_picker.py` -- create `build_model_dropdown()` + `refresh_model_options()` over plain `list[str]` (verbatim key=text=name, no filtering, no `runtimes` import) -- the picker surface with no model policy inside.
- `text-c3po/ui/top_strip.py` -- extend `build_top_strip()` to mount the model `Dropdown` + Refresh in the same always-visible row over plain params plus an in-place picker refresher -- the CAP-4 strip surface story 6 reads the current value from.
- `text-c3po/app.py` -- extend `main()` to pass the startup model list + default selection into the strip and wire Refresh/Retry to re-probe and refresh status + picker in place (selection preserved when still present) -- the no-restart CAP-2/CAP-4 recovery path.
- `text-c3po/ui/__init__.py`, `text-c3po/runtimes/__init__.py` -- extend re-exports with the new picker/default-rule entry points -- keeps each layer's single import surface per AD-1.

**Acceptance Criteria:**
- Given `/api/tags` containing an `lfm2.5`-prefixed name, when the app cold-launches, then the model picker lists exactly the returned names verbatim with the `lfm2.5` entry preselected.
- Given `/api/tags` with no `lfm2.5`-prefixed name, when the app cold-launches, then the picker lists all names verbatim with the first available preselected; given zero models or Ollama down, then the picker is empty with no selection while status guidance stays intact.
- Given a new model pulled after launch, when the implementer taps Refresh, then the picker re-lists exactly the fresh names, keeping the prior selection when still present else re-applying the default rule; when the re-probe fails, then prior options and selection stay intact with no traceback or dialog.
- Given a model picked mid-session, when story 6 later issues a call, then it uses the picker's current value with no retroactive effect on prior results.
- Given the finished tree, when the implementer greps under `text-c3po/`, then no import of `runtimes` appears in `ui/`, the `lfm2.5` literal appears only in `runtimes/ollama_client.py`, and no `translat`, `whisper`, or `sounddevice` symbols exist outside comments and placeholder copy.
- Given a headless environment, when the implementer loads the app module with a FakePage, then the strip plus status controls plus model Dropdown plus Refresh build with the default rule applied and no window launched.

## Spec Change Log

## Review Triage Log

### 2026-09-08 — Review pass
- verdicts: 23 findings — high 0, medium 0, low 6, false 17, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind B1: script-dir-relative `from runtimes`/`from ui`/`from languages` imports unresolvable from repo root — `python text-c3po/app.py` prepends the script dir so all resolve; headless path-load plus 26/26 matrix audit pass (same claim rejected in stories 2-4).
  - `[false]` `[reject]` Blind B2: requirements drops streamlit/langchain leaving dead `streamlit_app.py` with no langchain-ollama path — the rewrite hunk is story-1 work predating this baseline; this story's Never freezes the file and SPEC mandates the v1 replacement (same as stories 2-4).
  - `[false]` `[reject]` Blind B3: no run/smoke command or doc update, AGENTS.md TODO(E1) unaddressed — the spec's task list enumerates product files only with no run-command deliverable; AGENTS.md TODO(E1) is future work for later stories (same claim rejected in stories 1-4).
  - `[low]` `[reject]` Blind B4: single Row with no spacing/alignment/expand/wrap overflows 960px and squeezes the Dropdown — row renders correctly with all six controls headless-verified; no named runtime harm shown and the fix adds layout complexity beyond spec (same class rejected in stories 2-4).
  - `[false]` `[reject]` Blind B5: picker accepts `selected` absent from `models`, blindly assigns value incl `None` leaving blank picker — `app.py` always computes selected as prior-if-present else `pick_default_model`, so membership is guaranteed on the app path; empty-options plus `None` selection is the specified Ollama-down state, not a defect.
  - `[false]` `[reject]` Blind B6: source+target both default `en` with no auto-detect, `LANGUAGE_CODES` unused, no uniqueness guard — spec explicitly mandates `en` defaults with no `auto` entry until E2/E3; static 23-entry literal copied verbatim needs no runtime guard (same as story 3 E4-E7).
  - `[false]` `[reject]` Blind B7: hardcoded loopback URL/timeout with no env override, no HTTP-status check, single malformed entry discards all names — loopback URL plus 2.0s timeout are SPEC AD-11/CAP-2 requirements; `urllib` raises `HTTPError` on non-200 caught to not-running (verified story 4); strict-malformed is the specified behavior (same as story 4 B6-B7).
  - `[false]` `[reject]` Blind B8: `pick_default_model` list-only, case-sensitive prefix, first-hit in undefined tag order — spec input is the verbatim `/api/tags` list; prefix case-sensitivity matches case-sensitive model names; first-hit is deterministic in returned order; non-list safely returns `None` without raising (matrix-verified).
  - `[false]` `[reject]` Blind B9: `on_model_change` swallows exceptions storing `None`, Retry/Refresh spam with no debounce, `strip.data` magic-string duplication — framework `on_change` always delivers a ControlEvent so `None` occurs only in isolation; single-threaded Flet runs probes sequentially within the 2s budget (same as story 4 E7); `strip.data` refs follow the established story-4 pattern with guarded lookups.
  - `[false]` `[reject]` Blind B10: views lack accessible labels/disabled affordances/Start/file stubs, dot has no tooltip — session controls are E3 scope and picker button E2 scope per this story's Never; label/expand/tooltip polish is beyond spec (same class rejected in stories 2-3).
  - `[false]` `[reject]` Edge E1: mode value missing from views dict blanks the window — SegmentedButton only yields its own segment values with `allow_empty_selection=False` (verified default); no reachable outside value (same as stories 2-4).
  - `[false]` `[reject]` Edge E2: `on_model_change` with `e None` clears the stored model — framework contract always delivers a ControlEvent with control; `None` occurs only in isolation tests, never on the app path.
  - `[false]` `[reject]` Edge E3: `selected_model` absent from models shows invalid selection — app wiring guarantees membership (see B5); empty plus `None` is the specified down-state.
  - `[false]` `[reject]` Edge E4: non-string/empty/duplicate names break the Dropdown — `_verbatim_names` guarantees non-empty-string names on the app path (malformed yields `[]`); non-string input is unreachable from `/api/tags` wiring.
  - `[false]` `[reject]` Edge E5: first entry empty/non-string yields default `None` despite later valid entries — same upstream guarantee as E4; the helper never raises and returns `None` safely for out-of-contract input.
  - `[false]` `[reject]` Edge E6: one malformed entry drops all valid names into false disconnected — strict-malformed mapping to not-running is the specified matrix behavior (same as story 4 B7).
  - `[false]` `[reject]` Edge E7: `strip.data` missing `model_dropdown` ref diverges UI from stored model silently — strip is always built by `build_top_strip` which sets all refs; refreshers guard on `None`; no reachable missing-refs path on the app wiring (same as story 4 E4).
  - `[low]` `[reject]` Verif V1: default-rule prefix match has no normally-run regression check — real committed-coverage gap, but the headless matrix asserts prefix-win/first-else/empty-None/non-list-None and 26/26 pass; committed-test fix rejected for the runner-less reason (no test files exist; spec file list enumerates product files only; same as stories 1-4 V-gaps).
  - `[low]` `[reject]` Verif V2: probe never-raises plus connected-semantics unpinned — real committed-coverage gap, but headless matrix asserts refused/timeout/malformed/missing-key yield `(False,[])`, empty yields `(True,[])`, verbatim names pass; committed-test fix rejected for the same runner-less reason.
  - `[low]` `[reject]` Verif V3: Dropdown verbatim list plus in-place refresh unchecked — real committed-coverage gap, but headless matrix asserts verbatim key=text=name options/value before and after refresh plus the empty case; committed-test fix rejected for the same runner-less reason.
  - `[low]` `[reject]` Verif V4: Refresh failure-preservation plus status-flip path unchecked — real committed-coverage gap, but headless matrix asserts keep-prior, default-reapply, failure-preserves, and dot/label flip both directions; committed-test fix rejected for the same runner-less reason.
  - `[low]` `[reject]` Verif V5: 23-language constant plus picker defaults have no consumer check — real committed-coverage gap in story-3-owned files untouched by this story (story 3 matrix covered 23 verbatim plus `en` defaults); committed-test fix rejected for the same runner-less reason.
  - `[false]` `[reject]` Intent audit divergences (spec surface external to diff, process surface undecidable from diff, no test surface in diff) — descriptive only; story-5 spec acceptance holds (matrix 26/26), and process constraints were honored outside the diff (bmad-dev handoffs, /tmp-only temps, no commit).

## Verification

**Commands:**
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['text-c3po/runtimes/ollama_client.py', 'text-c3po/ui/model_picker.py', 'text-c3po/ui/top_strip.py', 'text-c3po/app.py', 'text-c3po/ui/__init__.py', 'text-c3po/runtimes/__init__.py']]"` -- expected: parses clean.
- `python3 -c "import sys; sys.path.insert(0, 'text-c3po'); from runtimes.ollama_client import pick_default_model; assert pick_default_model(['a:1','lfm2.5:latest','b:2'])=='lfm2.5:latest'; assert pick_default_model(['b:2','a:1'])=='b:2'; assert pick_default_model([]) is None; print('default-rule OK')"` -- expected: prints `default-rule OK`.
- `python3 -c "import sys; sys.path.insert(0, 'text-c3po'); from runtimes.ollama_client import check_ollama; print(check_ollama())"` -- expected: prints a connected result with the live model names while `ollama serve` runs.
- `grep -rn "runtimes" text-c3po/ui/ || true` -- expected: no matches.
- `grep -rniE "translat|whisper|sounddevice" text-c3po/ || true` -- expected: no matches outside comments and placeholder copy.
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.

## Auto Run Result

Status: done
Intent: folder-plus-id dispatch spec_folder=_bmad-output/specs/spec-e1-shell-core story_id=5; implement plus verify plus review per the story spec.
Summary: Top-strip model Dropdown bound verbatim to /api/tags plus Refresh with the lfm2.5 prefix-match default rule, verified complete per spec; 4-layer review triaged with zero patches, zero loopbacks.
Files changed:
- text-c3po/runtimes/ollama_client.py — added `DEFAULT_MODEL_PREFIX = "lfm2.5"` plus pure never-raises `pick_default_model()` (first `lfm2.5*` hit else first else `None`); probe, loopback URL, 2s timeout, stdlib-only untouched.
- text-c3po/ui/model_picker.py — new `build_model_dropdown()` / `refresh_model_options()` over plain `list[str]` (verbatim key=text=name, no filtering, no `runtimes` import, no policy literal).
- text-c3po/ui/top_strip.py — extended `build_top_strip()` with model Dropdown + Refresh in the same always-visible row over plain params plus `refresh_model_picker()` in-place updater; status dot/label/Retry untouched.
- text-c3po/app.py — extended `main()` to pass startup list + default selection into the strip and wire Refresh/Retry to re-probe and refresh status + picker in place (prior selection kept when still present, else default rule; failure preserves prior).
- text-c3po/ui/__init__.py, text-c3po/runtimes/__init__.py — extended re-exports with the new picker/default-rule entry points.
- (context in review diff only, owned by stories 1-4: requirements.txt pin, languages.py, language_pickers.py, text/live/file views, package markers — untouched by this story.)
Review breakdown: 23 findings — 17 false/reject (import resolution, hyphen package, requirements freeze, run-command scope, en defaults, loopback/timeout/strict-malformed, prefix semantics, ControlEvent contract, verbatim-name guarantees, missing-refs guards — each refuted against verified flet 0.86.5 behavior, stdlib semantics, and SPEC constraints) and 6 low/reject (single-Row layout polish, V1-V4 committed-coverage gaps, V5 story-3 coverage note, intent-audit note — headless coverage ran 26/26 and passed, but committing test files would exceed the spec's enumerated file list in a repo with no test runner). Patches applied: none. Deferred: none. Follow-up review recommended: false (zero patched entries).
Verification: ast.parse clean on all 6 files; default-rule asserts print `default-rule OK`; live `check_ollama()` returns `(True, [...5 models...])` with `ollama serve` running; `grep -rn runtimes text-c3po/ui/` clean; forbidden-token grep shows only docstring/placeholder hits plus the single sanctioned `lfm2.5` constant in `runtimes/ollama_client.py`; `uv run --with flet` prints 0.86.5; independent headless matrix `/tmp/story5_matrix_check.py` 26/26 rows OK (verbatim preselect, first-else, bare-prefix, down-empty with Refresh visible, zero-models connected, keep-prior/drop-redefault, malformed matrix to `(False,[])`, failure-preserves, mid-session store, headless build with default applied).
Residual risks: native one-window eyeball not run headless (recommend `python text-c3po/app.py` on Mac with `ollama serve` stopped/started, Refresh after a pull, mid-session change — same carry-forward as stories 1-4); no committed automated test (repo has no runner; per-story headless re-verification is the standing practice).
Finalization note: the skill's commit step was skipped per the explicit `never commit` dispatch constraint; reviewed files remain uncommitted by design.
