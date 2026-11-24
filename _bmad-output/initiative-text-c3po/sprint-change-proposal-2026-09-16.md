---
date: 2026-09-16
type: sprint-change-proposal
trigger: failed manual test — BlackHole in-call capture (TEST-PLAN §F7 §J gate)
status: approved 2026-09-16 — D7-A by owner, folded into spec-e2 stories.yaml + memlog
owner: vshanbha
decided: 2026-09-16
decisions:
  D7: A — full swap to ffmpeg avfoundation pipeline
epics_impacted: [E2, E3, E4]
artifacts_impacted: [spec-e2-audio-asr, ARCHITECTURE-SPINE, EXPERIENCE, DESIGN, TEST-PLAN, AGENTS.md, blueprint]
mode: single
---

# Sprint Change Proposal — text-c3po v2 (2026-09-16)

Produced from the 2026-09-15 brainstorming session
(`brainstorm-blackhole-call-capture-failure-2026-09-15`) and follow-up
code review of `live-translate/`. Triggered by failed manual test:
BlackHole loopback capture during a live call auto-stops immediately on
Start, across all listed devices.

## Section 1 — Issue Summary

**Trigger.** TEST-PLAN §J gate — §F (real-mic live session) was never
exercised with real hardware. First manual attempt: pick BlackHole 2ch,
start a call, press Start. Result: auto-stop (UI resets to Idle) on
every device, no error message shown.

**Problem statement.** The E2 capture path uses `sounddevice` (PortAudio)
which is fundamentally broken for BlackHole loopback capture on macOS:

1. **Forced 16 kHz mono** — `open_input_stream` (`live_runner.py:26-36`)
   hardcodes `samplerate=16000, channels=1, dtype=int16`. BlackHole's
   native rate is 48 kHz stereo. PortAudio either rejects the resample
   (deterministic `open-failed`) or silently produces garbage frames.
2. **Name-vs-index collision** — device picker stores verbatim name
   strings (`audio_devices.py:56`); `sd.InputStream(device=name)` can
   resolve to the output instance when duplicate / aggregate names exist.
3. **5-second silent timeout** — `process_manager.py:29 READY_TIMEOUT_S=5.0`
   is tighter than cold model load; `app.py:1345-1350` resets UI to Idle
   with **no error message** on `ensure_running()=="failed"`.
4. **Hog-mode contention** — Zoom/Teams hold the mic HAL; second
   `InputStream` open fails silently or `stream.read()` throws instantly,
   triggering `_on_live_ended_naturally` (`app.py:1282`) reset.

**Root cause.** sounddevice/PortAudio is the wrong abstraction for this
use case. The live-translate PoC already solved it: `ffmpeg -f avfoundation`
handles device enumeration, open, resample, and format conversion in one
pipeline (`live-translate/live-translate:29-31`). text-c3po's E2 spec
(SPEC-e2-audio-asr line 36) still assumes sounddevice.

**Evidence.**
- `live-translate/live-translate:10-12` — ffmpeg lists devices natively
- `live-translate/live-translate:29-31` — ffmpeg captures at native rate,
  resamples to 16k mono s16le internally, pipes to Python stdin
- `live-translate/transcribe.py:83` — identical VAD logic reads
  `sys.stdin.buffer.read(FRAME_BYTES)`, works on BlackHole
- `text-c3po/services/live_runner.py:26-36` — sounddevice demands
  16kHz/mono/int16, no native-rate negotiation, no fallback
- `text-c3po/runtimes/audio_devices.py:20-22` — `sd.query_devices()`
  enumerates by name, no index stability

## Section 2 — Impact Analysis

**Epic impact.**
- **E2** — CAP-1 (device enumeration) and capture mechanism fully
  rewritten; CAP-2 (VAD), CAP-3 (whisper), CAP-4 (file decode) unchanged.
- **E3** — device picker behavior preserved; new failure mode "ffmpeg
  absent" vs "no devices" needs UX coverage; stop-within-2s now bounds
  subprocess teardown.
- **E4** — setup.sh PortAudio block removable; ffmpeg already installed;
  TCC mic permission now applies to ffmpeg spawned by the app (verify
  bundle inherits NSMicrophoneUsageDescription).

**Files changed (blast radius).**

| File | Change |
|---|---|
| `runtimes/audio_devices.py` | Full rewrite — `sd.query_devices()` → `ffmpeg -f avfoundation -list_devices` parse |
| `services/live_runner.py` | `open_input_stream` → ffmpeg subprocess + pipe adapter; overflow/abort redefined for pipes |
| `pyproject.toml` + `requirements.txt` | Remove `sounddevice==0.5.6` |
| `uv.lock` | Regenerate (drops cffi/pycparser transitive) |
| `setup.sh` | Remove PortAudio install block (lines 51-55) |
| `ARCHITECTURE-SPINE.md` | Amend AD-9 (sounddevice→ffmpeg), AD-13 (PortAudio→ffmpeg), tech-lock line 148 |
| `EXPERIENCE.md` line 58 | Update "sounddevice devices" → "ffmpeg/avfoundation devices" |
| `TEST-PLAN.md` §C1-C4 | Re-anchor to ffmpeg/avfoundation |
| `AGENTS.md` | Refresh managed block (ffmpeg capture) |
| `blueprint.md` lines 37, 87, 99 | Update capture mechanism reference |
| `test_units.py` | Rewrite ~4-5 tests (monkeypatch targets, fake-stream shape, open_input_stream close) |

