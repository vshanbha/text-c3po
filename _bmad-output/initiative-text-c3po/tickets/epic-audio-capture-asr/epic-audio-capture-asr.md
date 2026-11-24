---
type: epic
title: "Audio Capture + ASR"
parent: initiative-text-c3po
after: [epic-flet-shell-local-text-translation-core]
covers: [R6, R7, R8, R9]
sources:
  - _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e2-audio-asr/SPEC.md
  - _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
companions:
  - _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
  - _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
risk: medium
---

# Audio Capture + ASR

## Description

Text mode alone cannot follow a meeting or translate a recording — the PoC's RMS-VAD plus whisper-server pipeline proves the approach but only as throwaway terminal scripts. E2 ports that pipeline into the app's layered services (device enumeration, utterance chunking, managed whisper subprocess, file decode) so E3's live UI has real utterances to render and UJ-2/UJ-3 become possible.

## Outcome

On a machine without BlackHole, the app lists real devices, chunks live mic speech into utterances, transcribes them via its own managed whisper-server, and translates a picked audio file end-to-end — the full capture→ASR→translate path proven before any captions UI is built.

## Requirements

1. **R1 (CAP-1):** User can pick a capture device from the ffmpeg-enumerated list, with BlackHole shown only when present. (Originally built on sounddevice; reimplemented on ffmpeg avfoundation per D7-A story 5.) Success: With BlackHole absent the picker lists remaining devices and live capture still starts on mic; no hard-coded device names.
2. **R2 (CAP-2):** System can segment the int16 PCM stream into utterances via ported RMS-silence logic, flushing on 2 silent frames or max-utterance length. Success: Continuous speech yields ≥1 utterance per sentence cluster, 2s silence forces a flush; unit tests cover silence-threshold and max-utterance paths.
3. **R3 (CAP-3):** App can spawn whisper-server (transcribe only) on 127.0.0.1:9001 at launch, health-check it, restart on crash, and clean up on exit. Success: Readiness check passes within ~5s of launch; killing the subprocess triggers a restart attempt with visible status; app exit leaves no orphan process.
4. **R4 (CAP-4):** User can pick an audio/video file and run it through the same ASR→translate pipeline with no capture device present. Success: File path works with BlackHole absent and no device selected; unsupported containers error readably before any ASR call.

## Constraints

- Devices enumerated from ffmpeg avfoundation each launch (reimplemented per D7-A story 5; originally sounddevice); BlackHole listed only when present (AD-9).
- VAD emits immutable utterance WAV bytes (16 kHz mono s16le, RMS threshold, flush on 2 silent frames or max-utterance); file mode decodes via ffmpeg into the same ASR entry point (AD-9).
- whisper-server called transcribe-only over HTTP on `127.0.0.1:9001`; translation owned exclusively by the LLM (AD-7).
- One `ProcessManager` owns whisper spawn (default `ggml-small.bin`), health-check, restart-on-crash, cleanup-on-exit; missed utterances during restart labeled as gaps, never silently dropped (AD-8).
- Whisper `-l` flag receives the code from the single 23-language constant (AD-10).
- Pipeline threads never touch Flet controls; results flow up via callbacks/queues to the session controller (AD-2, AD-4).
- All product code inside `text-c3po/`; VAD logic re-implemented from the PoC, no cross-imports from `live-translate/`.

## Done when

- On a machine without BlackHole, the app lists real devices, chunks live mic speech into utterances, transcribes them via its own managed whisper-server, and translates a picked audio file end-to-end — the full capture→ASR→translate path proven before any captions UI is built.

## Boundaries

- Captions pane rendering, Start/Stop toggle, status indicators, session list ownership (E3).
- Text-mode translation changes beyond reusing the E1 service with `{text, source_lang}` utterance payloads.
- setup.sh ffmpeg/BlackHole install guidance, soak/latency gates (E4).
- Token-streaming ASR partials, diarization, persisted audio.

## References

- parent — _bmad-output/initiative-text-c3po/initiative-text-c3po.md, section Requirements
- spec — _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e2-audio-asr/SPEC.md
- prd — _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
- architecture — _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
- design — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
- experience — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/EXPERIENCE.md

- Waits on epic-flet-shell-local-text-translation-core: the E1 translation service
