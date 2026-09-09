---
title: 'Top strip with three-mode switching'
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

**Problem:** The scaffold window from story 1 is empty, so no Text, Live, or File surface is reachable and CAP-1 mode switching cannot be exercised.

**Approach:** Add the always-visible top strip with a Text/Live/File `SegmentedButton` plus the three mode surfaces (Text hosting the input field, Live and File as labeled placeholders), with Text as the launch default and all view state surviving switches.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; `ui` never imports `runtimes` internals (AD-1/AD-2); `flet==0.86.5` exact stays untouched in `requirements.txt`; single window keeps title `text-c3po` and 960x640 minimums from story 1; Text is the launch default; top strip identical across modes per DESIGN/EXPERIENCE; no secrets files.

**Never:** No translation, Ollama client, model picker, language-constant, whisper, or sounddevice code (owned by stories 3-6); no cross-imports from `live-translate/`; no changes to `streamlit_app.py`; no modal dialogs, drawers, or extra windows; no restyling of Flet Material defaults beyond the top-strip brand layer already specified in DESIGN.md.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cold launch | `python text-c3po/app.py` with deps installed | One window; top strip with Text/Live/File toggle, Text selected, Text input visible | No error expected |
| Switch to Live | Tap Live segment | Live placeholder surface shows; top strip unchanged and still visible | No error expected |
| Switch to File | Tap File segment | File placeholder surface shows; top strip unchanged and still visible | No error expected |
| Round-trip with typed input | Type text in Text input, visit Live and File, return to Text | Typed text still present; no process restart, no window flicker beyond view swap | No error expected |
| Headless import | Load app module without launching a window | Module imports cleanly; `main(FakePage)` builds strip plus three views without raising | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `text-c3po/app.py` -- story-1 Flet entry (`main(page)` sets title + 960x640 minimums, `ft.app` guard); EXTEND to mount the top strip plus the three mode views, Text default.
- `text-c3po/ui/__init__.py` -- UI layer marker (AD-1, never imports `runtimes`); re-export point for the strip and views.
- `text-c3po/ui/top_strip.py` -- DOES NOT EXIST; build `SegmentedButton` (`ft.Segment(value, label=...)` per verified flet 0.86.5 signature: segments list, `selected: list[str]`, `on_change`) with values `text`/`live`/`file`, always-visible single-row strip.
- `text-c3po/ui/text_view.py` -- DOES NOT EXIST; Text surface hosting a multiline `TextField` (min 6 lines per EXPERIENCE input-area rule); pickers and Translate button arrive in later stories.
- `text-c3po/ui/live_view.py` -- DOES NOT EXIST; Live placeholder surface (labeled, empty-state copy per EXPERIENCE "Press Start and speak" pattern minus session controls, which arrive in E3 scope).
- `text-c3po/ui/file_view.py` -- DOES NOT EXIST; File placeholder surface (labeled; picker + progress arrive in E2 scope).
- `requirements.txt` -- exact `flet==0.86.5` pin; READ-ONLY for this story.
- `streamlit_app.py` -- v1 entry; READ-ONLY, must not be modified.
- `_bmad-output/specs/spec-e1-shell-core/stories/1-scaffold-flet-app-shell-and-pinned-requirements.md` -- prior-story continuity: reuses the `main(page)` + FakePage-headless pattern and the 6-file scaffold; carry forward its residual risk note (native one-window eyeball still needs a Mac run).

## Tasks & Acceptance