**Files NOT changed.**
- `services/vad.py` — hardware-agnostic, consumes raw bytes
- `services/asr.py` — shared entry point, ffmpeg-compatible
- `ui/live_view.py`, `ui/device_picker.py` — pure Flet, no hardware imports
- `runtimes/audio_file.py` — already uses ffmpeg, becomes the template
- `services/session.py`, `services/translation.py` — upstream consumers, frame contract holds

**No rollback required.** sounddevice was never exercised on real
hardware (§J gate: "the live path has never run with a real microphone").
No completed work is invalidated.

## Section 3 — Recommended Approach

**Option 1: Direct swap (recommended).** Replace the two sounddevice
binding points (enumeration + capture) with ffmpeg equivalents, following
the pattern already established by `audio_file.py`. No new dependencies —
ffmpeg is already a system prerequisite. Effort: Medium. Risk: Low
(narrow blast radius, injectable factory design, existing precedent).

**Option 2: Keep sounddevice + add ffmpeg fallback.** Dual-path capture
with sounddevice primary, ffmpeg fallback. Effort: High. Risk: Medium
(two code paths to maintain, sounddevice still broken for BlackHole).

**Option 3: Fix sounddevice (native-rate negotiation).** Query native
rate, open at native, resample in Python. Effort: Medium. Risk: Medium
(PortAudio hog-mode and name-collision issues remain).

Rationale: Option 1 is the simplest path to a working product. sounddevice
was never validated on real hardware; ffmpeg is proven in live-translate;
the blast radius is narrow thanks to the existing injectable factory
design.

## Section 4 — Detailed Change Proposal

### D7 — Replace sounddevice capture with ffmpeg avfoundation pipeline

- **Affected:** E2 CAP-1, AD-9, AD-13, tech-lock, `audio_devices.py`,
  `live_runner.py`, `pyproject.toml`, `setup.sh`, tests, docs.

- **Options.**
  - **A (recommended) — full swap.** Two binding points rewrite:
    1. `audio_devices._query_all_devices` → parse `ffmpeg -f avfoundation
       -list_devices true -i ""` stderr, extract input device names by
       index. Preserve `list[str]` contract, `has_blackhole`, `pick_default
       _device` helpers unchanged.
    2. `open_input_stream` → spawn `ffmpeg -f avfoundation -i ":DEVICE"
       -ac 1 -ar 16000 -f s16le -`, wrap stdout as adapter providing
       `read() → (bytes, False)`, `stop/close/terminate`. No overflow
       concept in pipes; remove overflow gap path or redefine as pipe-lag.
    3. Remove `sounddevice==0.5.6` from deps; remove PortAudio from
       setup.sh; regenerate lock.
    4. Amend AD-9, AD-13, tech-lock in ARCHITECTURE-SPINE.
    5. Rewrite ~4-5 unit tests; preserve ~10 via injection.
  - **B — dual-path (sounddevice primary, ffmpeg fallback).** Keeps
    sounddevice for mic-only machines, falls back to ffmpeg for
    BlackHole/aggregate. Effort High, Risk Medium.
  - **C — sounddevice native-rate fix only.** Query rate, resample in
    Python. Doesn't fix hog-mode or name-collision. Effort Medium,
    Risk Medium.

- **Rationale:** A is the proven path (live-translate). B adds complexity
  for a codepath that was never validated. C is a partial fix that
  leaves two of four root causes unresolved.

- **Success criteria:**
  1. `list_devices()` returns ffmpeg/avfoundation input devices, BlackHole
     shown only when present.
  2. `open_input_stream("BlackHole 2ch")` opens a 16 kHz mono s16le pipe
     that yields valid PCM frames.
  3. Live capture Start on BlackHole during a call produces captions
     (§F7 passes).
  4. Device unplug mid-session yields graceful reset (§F14 passes).
  5. `sounddevice` absent from `pyproject.toml`, `requirements.txt`,
     `uv.lock`, and `setup.sh`.
  6. Unit suite green; no import of sounddevice anywhere in `src/`.

## Section 5 — Implementation Handoff

- **Scope classification:** **Moderate** — two binding-point rewrites
  plus doc/test updates; no fundamental replan.
- **Prerequisite:** owner approval of D7 choice (A/B/C).
- **Recommended story structure:** single story in E2 (replacing or
  amending Story 2.1), with subtasks:
  1. Rewrite `audio_devices.py` (ffmpeg enumeration)
  2. Rewrite `open_input_stream` (ffmpeg subprocess + pipe adapter)
  3. Remove sounddevice dependency, regenerate lock
  4. Amend architecture spine (AD-9, AD-13, tech-lock)
  5. Rewrite affected unit tests
  6. Update TEST-PLAN §C wording
  7. Manual verification: §F7 (BlackHole loopback), §F14 (device unplug)
- **Owner override needed:** D7 choice. No PM/Architect sign-off
  required (scope within existing E2 boundary).
- **Spec ownership rule:** SPEC.md is derived by `bmad-spec`; decisions
  are first appended to the owning `.memlog.md`, then re-derived — never
  hand-edit SPEC.md.
- **Tracking:** after approval, run `bmad-sprint-planning` to refresh
  `sprint-status.yaml`.

## Decision register (approve / edit / skip)

| ID | Decision to make | Recommendation | Proposed downstream story |
|----|------------------|----------------|---------------------------|
| D7 | Capture mechanism: sounddevice or ffmpeg | A — full swap to ffmpeg | E2 story (amend Story 2.1) |

## Approval record

Approved 2026-09-16 by owner vshanbha: **D7-A — full swap to ffmpeg.**
Rationale accepted: proven in live-translate, narrow blast radius,
no new dependencies, injectable factory design.

Next: fold into stories + memlogs (done: spec-e2 story 5 + memlog),
refresh sprint-status, dispatch story 5 with bmad-build.
