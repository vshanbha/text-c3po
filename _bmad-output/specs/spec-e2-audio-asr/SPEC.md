---
id: SPEC-e2-audio-asr
companions:
  - ../../planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
sources:
  - ../../planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - ../../../../blueprint.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# E2 — Audio Capture + ASR

## Why

Text mode alone cannot follow a meeting or translate a recording — the PoC's RMS-VAD plus whisper-server pipeline proves the approach but only as throwaway terminal scripts. E2 ports that pipeline into the app's layered services (device enumeration, utterance chunking, managed whisper subprocess, file decode) so E3's live UI has real utterances to render and UJ-2/UJ-3 become possible.

## Capabilities

- **CAP-1**
  - **intent:** User can pick a capture device from the sounddevice-enumerated list, with BlackHole shown only when present.
  - **success:** With BlackHole absent the picker lists remaining devices and live capture still starts on mic; no hard-coded device names.
- **CAP-2**
  - **intent:** System can segment the int16 PCM stream into utterances via ported RMS-silence logic, flushing on 2 silent frames or max-utterance length.
  - **success:** Continuous speech yields ≥1 utterance per sentence cluster, 2s silence forces a flush; unit tests cover silence-threshold and max-utterance paths.
- **CAP-3**
  - **intent:** App can spawn whisper-server (transcribe only) on 127.0.0.1:9001 at launch, health-check it, restart on crash, and clean up on exit.
  - **success:** Readiness check passes within ~5s of launch; killing the subprocess triggers a restart attempt with visible status; app exit leaves no orphan process.
- **CAP-4**
  - **intent:** User can pick an audio/video file and run it through the same ASR→translate pipeline with no capture device present.
  - **success:** File path works with BlackHole absent and no device selected; unsupported containers error readably before any ASR call.

## Constraints

- Devices enumerated from sounddevice each launch; BlackHole listed only when present (AD-9).
- VAD emits immutable utterance WAV bytes (16 kHz mono s16le, RMS threshold, flush on 2 silent frames or max-utterance); file mode decodes via ffmpeg into the same ASR entry point (AD-9).
- whisper-server called transcribe-only over HTTP on `127.0.0.1:9001`; translation owned exclusively by the LLM (AD-7).
- One `ProcessManager` owns whisper spawn (default `ggml-small.bin`), health-check, restart-on-crash, cleanup-on-exit; missed utterances during restart labeled as gaps, never silently dropped (AD-8).
- Whisper `-l` flag receives the code from the single 23-language constant (AD-10).
- Pipeline threads never touch Flet controls; results flow up via callbacks/queues to the session controller (AD-2, AD-4).
- All product code inside `text-c3po/`; VAD logic re-implemented from the PoC, no cross-imports from `live-translate/`.

## Non-goals

- Captions pane rendering, Start/Stop toggle, status indicators, session list ownership (E3).
- Text-mode translation changes beyond reusing the E1 service with `{text, source_lang}` utterance payloads.
- setup.sh PortAudio/BlackHole install guidance, soak/latency gates (E4).
- Token-streaming ASR partials, diarization, persisted audio.

## Success signal

On a machine without BlackHole, the app lists real devices, chunks live mic speech into utterances, transcribes them via its own managed whisper-server, and translates a picked audio file end-to-end — the full capture→ASR→translate path proven before any captions UI is built.

## Assumptions

- Assumed PortAudio present post-setup (`brew install portaudio` + pip sounddevice); verified absent pre-E2.
- Assumed `ggml-small.bin` is the default whisper model (~2s ready); medium optional via flag.
- Assumed file container floor is mp3 / wav / m4a / mp4 (PRD Q2).

## Open Questions

- File-mode scope: which containers must pass E2 (mp3/wav/m4a/mp4 minimum set)?
