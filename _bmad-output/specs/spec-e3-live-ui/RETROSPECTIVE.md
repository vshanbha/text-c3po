---
date: 2026-09-11
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# E3 Retrospective — Live Captions UI + Session State

## Epic summary

- **Epic:** E3 (Live Captions UI + Session State), spec folder `_bmad-output/specs/spec-e3-live-ui/` (`SPEC.md`, stories 3-1–3-4 per `sprint-status.yaml`).
- **Stories completed:** 4/4 in one continuous run: 3-1 session controller (`3a4930d`), 3-2 captions pane (`4eee88f`), 3-3 Start/Stop + indicators (`4d3753f`), 3-4 retry/guards/polish (`0f819a2`), plus review pass (`cab7ae0`).
- **Evidence inventory (available):** SPEC.md CAP-1–CAP-4; three fresh-context review passes (20 findings, 12 patched — the highest hit rate of any epic); 116 unit tests green (incl. a 4-thread × 25-post concurrent drain and an awaited async-jump drive); live proofs — launch auto-spawns whisper, SIGTERM reaps it with zero orphans, app imports + constructs clean.
- **Evidence inventory (missing):** real-mic Start (no desktop automation available — TEST-PLAN §F is the human script); VoiceOver cadence; jump-scroll effectiveness under a live session (browser E2E could not drive SegmentedButton/Button taps — recorded in TEST-PLAN §I).

## Findings

- **F1 — Concurrency review was the whole game (4 patched).** Blind + edge passes independently found the same `_seq` race (drain on capture thread vs retry thread → duplicate seqs → silently dropped rows); fixed with a lock scoped to seq-assign/append, translate calls kept outside it. Same pass fixed: retry flipping rows invisibly (in-place row rebuild by stable key), double-Start TOCTOU (starting flag + generation token), and the dropped chunker tail on stop (flush-on-exit). All re-tested deterministically, including concurrent drains asserting seqs 1..50. Disposition: accept.
- **F2 — Scroll-follow fixed by evidence, not assertion.** The review claimed programmatic scrolls self-disable follow; instead of restructuring on an unverified claim, the installed `OnScrollEvent` was inspected, `ScrollType.USER` filtering implemented, and the suppress-flag machinery deleted. Lesson: check the framework source before trusting a reviewer's mental model — including this author's. Disposition: accept.
- **F3 — CAP-2 closed with the third dot.** Review noted the missing model indicator (DESIGN.md asks three dots); `model_label` was added to the Live status row and set at Start. Whisper-dot staleness between events is accepted (event-driven refresh, no poller — the 2-1 no-second-poller decision stands). Disposition: accept.
- **F4 — AD-4 letter vs spirit, settled.** No Flet main-thread pump exists (`page.run_thread` targets an executor, verified in source); the shipped contract is the single render point (`_render_session`) with pipeline threads posting dicts only — the same tolerance E1 ships. Recorded explicitly in code so the next retro stops re-flagging it. Disposition: accept as documented deviation.
- **F5 — Non-goals held.** No VAD/whisper/decode changes beyond surfacing status; no text-mode changes; no token streaming; memory-only sessions. Disposition: accept.

## Behavior verification

- **First-hand this run:** concurrent-drain uniqueness (4 threads × 50 posts → seqs 1..50); retry flip renders in place; USER-vs-UPDATE scroll filtering; tail flush on stream end; abort-first stop; stop-latch (zero reads after pre-set stop); launch→spawn→SIGTERM→reaped with zero orphans, twice.
- **Inherited:** stub-translate ordering/timestamps/gaps; headless pane construction.
- **Explicitly not exercised:** real-mic capture loop; VoiceOver announcements; double-Start race under a human finger (unit-latched, TEST-PLAN F12).

## Action items

None new. Carries: (1) VoiceOver cadence + 1000-row live-region behavior → human TEST-PLAN F5/F6; (2) jump-scroll effectiveness under live load → F5; (3) mid-session auto-restart stays a non-goal (gaps + next-Start, per E2-F2).

## Acceptance verdict

**accepted-with-open-items** — criteria **declared** (SPEC CAP-1–CAP-4 + Success signal). 4/4 stories done + reviewed + live-verified where automation reaches; the named open items are human-only checks (F5/F6/F12) plus the documented AD-4 deviation.

## Open questions

1. Should the AD-4 deviation ever be revisited (e.g. a main-thread pump if Flet adds one), or is the single-render-point contract permanent?
2. Is a monitor loop for mid-session whisper restart wanted, or do gaps stand?

## Assumptions

- Same run/verify/review shape as E2 (commits `3a4930d`–`cab7ae0`); review via three parallel fresh-context Task subagents, triaged with verify-first discipline (two claims checked against installed flet/sounddevice sources before patching).
- No `sprint-status.yaml` story writes beyond keys (tracking) — story artifacts were never this repo's unit (commits are).
