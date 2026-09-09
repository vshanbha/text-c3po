---
title: 'Ship the 23-language constant and pickers'
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
deferred:
  - summary: >-
      Mode-switch visibility branching has no check in this change's verification path.
    evidence: |-
      Real but pre-existing story-2 scope: on_mode_change branching in text-c3po/app.py:30-35 unchanged by this story; story 2 headless round-trip covered it and this run's matrix re-executed headless build OK.
    location: >-
      text-c3po/app.py:30-35
    severity: low
---

<intent-contract>

## Intent

**Problem:** No language list exists yet, so no Text, Live, or File surface can offer the 23 blueprint languages and CAP-5 has nothing to bind pickers to.

**Approach:** Add `text-c3po/languages.py` with the 23 `{code, name}` pairs verbatim from blueprint section 2.1, plus one shared picker builder that binds target (and source-override) `Dropdown`s in all three mode views to that single constant.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; `ui` never imports `runtimes` internals (AD-1/AD-2); one `LANGUAGES` list feeds every picker with zero duplication (AD-10); pickers list exactly the 23 codes/names verbatim with no filtering and no client-side blocking of any model x language combo; view controls are built once so picker selections survive mode switches (story 2 pattern); `flet==0.86.5` exact stays untouched in `requirements.txt`; no secrets files.

**Never:** No translation service, Ollama client, model picker, whisper, or sounddevice code (owned by stories 4-6 and E2/E3); no "auto" or extra entry in the constant or the pickers (auto-detect behavior arrives with the E2/E3 pipeline; source Dropdowns default to English until then); no cross-imports from `live-translate/`; no changes to `streamlit_app.py` or `requirements.txt`; no modal dialogs or extra windows; no restyling of Flet Material defaults.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Import constant headless | Load `languages` module without launching a window | `LANGUAGES` holds exactly 23 `{code, name}` dicts with blueprint codes/names verbatim in blueprint order | ImportError surfaces with missing-dep message |
| Cold launch Text | `python text-c3po/app.py` with deps installed | Text surface shows a target-language `Dropdown` listing all 23 names, defaulting to English | No error expected |
| Live/File pickers | Open Live and File surfaces | Each shows source-override plus target `Dropdown`s, each listing all 23 names, each defaulting to English | No error expected |
| Round-trip with selections | Change target to German and source to French, visit all three modes, return | Both selections intact on the same control objects; process never restarted | No error expected |
| Any combo selectable | Pick any language in any picker | Selection accepted with no client-side block or warning (submit wiring arrives in story 6) | No error expected |
| Headless build | Load app module with a FakePage | Strip plus three views plus all pickers build with 23 options each, no window launched | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `blueprint.md` section 2.1 -- READ-ONLY source of truth: 23 `{code, name}` pairs in fixed order (af→vi); copy verbatim, never reword names or reorder.
- `text-c3po/languages.py` -- DOES NOT EXIST; create the single `LANGUAGES` constant (AD-10) plus a derived `LANGUAGE_CODES` tuple; pure data, zero imports from `ui`/`services`/`runtimes`.
- `text-c3po/ui/language_pickers.py` -- DOES NOT EXIST; shared `build_target_dropdown()` / `build_source_dropdown()` returning `ft.Dropdown`s with options mapped from `LANGUAGES` (key=code, label=name), defaults `en`; import style `from languages import LANGUAGES` matching the script-dir sys.path convention story 2 verified (`python text-c3po/app.py` prepends the script dir).
- `text-c3po/ui/text_view.py` -- story-2 Text surface (`build_text_view()` returning `Column` with `Text` + multiline `TextField` min 6 lines); EXTEND to mount the target picker beside the input.
- `text-c3po/ui/live_view.py` -- story-2 Live placeholder (`build_live_view()`); EXTEND to mount source-override plus target pickers above the placeholder copy (session controls stay E3 scope).
- `text-c3po/ui/file_view.py` -- story-2 File placeholder (`build_file_view()`); EXTEND to mount source-override plus target pickers above the placeholder copy (picker button + progress stay E2 scope).
- `text-c3po/app.py` -- story-2 entry mounting strip plus once-built views with `visible` toggling; NO CHANGE NEEDED (views own their pickers; switch-preservation already handled).
- `text-c3po/ui/__init__.py` -- UI layer marker re-exporting builders; EXTEND re-exports with the two new picker builders (still never imports `runtimes`).
- `requirements.txt` -- exact `flet==0.86.5` pin; READ-ONLY for this story.
- `streamlit_app.py` -- v1 entry; READ-ONLY, must not be modified.
- `_bmad-output/specs/spec-e1-shell-core/stories/2-top-strip-with-three-mode-switching.md` -- prior-story continuity: reuse its FakePage-headless verification pattern and its forbidden-token grep (updated: `language` symbols now allowed, `ollama`/`whisper`/`sounddevice`/`translat`/`model` still forbidden); carry forward its residual risk (native one-window eyeball still needs a Mac run).

