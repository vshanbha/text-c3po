---
date: 2026-09-11
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# E4 Retrospective — Ops, Eval Polish, Test Track, Browser E2E

## Epic summary

- **Epic:** E4 (Ops + Eval Polish), spec folder `_bmad-output/specs/spec-e4-ops-eval-polish/`. Shipped 4/5: 4-1 `setup.sh` clean-machine install, 4-2 full 23-language harness (`--languages matrix|all|subset`), 4-4 regression tests, 4-5 cloud-surface removal + docs refresh. **4-3 macOS packaging stays backlog** (attempted: `flet build macos` demands an interactive Flutter 3.44.8 SDK download plus a signing identity — recorded in TEST-PLAN §H, needs a manual session).
- **Plus, same run:** the test track (TEST-PLAN.md manual matrix, unit 67→133, new `test_integration.py` 6 live PASS, coverage 51→58%) and browser E2E L1–L3 (corrected web-serve command, `test_web_smoke.py`, `/neo-text-c3po-browser-e2e` skill + live pass).
- **Evidence inventory (available):** `setup.sh` ran green end-to-end (exit 0, incl. a 465 MB model fetch); full 23×5 gate **115/115 PASS** on lfm2.5 recorded in `research.md`; final three-pass review (blind/spec/edge) with triage commit; live browser pass with screenshots (shell, 23-language menu, typed entry at 12/5000).
- **Evidence inventory (missing):** packaging bundle (4-3); fresh-machine setup run (only re-run/idempotency proven here).

## Findings

- **F1 — setup.sh caught a real env bug on first live run.** `uv sync` pruned the undeclared pytest and broke the dev loop; fixed by declaring `[dependency-groups] dev = ["pytest>=8"]`. Setup scripts must be executed, not just read — the failure mode was invisible statically. Disposition: accept, rule: every setup change gets a live re-run.
- **F2 — Final review quality stayed high (triage: patch 12+, reject ~8).** Verified-then-patched: broken `sprint-status.yaml` (did not parse — every E4 flag invisible to tooling), wrong BlackHole driver path (live-confirmed), sticky partial downloads (atomic fetch), integration fixture leak (try/finally), poll-thread picker race (lock, `page.update` outside it). Rejected with evidence: AD-4 letter (no pump exists), jump-scroll rework on unverified claims (checked source instead), requirements.txt deletion (kept + drift-guard test). Disposition: accept.
- **F3 — The web-serve docs were wrong and nobody caught it until E2E.** `FLET_SERVER_PORT` alone serves nothing to browsers (verified in flet 0.86.5 `app.py`: only `FLET_FORCE_WEB_SERVER=true` flips to an HTTP site). The AGENTS.md recipe predated any browser run. Rule: every documented command gets executed once before it is written down. Disposition: accept, commands corrected + smoke-tested.
- **F4 — Browser E2E honest boundaries.** Proven: serve, shell render, 23-language menu, snapshot-assertable text entry, `/inference` round-trip shape. Not automatable: ref-based interaction (~3 a11y nodes on CanvasKit), SegmentedButton/Button taps (tried `click_at` + synthetic pointer sequences + shadow-DOM dispatch — no response), FilePicker paints a red web-only error panel. All recorded in TEST-PLAN §I and the skill's learned notes. Disposition: accept; `flet test` remains the future control-level option, not a browser.
- **F5 — Cloud removal verified empty.** Zero openai/anthropic/streamlit/API-key surface in `src/`, deps, or run guides (grep clean); remaining blueprint mentions are historical record, not surface. Disposition: accept.
- **F6 — Non-goals held.** No packaging artifacts stubbed in; no CI added (manual-only policy stands); no test-runner changes beyond the dev group. Disposition: accept.

## Behavior verification

- **First-hand this run:** `./setup.sh` exit 0 twice (fetch + all-skip); subset gate 10/10 then title-fix re-proof; full 23×5 gate 115/115 PASS appended to `research.md`; `yaml.safe_load` parses tracking; BlackHole skip branch fires; web smoke 200 + bootstrap + SIGTERM-clean; browser screenshots of shell/menu/entry; `pytest` 133 + `pytest -m integration` 6 green.
- **Explicitly not exercised:** fresh-machine setup; packaged `.app` (4-3); real-mic live session; VoiceOver.

## Action items

1. (Manual session) 4-3 packaging: approve Flutter SDK, build, Info.plist mic string, ad-hoc run, TCC + Cmd-Q/Dock kill checks — TEST-PLAN §H is the script.
2. (Human) TEST-PLAN top-to-bottom pass, especially §F live-mic items and §P packaging.
3. (Convention, standing) Documented commands get executed once before write-up; reviews verify claims against installed sources before patching.

## Acceptance verdict

**accepted-with-open-items** — 4-1, 4-2 (+115/115 evidence), 4-4, 4-5 done + reviewed + live-proven; 4-3 honestly backlog. No silent gaps: everything unproven is named above with its manual script.

## Test-quality audit (post-acceptance, three fresh lenses)

Assert-strength, flakiness/hermeticity, and coverage-honesty passes over
all of `tests/` (139 tests read) produced 30+ findings; triage below.
Suite now 134 unit + 1 web smoke + 6 integration, all green
(unit headless, integration live in 6 s).

- **Patched (strength):** async-jump test now breaks follow first;
  whisper validation asserts transport-never-attempted (recording
  urlopen); integration shape test injects a stub translate and
  asserts `formal`; asr short-circuit asserts the exact message;
  probe asserts `ok is True`; translate asserts non-echo output;
  file-view handler actually fired; concurrency asserts order-free
  completeness; table asserts parsed structure, not separator count.
- **Patched (flakiness):** both stop/abort tests rebuilt on
  event-gated streams (zero sleeps); registry test discards only its
  own entry; `WHISPER_MODEL` injected everywhere; web smoke logs to
  a file and prints the tail on boot failure; `atexit.register`
  patched in the cleanup test; `/tmp` litter moved to `tmp_path`;
  joins asserted; integration fixture skips on a squatted :9001.
- **Patched (coverage):** retry-raising, tail-with-stop, close
  recording, offline `main()` pass/fail/labels (via new injectable
  `translate_fn` param), SIGINT invocation, timeout-kwarg capture,
  non-dict/non-str shapes, `_port_closed` unit, session `_render`
  deleted as dead code.
- **Rejected with evidence:** `main()`-fake app test (covers
  construction only, adds threading-flake surface); TTS-based
  integration assertions (nondeterministic across model builds —
  the shape/branch structure is the deterministic part).
- **Open measurement anomaly:** successive `--cov` runs reported
  1724 vs 2739 statements on the same tree (unpinned ephemeral
  `pytest-cov`, coverage 7.16.0 this run). Counts in TEST-PLAN are
  test cardinalities (stable), not coverage ratios; pin the tool
  if the ratio ever gates anything.

## Open questions

1. Is `flet test` (control-level, golden screenshots) wanted as the UI-regression layer, or do unit + smoke + neo-skill suffice?
2. Should TEST-PLAN counts ("131 unit + 6 integration") become a generated check instead of prose, given two staleness fixes already?

## Assumptions

- One continuous run (commits `9adf62f`–`23dfaf3` plus review/fix commits); final review was three parallel fresh-context Task subagents over `a7c39f1..HEAD` with the E2/E3 ranges explicitly excluded to avoid re-triage.
- Environment as E2 (plus models/ggml-small.bin fetched by setup.sh into `models/`).
