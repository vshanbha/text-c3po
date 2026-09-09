---
id: SPEC-e1-shell-core
companions:
  - ../../planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/DESIGN.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
sources:
  - ../../planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - ../../../../blueprint.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# E1 — Flet Shell + Local Text Translation Core

## Why

Shanb's v1 translator needs a cloud key and a browser; the live-translate PoC proves local speech→translate works but only as terminal scripts. E1 delivers the shippable local-first foundation — one native Flet window with Text mode fully working on-device — so every later epic (capture, captions, packaging) lands on a proven shell, translation service, and quality gate instead of scaffolding.

## Capabilities

- **CAP-1**
  - **intent:** User can switch between Text, Live, and File mode surfaces in one Flet window without restart.
  - **success:** All three surfaces reachable within 2 taps from launch; switching neither kills the process nor resets the model pick.
- **CAP-2**
  - **intent:** App can probe Ollama at 127.0.0.1:11434 on startup and show connected / not-running state with retry.
  - **success:** With `ollama serve` stopped the top strip shows not-running guidance within 5s; with it running the state flips to connected without restart.
- **CAP-3**
  - **intent:** User can submit typed text with a target language and receive formal / informal / commentary / origin_language.
  - **success:** Valid input returns all four fields; malformed model JSON surfaces as a retryable inline error, never raw; empty input is rejected client-side with no LLM call.
- **CAP-4**
  - **intent:** User can pick any installed Ollama model listed from `/api/tags`, defaulting to lfm2.5 when present else first available.
  - **success:** Picker lists exactly what `/api/tags` returns at launch plus a refresh action; default-selection rule holds with and without lfm2.5 installed.
- **CAP-5**
  - **intent:** App offers the 23 `{code, name}` languages from blueprint §2.1 as the target (and source-override) list.
  - **success:** Picker contains all 23 codes/names verbatim; any model×language combo submits with no client-side block.
- **CAP-6**
  - **intent:** Builder can run a repeatable 5-language × 5-sentence smoke harness across installed models and record JSON-validity scores.
  - **success:** Matrix output records per-model ≥95% JSON-valid to gate E1 exit; re-running with a new model appends a comparable row without code changes.

## Constraints

- Layered monolith: `ui/` never imports `runtimes/` internals; all runtime access goes through `services/` (AD-1, AD-2).
- Text mode returns the full `Translation` schema via `JsonOutputParser` with `ChatOllama` JSON format enforced; malformed JSON is a retryable `{error, retryable}` error, never raw to the UI (AD-5).
- Model is an opaque runtime string from `/api/tags`; no model-specific branches in product code (AD-6).
- One `LANGUAGES` list of 23 `{code, name}` in `text-c3po/languages.py` feeds all pickers (AD-10).
- Loopback only: after model download, traffic goes only to `127.0.0.1:11434` (whisper `:9001` arrives in E2); `langchain-openai` banned (AD-11).
- Recoverable failures render inline in the failing card plus `SnackBar` retry; no modal dialogs (AD-12).
- `flet==0.86.5` exact in `requirements.txt`; re-pin check with changelog note at E1 kickoff (NFR-6).
- All product code inside `text-c3po/`; no cross-imports from `live-translate/` (re-implement patterns only).

## Non-goals

- Audio capture, VAD, whisper-server lifecycle, file pipeline (E2).
- Captions pane, Start/Stop session controls, session state (E3).
- setup.sh, 23-language matrix, packaging, OpenAI removal sweep (E4).
- Token-streaming captions, diarization, translation memory, persisted history.

## Success signal

Shanb pastes a paragraph in Text mode, picks a target language and model, gets formal/informal/commentary plus origin language, and the 5×5 smoke matrix is recorded — the shell, translation core, and repeatable gate all demonstrably work before E2 begins.

## Assumptions

- Assumed `flet==0.86.5` pin holds; E1 kickoff re-confirms against the changelog (PRD Q1).
- Assumed live source-language default (auto-detect where supported, else English) carries into E3 picker presets (PRD Q3).

## Open Questions

- Confirm `flet==0.86.5` stays the pin at E1 kickoff, or re-pin to newer stable with changelog note?