**Execution:**
- `text-c3po/ui/top_strip.py` -- create `build_top_strip(on_mode_change)` returning the always-visible strip row with a `SegmentedButton` of `ft.Segment("text", label="Text")`, `("live", "Live")`, `("file", "File")`, `selected=["text"]`, `allow_empty_selection=False` -- the CAP-1 mode toggle later stories and E2/E3 extend without rework.
- `text-c3po/ui/text_view.py` -- create `build_text_view()` returning the Text surface with a multiline `TextField` (min 6 lines, hint text per EXPERIENCE empty-input microcopy family) -- the input host story 6 wires Translate into.
- `text-c3po/ui/live_view.py` -- create `build_live_view()` returning the labeled Live placeholder surface -- reserves the live surface without session controls (E3 scope).
- `text-c3po/ui/file_view.py` -- create `build_file_view()` returning the labeled File placeholder surface -- reserves the file surface without picker/progress (E2 scope).
- `text-c3po/app.py` -- extend `main(page)` to mount the strip plus all three views (Text visible, Live/File hidden, controls built once and toggled visible so input text survives switches), keeping title and 960x640 minimums -- the CAP-1 shell later stories attach pickers and services to.

**Acceptance Criteria:**
- Given a cold launch, when the window opens, then the top strip with Text/Live/File is visible, Text is selected, and the Text input surface shows.
- Given any mode surface, when the implementer taps each of the other two segments, then the matching surface shows within one tap and the top strip stays visible and identical.
- Given typed text in the Text input, when the implementer switches to Live then File then back to Text, then the typed text is intact and the process never restarted.
- Given the finished tree, when the implementer greps under `text-c3po/`, then no import of `runtimes` appears in `ui/`, and no `ollama`, `whisper`, `sounddevice`, `translat`, `language`, or `model` symbols exist outside comments and placeholder copy.
- Given a headless environment, when the implementer loads the app module with a FakePage, then strip plus three views build with Text selected and visible, with no window launched and no exception.

## Spec Change Log

## Review Triage Log

### 2026-09-08 — Review pass
- verdicts: 18 findings — high 0, medium 0, low 4, false 14, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: `from ui.*` absolute imports only work with CWD inside text-c3po/ — spec cold-launch `python text-c3po/app.py` prepends the script dir to sys.path so the imports resolve from repo root (verified by the passing headless path-load).
  - `[false]` `[reject]` Blind: synthetic diff hunks not `git apply`-able — artifact of review-diff generation for untracked files, not a property of the change; files on disk parse and import clean.
  - `[false]` `[reject]` Blind: requirements drops future translation/Ollama/audio libs — SPEC loopback-only constraint plus this story's Never mandate exactly this; those deps are stories 3-6 scope.
  - `[false]` `[reject]` Blind: bare `ft.Row` with no alignment/expand/reserved slots — row renders the single toggle correctly; no named runtime harm, and future strip extension is later stories' scope.
  - `[false]` `[reject]` Blind: positional `Segment` value, no tooltip/automation id — matches verified flet 0.86.5 `Segment(value, ...)` signature and headless lookup via `.segments` values already works.
  - `[false]` `[reject]` Blind: Text view lacks output surface/actions/language hooks — all owned by stories 3-6 per this story's Never; adding them would violate scope.
  - `[false]` `[reject]` Blind: Live/File copy references controls that don't exist — copy matches the EXPERIENCE empty-session state pattern verbatim; no control is promised.
  - `[false]` `[reject]` Blind: minimums only, no initial size/expand/resize behavior — spec requires 960x640 minimums only (same claim class rejected in story 1); DESIGN states a minimum, not an initial size.
  - `[false]` `[reject]` Edge E1: outside-set selected value blanks all views — SegmentedButton only yields its own segment values with `allow_empty_selection=False` (verified default); no reachable path produces an outside value.
  - `[false]` `[reject]` Edge E2: multi-select desyncs toggle from views — `allow_multiple_selection=False` is the verified flet 0.86.5 default; multi-select unreachable.
  - `[false]` `[reject]` Edge E3: event without control crashes handler — framework `on_change` contract always delivers a ControlEvent with control; defensive getattr would add branching beyond spec for an unreachable case.
  - `[false]` `[reject]` Edge E4: repo-root `sys.path` import fails — both spec-sanctioned load paths (cold-launch command, path-based headless load) verified working; bare `import app` is not an exercised surface.
  - `[false]` `[reject]` Edge E5: requirements rewrite breaks v1 streamlit entry — intended E1 replacement per SPEC with streamlit_app.py READ-ONLY (same claim rejected in story 1); SPEC mandates the removal.
  - `[false]` `[reject]` Edge E6: story touched READ-ONLY requirements.txt — story 2 made no change to the file (reads exactly `flet==0.86.5`); the hunk is story-1 work predating this story's baseline.
  - `[low]` `[reject]` Verif V1: no committed check executing `on_mode_change` visibility branching — real gap in committed coverage, but the branch was executed headless twice this run (implementer + independent re-run, round-trip text preserved); committing a runner-less test file adds files beyond the spec's enumerated list in a repo with no test runner.
  - `[low]` `[reject]` Verif V2: no committed strip/views contract assertion — same evidence as V1 (segment values, selected default, handler wiring all asserted headless and passing); committed-test fix rejected for the same runner-less reason.
  - `[low]` `[reject]` Verif V3: no committed TextField multiline pin — same evidence as V1 (`multiline`, `min_lines>=6` asserted headless and passing); committed-test fix rejected for the same runner-less reason.
  - `[low]` `[reject]` Intent audit divergences (empty test surface in diff, process surface undecidable from diff) — descriptive only; verification did run (headless, recorded below) and process constraints were honored outside the diff (bmad-dev handoffs, /tmp-only temps, no commit).

