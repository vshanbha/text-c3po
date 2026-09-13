---
title: 'Serialize background UI updates through one render point'
type: 'refactor'
created: '2026-09-13'
status: 'done'
baseline_revision: '6fef73d6042bb82385f4b8fb3dc7b63870ab1a20'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/specs/spec-e3-live-ui/SPEC.md
  - _bmad-output/planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-13.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** AD-4 promises that only the main thread touches Flet controls, but
~10 background workers still call `page.update()` directly (and mutate control
attributes first). Stage 1 of E3-9 only routed the live-capture drain
(`_render_session`) through the serialized `_UI_LOCK`/`_ui_update` helper, so a
crash or interleave from the other background paths remains possible.

**Approach:** Complete the D3 re-decision (**B+**, owner-approved 2026-09-13):
route every background `page.update()` through the existing serialized
`_ui_update(page)` helper, leaving main-thread event handlers as the only direct
callers, and record AD-4 as the shipped "single serialized render point"
tolerance. No new lifecycle, no `page.run_thread`, no asyncio pump (that is the
deferred a-lite option, out of scope).

## Boundaries & Constraints

**Always:** `_ui_update(page)` stays the one serialization point; preserve
current behavior, ordering, and UX in text/file/live modes; keep tests fast,
headless, deterministic (no sleeps in the happy path); only main-thread event
handlers may call `page.update()` directly.

**Never:** do not use `page.run_thread` (it runs in an executor thread, not the
main thread — verified in flet 0.86.5 `flet/controls/page.py:903-922`); do not
add a `call_soon_threadsafe`/asyncio pump; do not change services/ or runtimes/
behavior; no new dependencies; do not alter `_render_session`'s existing
correctness.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Background worker completes | `_work` / `_run_file` / `_supervise_live` / `_poll_ollama` / `on_token` updates then calls `_ui_update` | UI refreshes once; no direct `page.update()` on the worker thread | `_ui_update` swallows update errors, never raises |
| Concurrent workers finish together | Two+ background paths call `_ui_update` at once | Updates serialize under `_UI_LOCK`; no interleaved `page.update()` | Second caller waits, then updates |
| Main-thread event handler | device/model/mode change, Start/Stop, Translate | May keep calling `page.update()` directly | unchanged |

</intent-contract>

## Code Map

- `src/text_c3po/app.py` -- `_ui_update` (line 67) is the helper; background sites to route: `_set_translating` (143), `_show_snackbar` (170), `on_token` (515), `_work` (552), `_set_file_status` (616), `_run_file` (657), `_on_live_ended_naturally` (802), `_supervise_live` (846/859/900), `_refuse_live_start` (925), `_poll_ollama` (1144). Main-thread-only sites to LEAVE as direct: `on_mode_change` (321), `_reprobe_and_refresh` (369), `on_translate` (407/432), `on_start_live` (1015), `on_stop_live` (1057), `main` (1087). Comment block at 52-58 states the old "stage 2 run_thread pump" plan.
- `tests/test_units.py` -- add the tripwire + concurrency tests; existing `FakePage` fakes at ~282, ~464, ~583 exercise `_set_translating`/`_render_translation_result`/`_show_snackbar`.
- `_bmad-output/planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md` -- AD-4 rule text (lines 64-68) to update.

## Tasks & Acceptance

**Execution:**
- [ ] `src/text_c3po/app.py` -- replace the background `page.update()` calls listed in Code Map with `_ui_update(page)`; leave the six main-thread-only sites direct -- one serialization point per AD-4.
- [ ] `src/text_c3po/app.py` -- rewrite the 52-58 comment block to state the serialized render-point contract and that the main-thread loop pump is deferred (a-lite, pending manual F5 evidence) -- removes the misleading "stage 2" promise.
- [ ] `tests/test_units.py` -- add a structural tripwire that AST-scans `app.py` and asserts `page.update()` is called directly only from the whitelisted main-thread functions -- prevents regression of the contract.
- [ ] `tests/test_units.py` -- add a concurrency test that calls `_ui_update` from several threads against a FakePage whose `update()` fails if re-entered, asserting serialization and no exception.
- [ ] `_bmad-output/.../ARCHITECTURE-SPINE.md` -- update AD-4 to "single serialized render point; only main-thread event handlers call `page.update()` directly; background threads post dicts" and note `run_thread` is an executor (main-thread pump deferred) -- keeps the spine true to the build.
- [ ] Re-attempt the deferred E3-7 interleaver test only if it deterministically distinguishes the single-lock ordering from the old two-lock code; if it cannot, record the deferral to manual F5 in the E3 memlog instead of writing a vacuous test.

**Acceptance Criteria:**
- Given `app.py`, when scanned, then `page.update()` appears directly only in the six whitelisted main-thread functions; all background sites call `_ui_update`.
- Given `uv run pytest -q`, then all existing tests plus the new tripwire and concurrency tests pass (headless, no Ollama/whisper).
- Given the running app is exercised in text/live/file modes, then behavior is unchanged (functional check via existing tests; live behavior deferred to manual F1/F5).

## Implementation Notes

- Routed all 11 background `page.update()` sites through `_ui_update(page)`
  (`_set_translating`, `_show_snackbar`, `on_token`, `_work` tail,
  `_set_file_status`, `_run_file` finally, `_on_live_ended_naturally`,
  `_supervise_live` ×3, `_refuse_live_start`, `_poll_ollama`); six
  main-thread handlers stay direct. Rewrote the 52-58 comment as the B+
  contract (no run_thread stage-2 promise).
- Interleaver retry (task 6): not attempted — any threaded ordering test
  needs sleeps/gating and cannot deterministically distinguish single-lock
  from two-lock headless; the existing deferral to manual F5 stands (E3
  memlog 2026-09-13). No vacuous test written, per the task's own escape
  clause.

## Spec Change Log

- AD-4 spine updated to the serialized-render-point rule with the
  run_thread rationale; DESIGN/EXPERIENCE source-picker + cards copy
  already fixed under E3-8/D1-A (second review).

## Review Triage Log

- Self-review: no behavior change (same update calls, serialized); lock
  order `_callback_lock → session lock → _UI_LOCK` has no cycle (second
  review verified); `_ui_update` never raises so bare-call replacements
  inside existing try blocks are safe.

## Verification

**Commands:**
- `uv run pytest -q` -- expected: all tests pass (>=143, 6 integration deselected).
- `grep -n "page.update()" src/text_c3po/app.py` -- expected: only `_ui_update` plus the six whitelisted main-thread functions.
- `uv run python -c "import ast,text_c3po.app"` -- expected: imports clean.

**Result (2026-09-13 build):**
- `uv run pytest -q -m "not integration"` → 145 passed, 6 deselected (143 prior + tripwire + concurrency).
- `grep -n "page.update()"` → `_ui_update` body + exactly 7 calls in 6 whitelisted fns (`on_translate` ×2).
- `ast.parse(app.py)` clean; self-review triage above, no behavior change.