## Tasks & Acceptance

**Execution:**
- `text-c3po/languages.py` -- create `LANGUAGES` (23 `{code, name}` dicts verbatim from blueprint section 2.1 in blueprint order) plus derived `LANGUAGE_CODES` -- the AD-10 single source every picker binds to.
- `text-c3po/ui/language_pickers.py` -- create `build_target_dropdown()` and `build_source_dropdown()` mapping `LANGUAGES` to `ft.Dropdown` options (key=code, label=name), each defaulting to `en`, no filtering, no gating -- one builder module prevents picker drift across the three views.
- `text-c3po/ui/text_view.py` -- extend `build_text_view()` to mount the target picker -- the CAP-5 target surface story 6 wires Translate into.
- `text-c3po/ui/live_view.py` -- extend `build_live_view()` to mount source-override plus target pickers -- reserves the live language row without session controls (E3 scope).
- `text-c3po/ui/file_view.py` -- extend `build_file_view()` to mount source-override plus target pickers -- reserves the file language row without picker button or progress (E2 scope).
- `text-c3po/ui/__init__.py` -- extend re-exports with the two picker builders -- keeps the UI layer's single import surface per AD-1.

**Acceptance Criteria:**
- Given a headless environment, when the implementer loads the `languages` module, then `LANGUAGES` contains exactly the 23 blueprint code/name pairs verbatim in blueprint order and `LANGUAGE_CODES` matches their codes.
- Given a cold launch, when the window opens on Text, then the target picker lists all 23 language names with English preselected and every option selectable with no block or warning.
- Given the Live and File surfaces, when each is shown, then its source and target pickers each list all 23 names defaulting to English with any option selectable and no block.
- Given changed picker selections, when the implementer switches through all three modes and back, then every selection is intact and the process never restarted.
- Given the finished tree, when the implementer greps under `text-c3po/`, then no import of `runtimes` appears in `ui/`, and no `ollama`, `whisper`, `sounddevice`, `translat`, or `model` symbols exist outside comments and placeholder copy.
- Given a headless environment, when the implementer loads the app module with a FakePage, then strip plus three views plus all five pickers build with 23 options each and Text visible by default, with no window launched and no exception.

## Spec Change Log

## Review Triage Log

