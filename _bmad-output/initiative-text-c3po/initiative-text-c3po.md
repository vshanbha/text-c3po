---
type: initiative
title: text-c3po v2 — Local-first Live Translator
parent: none
status: done
risk: medium
---

# text-c3po v2 — Local-first Live Translator

## Description

One native Flet desktop app with three modes — Text, Live, File — running entirely
locally: type, speak, or drop a file and get a structured translation with no keys,
no SaaS and no browser. After the first-run model download the machine goes quiet:
zero outbound traffic, loopback only to Ollama and whisper-server. The backend stays
model-agnostic across 23 aspirational languages, and an eval harness tells the user
which model by language combos are actually good. Built from the v2 PRD, the E1 to E5
SPEC set and the live-translate proof of concept.

## Outcome

vshanbha uses the local app weekly for real text, live and file translation and never
re-adds a cloud key. Source measure of success: SM-1 (5x5 smoke matrix at or above
95 percent JSON-valid per model) and SM-2 (median utterance end-to-end under 3s on M4).

## Requirements

1. R1 (FR-1): User can switch between Text, Live, and File modes via buttons/toggles without restart.
2. R2 (FR-2): App can probe Ollama at 127.0.0.1:11434 on startup and show connected / not-running state.
3. R3 (FR-3): User can submit typed text with a Target language and receive formal / informal / commentary / origin_language.
4. R4 (FR-4): User can pick any installed Ollama Model listed from `/api/tags`; default preselects ornith-1.5:9b when present, else first available.
5. R5 (FR-5): App can offer the 23 `{code, name}` languages from blueprint §2.1 as the Target language (and Source language override) list.
6. R6 (FR-6): User can choose between Built-in Microphone and BlackHole when present; when BlackHole is absent only available sounddevice devices list.
7. R7 (FR-7): System can segment the int16 PCM stream into Utterances via ported RMS-silence + flush-on-2-silent-frames-or-max-utterance logic.
8. R8 (FR-8): App can spawn `whisper-server` (transcribe only) on 127.0.0.1:9001 at launch, health-check it, restart on crash, and clean up on exit.
9. R9 (FR-9): User can pick an audio/video file and run it through the same ASR→translate pipeline as live.
10. R10 (FR-10): User can watch Utterance Captions append in order with timestamps and scroll back through the Session.
11. R11 (FR-11): User can start/stop capture→ASR→translate via toggle; UI shows capture-active, whisper latency, and active Model.
12. R12 (FR-12): System can retain the ordered Caption list for the active Session until the user starts a new one or closes the app.
13. R13 (FR-13): New user can run `setup.sh` covering Ollama install, Model pull, PortAudio/sounddevice, and BlackHole guidance.
14. R14 (FR-14): Builder can run a repeatable eval harness (sample sentences × languages × installed Models) recording JSON-validity and per-language scores.
15. R15 (FR-15): User can install the Flet-built (or PyInstaller `--windowed`) macOS bundle with `NSMicrophoneUsageDescription` so TCC grants mic access.
16. R16 (FR-16): System contains no `langchain-openai`, no `secrets.toml`, no API-key auth; README/AGENTS.md describe Flet run + smoke commands.

## Constraints

- Zero outbound network after first-run model download; loopback only to
  127.0.0.1:11434 and 127.0.0.1:9001 (NFR-2, NFR-3).
- flet==0.86.5 exact in requirements until 1.0; changelog read before any
  upgrade (NFR-6).
- All product code inside src/text_c3po/; no cross-imports from the
  live-translate proof of concept.
- Never commit secrets; the cloud LLM surface stays removed by design.

## Done when

- SM-1: the 5x5 smoke matrix records at or above 95 percent JSON-valid per model.
- SM-2: median utterance end-to-end latency under 3s on the M4 reference path.
- vshanbha uses the app weekly and never re-adds a cloud key (validates FR-3,
  FR-10, FR-16).

## Boundaries

- Out of scope: cloud providers, API keys, SaaS accounts; token-streaming
  captions; diarization, translation memory and persisted history; WebRTC or
  browser streaming; non-macOS packaging.
- Touch point: src/text_c3po/ — the whole product; owner: epic-flet-shell-local-text-translation-core.

## References

- prd — _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
- architecture — _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
- design — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
- experience — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/EXPERIENCE.md
- brief — _bmad-output/initiative-text-c3po/brief-text-c3po-2026-09-08/brief-text-c3po-2026-09-08.md

## Notes

- Decision: 2026-09-16 (D9) packaging moved from E4 story 4.3 to E5 story 5.1;
  E4 closes without an installable artifact.
- Source conflict: PRD FR-14 is realised partly by E1 story 1.7 (the 5x5 gate) and
  partly by E4 story 4.2 (the 23-language matrix); both are recorded in the
  coverage map in the migration plan.
