---
type: epic
title: "Flet Shell + Local Text Translation Core"
parent: initiative-text-c3po
covers: [R1, R2, R3, R4, R5]
sources:
  - _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e1-shell-core/SPEC.md
  - _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
companions:
  - _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
  - _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
risk: medium
---

# Flet Shell + Local Text Translation Core

## Description

vshanbha's v1 translator needs a cloud key and a browser; the live-translate PoC proves local speech→translate works but only as terminal scripts. E1 delivers the shippable local-first foundation — one native Flet window with Text mode fully working on-device — so every later epic (capture, captions, packaging) lands on a proven shell, translation service, and quality gate instead of scaffolding.

## Outcome

vshanbha pastes a paragraph in Text mode, picks a target language and model, gets formal/informal plus origin language, and the 5×5 smoke matrix is recorded — the shell, translation core, and repeatable gate all demonstrably work before E2 begins.

## Requirements

1. **R1 (CAP-1):** User can switch between Text, Live, and File mode surfaces in one Flet window without restart. Success: All three surfaces reachable within 2 taps from launch; switching neither kills the process nor resets the model pick.
2. **R2 (CAP-2):** App can probe Ollama at 127.0.0.1:11434 on startup and show connected / not-running state with retry. Success: With `ollama serve` stopped the top strip shows not-running guidance within 5s; with it running the state flips to connected without restart.
3. **R3 (CAP-3):** User can submit typed text with a target language and receive formal / informal / origin_language. Success: Valid input returns all three fields; malformed model JSON surfaces as a retryable inline error, never raw; empty input is rejected client-side with no LLM call.
4. **R4 (CAP-4):** User can pick any installed Ollama model listed from `/api/tags`, defaulting to ornith-1.5:9b when present else first available. Success: Picker lists exactly what `/api/tags` returns at launch plus a refresh action; default-selection rule holds with and without ornith-1.5:9b installed.
5. **R5 (CAP-5):** App offers the 23 `{code, name}` languages from blueprint §2.1 as the target (and source-override) list. Success: Picker contains all 23 codes/names verbatim; any model×language combo submits with no client-side block.
6. **R6 (CAP-6):** Builder can run a repeatable 5-language × 5-sentence smoke harness across installed models and record JSON-validity scores. Success: Matrix output records per-model ≥95% JSON-valid to gate E1 exit; re-running with a new model appends a comparable row without code changes.

## Constraints

- Layered monolith: `ui/` never imports `runtimes/` internals; all runtime access goes through `services/` (AD-1, AD-2).
- Text mode returns the full `Translation` schema via `JsonOutputParser` with `ChatOllama` JSON format enforced; malformed JSON is a retryable `{error, retryable}` error, never raw to the UI (AD-5).
- Model is an opaque runtime string from `/api/tags`; no model-specific branches in product code (AD-6).
- One `LANGUAGES` list of 23 `{code, name}` in `text-c3po/languages.py` feeds all pickers (AD-10).
- Loopback only: after model download, traffic goes only to `127.0.0.1:11434` (whisper `:9001` arrives in E2); `langchain-openai` banned (AD-11).
- Recoverable failures render inline in the failing card plus `SnackBar` retry; no modal dialogs (AD-12).
- `flet==0.86.5` exact in `requirements.txt`; re-pin check with changelog note at E1 kickoff (NFR-6).
- All product code inside `text-c3po/`; no cross-imports from `live-translate/` (re-implement patterns only).

## Done when

- vshanbha pastes a paragraph in Text mode, picks a target language and model, gets formal/informal plus origin language, and the 5×5 smoke matrix is recorded — the shell, translation core, and repeatable gate all demonstrably work before E2 begins.

## Boundaries

- Audio capture, VAD, whisper-server lifecycle, file pipeline (E2).
- Captions pane, Start/Stop session controls, session state (E3).
- setup.sh, 23-language matrix, packaging, OpenAI removal sweep (E4).
- Token-streaming captions, diarization, translation memory, persisted history.

## References

- parent — _bmad-output/initiative-text-c3po/initiative-text-c3po.md, section Requirements
- spec — _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e1-shell-core/SPEC.md
- prd — _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
- architecture — _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
- design — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
- experience — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/EXPERIENCE.md

