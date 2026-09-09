---
id: SPEC-e3-live-ui
companions:
  - ../../planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/DESIGN.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
sources:
  - ../../planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - ../../../../blueprint.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# E3 — Live Captions UI + Session State

## Why

E1 built the shell and E2 the pipeline, but Shanb still cannot follow a live talk: utterances exist with nowhere to appear and no Start/Stop control. E3 wires the E2 runtimes to the Flet live surface — captions pane, session controls, live status — so UJ-2 works end to end while the session controller keeps ordering and thread-safety guarantees.

## Capabilities

- **CAP-1**
  - **intent:** User can watch utterance captions append in order with timestamps and scroll back through the session.
  - **success:** Each caption shows translated text plus timestamp in utterance-completion order; utterance-flush granularity only, no token streaming.
- **CAP-2**
  - **intent:** User can start and stop capture→ASR→translate via a toggle with live capture, whisper, and model status.
  - **success:** Stop halts capture within 2s; restart begins a new session without relaunch; indicators reflect live subprocess/model state, not cached values.
- **CAP-3**
  - **intent:** System retains the ordered caption list for the active session until a new Start or app close.
  - **success:** Mode switch away and back never clears the list; no cross-restart persistence required (memory-only).
- **CAP-4**
  - **intent:** User can set device, source, and target pickers for a live session from the live surface.
  - **success:** Device list comes from E2 enumeration (BlackHole present-only); any model×language combo submits with quality measured, not gated.

## Constraints

- Session controller single-owns the ordered in-memory caption list and alone drains the utterance queue; UI re-renders from controller state (AD-3).
- Only the main thread touches Flet controls; background threads post to the queue the controller drains (AD-4).
- Live/file utterances use the lightweight `{text, source_lang}` contract; malformed LLM JSON is a retryable error, never raw to the UI (AD-5).
- Live Red (`#D64541`) means capture-running only; errors use Material defaults; every status dot pairs with a text label (DESIGN.md).
- Recoverable failures render inline in the failing row plus `SnackBar` retry; no modal dialogs (AD-12).
- Captions `ListView` auto-follows newest with scroll-back escape and Jump-to-latest; screen reader announces each new row at utterance granularity (EXPERIENCE.md).
- No new ASR or translation logic: E3 composes E1 `services/translation` and E2 runtimes only.

## Non-goals

- VAD tuning, whisper lifecycle changes, file decode changes (E2 owns; E3 only surfaces their status).
- Text-mode output changes (E1 owns).
- setup.sh, eval matrix, packaging, docs refresh (E4).
- Token-streaming captions, diarization, persisted history.

## Success signal

Shanb picks BlackHole (or mic), presses Start, watches timestamped translated captions accumulate, scrolls back and jumps to latest without losing place, presses Stop and keeps the readable ordered list — the live talk use-case demonstrably working in the window.

## Assumptions

- Assumed source picker preselects auto-detect where the pipeline supports it, else English (PRD Q3).

## Open Questions

- Source-language UX in live mode: auto-detect default vs explicit picker default?
