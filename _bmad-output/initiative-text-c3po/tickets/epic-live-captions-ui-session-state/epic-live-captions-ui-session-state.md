---
type: epic
title: "Live Captions UI + Session State"
parent: initiative-text-c3po
after: [epic-flet-shell-local-text-translation-core, epic-audio-capture-asr]
covers: [R10, R11, R12]
sources:
  - _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e3-live-ui/SPEC.md
  - _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
companions:
  - _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
  - _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
risk: medium
---

# Live Captions UI + Session State

## Description

E1 built the shell and E2 the pipeline, but vshanbha still cannot follow a live talk: utterances exist with nowhere to appear and no Start/Stop control. E3 wires the E2 runtimes to the Flet live surface — captions pane, session controls, live status — so UJ-2 works end to end while the session controller keeps ordering and thread-safety guarantees.

## Outcome

vshanbha picks BlackHole (or mic), presses Start, watches timestamped translated captions accumulate, scrolls back and jumps to latest without losing place, presses Stop and keeps the readable ordered list — the live talk use-case demonstrably working in the window.

## Requirements

1. **R1 (CAP-1):** User can watch utterance captions append in order with timestamps and scroll back through the session. Success: Each caption shows translated text plus timestamp in utterance-completion order; utterance-flush granularity only, no token streaming.
2. **R2 (CAP-2):** User can start and stop capture→ASR→translate via a toggle with live capture, whisper, and model status. Success: Stop halts capture within 2s; restart begins a new session without relaunch; indicators reflect live subprocess/model state, not cached values.
3. **R3 (CAP-3):** System retains the ordered caption list for the active session until a new Start or app close. Success: Mode switch away and back never clears the list; no cross-restart persistence required (memory-only).
4. **R4 (CAP-4):** User can set device, source, and target pickers for a live session from the live surface. Success: Device list comes from E2 enumeration (BlackHole present-only); any model×language combo submits with quality measured, not gated.

## Constraints

- Session controller single-owns the ordered in-memory caption list and alone drains the utterance queue; UI re-renders from controller state (AD-3).
- Only the main thread touches Flet controls; background threads post to the queue the controller drains (AD-4).
- Live/file utterances use the lightweight `{text, source_lang}` contract; malformed LLM JSON is a retryable error, never raw to the UI (AD-5).
- Live Red (`#D64541`) means capture-running only; errors use Material defaults; every status dot pairs with a text label (DESIGN.md).
- Recoverable failures render inline in the failing row plus `SnackBar` retry; no modal dialogs (AD-12).
- Captions `ListView` auto-follows newest with scroll-back escape and Jump-to-latest; screen reader announces each new row at utterance granularity (EXPERIENCE.md).
- No new ASR or translation logic: E3 composes E1 `services/translation` and E2 runtimes only.

## Done when

- vshanbha picks BlackHole (or mic), presses Start, watches timestamped translated captions accumulate, scrolls back and jumps to latest without losing place, presses Stop and keeps the readable ordered list — the live talk use-case demonstrably working in the window.

## Boundaries

- VAD tuning, whisper lifecycle changes, file decode changes (E2 owns; E3 only surfaces their status).
- Text-mode output changes (E1 owns).
- setup.sh, eval matrix, packaging, docs refresh (E4).
- Token-streaming captions, diarization, persisted history.

## References

- parent — _bmad-output/initiative-text-c3po/initiative-text-c3po.md, section Requirements
- spec — _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e3-live-ui/SPEC.md
- prd — _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
- architecture — _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
- design — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
- experience — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/EXPERIENCE.md

- Waits on epic-flet-shell-local-text-translation-core: the E1 services
- Waits on epic-audio-capture-asr: the E2 runtimes
