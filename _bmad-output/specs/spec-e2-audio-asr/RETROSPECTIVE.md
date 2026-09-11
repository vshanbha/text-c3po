---
date: 2026-09-11
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# E2 Retrospective — Audio Capture + ASR

## Epic summary

- **Epic:** E2 (Audio Capture + ASR), spec folder `_bmad-output/specs/spec-e2-audio-asr/` (`SPEC.md`, stories 2-1–2-4 per `sprint-status.yaml`).
- **Stories completed:** 4/4 in one continuous run, one commit each: 2-1 device enumeration + picker (`d31a5f1`), 2-2 VAD chunker (`fc4fec2`), 2-3 whisper process manager (`a138112`), 2-4 file decode + shared ASR entry (`401f17e`), plus review pass (`0906a98`).
- **Evidence inventory (available):** SPEC.md CAP-1–CAP-4; three fresh-context review passes (blind bug-hunt, spec-alignment, edge-case — 21/21/~20 findings, triaged below); 131→133 unit tests green (deterministic: stubbed devices/frames/processes/HTTP); 6 live integration tests; live proofs — 5 real input devices enumerated (speakers excluded, USB mic defaulted), whisper ready in 0.4 s / `kill -9` → restarted / stop → zero orphans, German TTS wav → *"Good morning, how are you today?"* via whisper-small + lfm2.5.
- **Evidence inventory (missing):** native desktop eyeball of the device picker (headless construction only); BlackHole-absent path (present on this machine — code-reviewed, not live-proven); cold-model whisper readiness timing.

## Findings

- **F1 — Review earned its keep (9 patched).** Blind pass caught two verified-against-installed-flet defects: `FilePicker(on_result=)` does not exist in 0.86.5 and `pick_files` is async (2-4's file-pick flow was silently dead), and `Dropdown` has no `on_change` (only `on_select`) — which also fixed a latent E1 bug where the model picker never propagated selections. Spec pass caught the unwired CAP-3 manager (wired at launch + `atexit` in the same pass). Edge pass caught the redundant second probe pattern early. All patches re-verified live. Disposition: accept.
- **F2 — CAP-3 honest gap.** Launch spawn, readiness probe, crash detection at Start, and exit cleanup are delivered and live-proven; mid-session auto-restart is not (crash mid-session → gap rows + down dot, restart on next Start). Recorded as an accepted gap, not a defect — no story promised a monitor loop. Disposition: accept, revisit if E3 needs it (it didn't — E3 consumes gaps as designed).
- **F3 — Layering held.** `ui/` imports flet + `languages` only (device_picker, live_view, file_view verified); services compose runtimes; no live-translate imports (PoC RMS math re-implemented in stdlib, verified equivalent on constant frames). New deps: exactly one (`sounddevice==0.5.6`, spec-assumed). Disposition: accept.
- **F4 — A6 paths-helper follow-through landed early.** E1-A6 required E2 paths to reuse `paths.find_project_root()` instead of `__file__` joins; `default_model_path` initially shipped with the forbidden pattern (caught by the author's own test-track, not the review) and was refactored before merge. Disposition: accept, close A6.
- **F5 — Non-goals held.** No captions UI, no Start/Stop, no setup.sh, no 23-language matrix (all E3/E4). Disposition: accept.

## Behavior verification

- **First-hand this run:** `sounddevice` enumerated 7 devices → 5 inputs listed; `VadChunker` threshold/flush/max-utterance/reset paths (9 tests); `ProcessManager` ready 0.4 s, kill→restarted, stop→`pgrep` empty; `decode_to_wav` + `transcribe_wav` + `transcribe_file` on real German TTS; `setup.sh` BlackHole skip branch fires on re-run.
- **Inherited:** stub-matrix determinism for `run_matrix`; headless UI construction for pickers.
- **Explicitly not exercised:** picker eyeball on desktop; BlackHole-absent enumeration; cold-cache whisper readiness vs the 5 s timeout.

## Action items

None new. E1-A7 (native eyeball) is partially answered by the E4 browser E2E (`/neo-text-c3po-browser-e2e`: shell + dropdown + entry proven in a real browser; mode/button taps not automatable — recorded in TEST-PLAN §I). Standing rules restated for E3–E4: deterministic stub-first tests, live-verify-once per story, review every epic with fresh-context passes.

## Acceptance verdict

**accepted-with-open-items** — criteria **declared** (SPEC CAP-1–CAP-4 + Success signal). 4/4 stories done + reviewed + live-proven; the named open item is F2 (mid-session auto-restart, accepted gap).

## Open questions

1. Does the mid-session auto-restart gap need a monitor loop, or do gap rows + next-Start restart stay the contract? (E3 answered: stays.)
2. BlackHole-absent enumeration still unproven live — fold into the next fresh-machine setup run?

## Assumptions

- Single continuous implementation run (commits `d31a5f1`–`0906a98`); review was three parallel fresh-context passes (Task subagents) triaged by the implementer, not `bmad-code-review` (skill not installed).
- Live proofs ran on macOS Tahoe / Python 3.12 / ollama 0.33.3 / whisper-cpp / ffmpeg 9 / flet 0.86.5 with lfm2.5 + ggml-small.