## Verification

**Commands:**
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['text-c3po/app.py', 'text-c3po/ui/top_strip.py', 'text-c3po/ui/text_view.py', 'text-c3po/ui/live_view.py', 'text-c3po/ui/file_view.py']]"` -- expected: parses clean.
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.
- `grep -rE "runtimes|ollama|whisper|sounddevice" text-c3po/ui/ || true` -- expected: no matches (placeholder copy must avoid these tokens).

## Auto Run Result

Status: done
Intent: folder-plus-id dispatch spec_folder=_bmad-output/specs/spec-e1-shell-core story_id=2; implement plus verify plus review per the story spec.
Summary: top strip with Text/Live/File switching verified complete per spec; 4-layer review triaged with zero patches, zero loopbacks.
Files changed:
- text-c3po/ui/top_strip.py — new `build_top_strip(on_mode_change)` with `SegmentedButton` (text/live/file, Text selected, empty selection forbidden).
- text-c3po/ui/text_view.py — new Text surface with multiline `TextField` (min 6 lines).
- text-c3po/ui/live_view.py — new labeled Live placeholder (session controls stay E3 scope).
- text-c3po/ui/file_view.py — new labeled File placeholder (picker/progress stay E2 scope).
- text-c3po/app.py — `main()` mounts strip plus three once-built views, toggles `visible` on switch, keeps title and 960x640 minimums.
- requirements.txt, streamlit_app.py — untouched by this story (pin hunk in review diff is story-1 work).
Review breakdown: 18 findings — 14 false/reject (scope-excluded or refuted against the verified flet 0.86.5 signatures and SPEC constraints) and 4 low/reject (V1-V3 missing committed regression checks plus the intent-audit note — headless coverage ran and passed twice, but committing test files would exceed the spec's enumerated file list in a repo with no test runner). Patches applied: none. Deferred: none. Follow-up review recommended: false (zero patched entries).
Verification: ast.parse clean on all 5 files; `uv run --with flet` prints 0.86.5; forbidden-token grep clean; independent headless FakePage run asserts title/minimums, segment values, Text-default visibility, multiline>=6, and Live→File→Text round-trip preserving typed input on the same control object → MATRIX-OK.
Residual risks: native one-window eyeball not run headless (recommend `python text-c3po/app.py` on Mac, same carry-forward as story 1); no committed automated test (repo has no runner; per-story headless re-verification is the standing practice).
Finalization note: the skill's commit step was skipped per the explicit `never commit` dispatch constraint; reviewed files remain uncommitted by design.