### 2026-09-08 — Review pass
- verdicts: 20 findings — high 0, medium 0, low 5, false 14, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind B1: inconsistent `from ui.*` vs `from languages import` sys.path roots — spec cold-launch `python text-c3po/app.py` prepends the script dir so both resolve (same claim rejected in story 2); headless path-load plus 6/6 matrix audit pass.
  - `[false]` `[reject]` Blind B2: requirements holds only `flet==0.86.5` with no run docs — the rewrite hunk is story-1 work predating this story's baseline; this story's Never mandates no changes to `requirements.txt` and the pin verifies `0.86.5`.
  - `[false]` `[reject]` Blind B3: per-mode Dropdown state does not sync target across modes — spec requires independent pickers built once with selections surviving switches (round-trip intact on same objects verified); cross-mode sync is not required and submit wiring is story-6 scope.
  - `[false]` `[reject]` Blind B4: views lack translate trigger / result areas / automation keys — all owned by stories 4-6 and E2/E3 per this story's Never; adding them would violate scope.
  - `[low]` `[reject]` Blind B5: no `expand`/scroll/wrapping so content may clip at 960x640 — row/column render the single pickers plus hint copy correctly; no named runtime harm shown and the fix adds layout complexity beyond spec for an unlikely everyday encounter.
  - `[false]` `[reject]` Blind B6: both pickers default `en` with no auto-detect/swap and untyped helper — spec explicitly mandates `en` defaults with no `auto` entry until E2/E3 (logged assumption); `-> list` matches existing style with no runtime harm.
  - `[false]` `[reject]` Blind B7: bare `ft.Row([toggle])` with untyped callback and fallback masking state — row renders the toggle correctly (same claim rejected in story 2) and the framework `on_change` contract always delivers a ControlEvent; future strip slots are later stories' scope.
  - `[low]` `[reject]` Blind B8: no runnable smoke path or test in diff — verification did run (4 spec commands plus independent 6/6 headless matrix, recorded below); committing a runner-less test file exceeds the spec's enumerated file list in a repo with no test runner (same reason as story 1/2 V-gaps).
  - `[false]` `[reject]` Edge E1: outside-set selected value blanks all views — SegmentedButton only yields its own segment values with `allow_empty_selection=False` (verified default, same as story 2 E1); no reachable path produces an outside value.
  - `[false]` `[reject]` Edge E2: multi-select keeps only first silently — `allow_multiple_selection=False` is the verified flet 0.86.5 default (same as story 2 E2); multi-select unreachable.
  - `[false]` `[reject]` Edge E3: event without control crashes handler — framework `on_change` contract always delivers a ControlEvent with control (same as story 2 E3); defensive getattr adds branching for an unreachable case.
  - `[false]` `[reject]` Edge E4: `languages.py` entry missing `code` raises KeyError — `LANGUAGES` is a static literal copied verbatim from blueprint 2.1 with no dynamic input path; loudly failing on never-shown corruption is correct behavior, not a defect.
  - `[false]` `[reject]` Edge E5: picker entry missing code/name raises KeyError — same static literal guarded upstream; no reachable malformed-entry path.
  - `[false]` `[reject]` Edge E6: default `en` missing or empty options breaks Dropdown — `en` present at index 6 verified among 23 verbatim entries; empty list unreachable from the static literal.
  - `[false]` `[reject]` Edge E7: duplicate codes create ambiguous options — codes verified unique (23 distinct, blueprint order intact); no reachable duplicate path.
  - `[false]` `[reject]` Edge E8: None/non-callable callback fails on change — `app.py` always passes the locally defined `on_mode_change`; framework contract holds and a ValueError guard adds branching beyond spec for an unreachable case.
  - `[low]` `[reject]` Verif V1: no committed check executing the five built Dropdowns — real gap in committed coverage, but the headless matrix executed the builders (23 verbatim options, `en` default each, no filtering) 6/6 passing; committed-test fix rejected for the runner-less reason above.
  - `[low]` `[reject]` Verif V2: verbatim names/order beyond length unpinned by the length-only assert — real gap in committed coverage, but the independent audit compared the full 23 pairs verbatim in blueprint order plus `LANGUAGE_CODES` equality (ROW import-constant OK); committed-test fix rejected for the same reason.
  - `[low]` `[defer]` Verif V3: mode-switch visibility branching ships without a check in this change's verification — real but pre-existing story-2 scope (`app.py` unchanged by this story); carry the FakePage visibility assertion into the story that next touches `app.py`.
  - `[low]` `[reject]` Intent audit divergences (import surface, requirements/shell hunks in diff, empty test surface) — descriptive only; both sanctioned load paths verified working, shell/requirements hunks predate this story's baseline, and verification ran headless outside the diff (recorded below) with process constraints honored (bmad-dev handoffs, /tmp-only temps, no commit).

## Verification

**Commands:**
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['text-c3po/languages.py', 'text-c3po/ui/language_pickers.py', 'text-c3po/ui/text_view.py', 'text-c3po/ui/live_view.py', 'text-c3po/ui/file_view.py', 'text-c3po/ui/__init__.py']]"` -- expected: parses clean.
- `python3 -c "import sys; sys.path.insert(0, 'text-c3po'); from languages import LANGUAGES, LANGUAGE_CODES; assert len(LANGUAGES) == 23 and len(LANGUAGE_CODES) == 23; print([d['code'] for d in LANGUAGES][:3])"` -- expected: prints the first three blueprint codes.
- `grep -rE "runtimes|ollama|whisper|sounddevice" text-c3po/ui/ text-c3po/languages.py || true` -- expected: no matches.
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.

## Auto Run Result

Status: done
Intent: folder-plus-id dispatch spec_folder=_bmad-output/specs/spec-e1-shell-core story_id=3; implement plus verify plus review per the story spec (resume: implementation and verify done, intent-alignment and blind-hunter done, edge-case and verification-gap completed this pass).
Summary: 23-language constant plus shared pickers wired into all three mode views, verified complete per spec; 4-layer review triaged with zero patches, zero loopbacks.
Files changed:
- text-c3po/languages.py — new `LANGUAGES` (23 `{code, name}` dicts verbatim from blueprint 2.1 in blueprint order) plus derived `LANGUAGE_CODES`.
- text-c3po/ui/language_pickers.py — new `build_target_dropdown()` / `build_source_dropdown()` mapping `LANGUAGES` to `ft.Dropdown` options (key=code, label=name), each defaulting to `en`, no filtering or gating.
- text-c3po/ui/text_view.py — extended `build_text_view()` to mount the target picker beside the multiline input.
- text-c3po/ui/live_view.py — extended `build_live_view()` to mount source-override plus target pickers above the placeholder copy.
- text-c3po/ui/file_view.py — extended `build_file_view()` to mount source-override plus target pickers above the placeholder copy.
- text-c3po/ui/__init__.py — extended re-exports with the two picker builders.
- (context in review diff only, owned by stories 1-2: text-c3po/app.py, ui/top_strip.py, package markers, requirements.txt pin — untouched by this story.)
Review breakdown: 20 findings — 14 false/reject (scope-excluded, unreachable paths, or refuted against verified flet 0.86.5 behavior and SPEC constraints) and 5 low/reject (layout polish, missing smoke/test-in-diff, V1/V2 committed-coverage gaps, intent-audit note — headless coverage ran and passed, but committing test files would exceed the spec's enumerated file list in a repo with no test runner) plus 1 low/defer (V3 mode-switch visibility assertion — prior-story scope carried to the story that next touches `app.py`). Patches applied: none. Deferred: 1 (V3). Follow-up review recommended: false (zero patched entries).
Verification: ast.parse clean on all 6 files; `LANGUAGES`/`LANGUAGE_CODES` length 23 with first codes `af, ar, bn`; forbidden-token grep clean under `text-c3po/ui/` and `languages.py` (`translat`/`model` hits only in `services/__init__.py` docstring copy); `uv run --with flet` prints 0.86.5; independent headless matrix `/tmp/story3_matrix_check.py` 6/6 rows OK (23 verbatim + order + keys, 1+2+2 pickers, 23 verbatim options with `en` default x5, any-combo selectable, round-trip same-object preservation, headless build).
Residual risks: native one-window eyeball not run headless (recommend `python text-c3po/app.py` on Mac, same carry-forward as stories 1-2); no committed automated test (repo has no runner; per-story headless re-verification is the standing practice).
Finalization note: the skill's commit step was skipped per the explicit `never commit` dispatch constraint; reviewed files remain uncommitted by design.
