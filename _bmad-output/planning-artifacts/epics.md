# Epics — text-c3po v2 (derived 2026-09-08)

Derived from `_bmad-output/specs/spec-e*/SPEC.md` + `stories.yaml`.
Source of truth stays the SPECs; this file exists as the `sprint_plan.py`
parser input (`## Epic N:` / `### Story N.M:` headings). Regenerate from
stories.yaml if titles change, then rerun sprint planning to refresh
`_bmad-output/implementation-artifacts/sprint-status.yaml`.

## Epic 1: Flet Shell + Local Text Translation Core

Source: `_bmad-output/specs/spec-e1-shell-core/SPEC.md` (SPEC-e1-shell-core).
Build scope: this epic only. Exit gate: 5x5 smoke matrix ≥95% JSON-valid per model.

### Story 1.1: Scaffold Flet app shell and pinned requirements

Create text-c3po/app.py entry plus ui/services/runtimes packages and
requirements.txt with the flet==0.86.5 pin confirmed against the changelog;
app launches to an empty single window per CAP-1. No translation or Ollama
code in this story.

### Story 1.2: Top strip with three-mode switching

Add the always-visible top strip with Text/Live/File SegmentedButton; Live
and File show placeholder surfaces while Text hosts the input; switching
preserves process and model pick per CAP-1. Text is the launch default;
minimum window 960x640.

### Story 1.3: Ship the 23-language constant and pickers

Add text-c3po/languages.py with the 23 {code, name} pairs verbatim from
blueprint section 2.1 and bind target (plus source-override) Dropdowns to
it per CAP-5.

### Story 1.4: Ollama client with launch connectivity check

Add runtimes/ollama_client probing 127.0.0.1:11434 at startup with
connected/not-running top-strip state and Retry action per CAP-2. List
models live from /api/tags; no hard-coded model names except the lfm2.5
default rule owned by story 1.5.

### Story 1.5: Model picker with lfm2.5 default rule

Add the top-strip model Dropdown listing exactly /api/tags output plus
Refresh; preselect lfm2.5 when present else first available per CAP-4.
Changing mid-session applies to the next call only, never retroactively.

### Story 1.6: Text translation service and Text mode wiring

Add services/translation on ChatOllama with enforced JSON format and
JsonOutputParser to the full Translation schema; wire Text mode input,
Translate button, three output cards plus origin caption, inline retryable
errors, and empty-input guard per CAP-3. Malformed JSON never reaches the
UI raw; errors render inline plus SnackBar retry, no dialogs.

### Story 1.7: E1 gate — 5-language by 5-sentence smoke harness

Add services/eval_harness running the repeatable 5x5 matrix over installed
models reusing the translation service with model as parameter; record
JSON-validity scores to research.md per CAP-6 and SM-1. E1 exit gate:
>=95% JSON-valid per model. Full 23-language matrix stays E4 scope.

## Epic 2: Audio Capture + ASR

Source: `_bmad-output/specs/spec-e2-audio-asr/SPEC.md` (SPEC-e2-audio-asr).
Tracked as planned; not in E1 build scope. Depends on E1 translation service.

### Story 2.1: Sounddevice device enumeration and picker source

Add runtimes/audio_devices querying sounddevice each launch with no
hard-coded names; expose the list for the E3 device picker with BlackHole
present-only per CAP-1.

### Story 2.2: Port VAD chunker with unit tests

Add services/vad re-implementing the PoC RMS-silence plus
flush-on-2-silent-frames-or-max-utterance logic emitting immutable 16 kHz
mono s16le utterance bytes; cover both flush paths with unit tests per
CAP-2. Re-implement from live-translate/transcribe.py patterns; no imports
from live-translate/.

### Story 2.3: Whisper process manager with health and restart

Add runtimes/process_manager plus runtimes/whisper_client owning spawn
(ggml-small.bin default), readiness check, restart-on-crash with visible
status, and cleanup-on-exit; transcribe-only on 127.0.0.1:9001 per CAP-3.
Utterances missed during restart are labeled as gaps, never silently
dropped.

### Story 2.4: File decode path into the shared ASR entry point

Add ffmpeg decode feeding picked audio/video files into the same ASR entry
point as live utterances with readable pre-ASR errors for unsupported
containers; works with no device and BlackHole absent per CAP-4. Assume
mp3/wav/m4a/mp4 floor; translation reuses the E1 service.

## Epic 3: Live Captions UI + Session State

Source: `_bmad-output/specs/spec-e3-live-ui/SPEC.md` (SPEC-e3-live-ui).
Tracked as planned; not in E1 build scope. Composes E1 services and E2
runtimes only; no new ASR or translation logic.

### Story 3.1: Session controller with owned caption list

Add services/session as sole mutator of the ordered in-memory caption list
draining the utterance queue; mode switch preserves the list while new
Start or app close clears it per CAP-3. Only the main thread touches Flet
controls.

### Story 3.2: Captions pane with history and timestamps

Build ui/live_view captions ListView appending rows in
utterance-completion order with mono timestamps, auto-follow plus
scroll-back escape and Jump-to-latest, utterance-flush only per CAP-1.
Announce each new row via live region at utterance granularity.

### Story 3.3: Start-Stop toggle with live status indicators

Wire the Start/Stop FilledButton (label is the state) with capture,
whisper-latency, and model dot-plus-label indicators reflecting live
state; Stop halts capture within 2s and restart needs no relaunch per
CAP-2. Live red is capture-running only; failures render inline plus
SnackBar retry, never a dialog.

### Story 3.4: Live pickers, file surface, and session-state polish

Bind device, source, and target Dropdowns to the E2 enumeration and the
23-language constant with auto-detect-where-supported source default;
compose the file surface (picker row, progress, results list reusing the
caption-row pattern) on the E2 decode path; verify mode-switch retention
and memory-only session labeling per CAP-4 and CAP-3. Any
model-by-language combo stays submittable; quality is measured in E4.

### Story 3.5: Fix captions auto-follow and Jump-to-latest wiring

Forward the ListView scroll event into on_pane_scroll so the USER filter
works; follow disables only on a genuine user scroll and Jump re-enables
it per CAP-1. Audit defect: the event was dropped, so every scroll
disabled follow.

### Story 3.6: Decouple translation from capture loop and label overflow

Keep the LLM drain off the capture read path so frames are still read
during translation, and surface PortAudio overflow as labeled gap rows
per AD-8. Audit defect: synchronous drain inside the read loop plus a
discarded overflow flag could silently drop speech.

### Story 3.7: Fix session queue and seq races on start and gap

Assign the mark_gap sequence and append under one lock; stop
start_session silently discarding queued utterances and label them as a
gap per AD-8. Audit defect: two-lock mark_gap could reorder rows.

### Story 3.8: Relabel source picker to Auto-detect (D2-A)

Remove the false affordance of the Live/File source-language dropdown:
relabel as read-only Auto-detect (or remove) to match the `-l auto`
whisper behavior per D2-A approved 2026-09-13; functional per-language
whisper restart deferred out of v1.

### Story 3.9: Build main-thread render pump (D3-B)

Serialize all Flet control mutation through a single main-thread render
queue/pump per D3-B approved 2026-09-13 (owner override of ratify);
background threads post dicts only. E3-6 lands first, then the pump.

### Story 3.10: Document and test global Stop scope (D4-A)

Document Text Stop as global abort per D4-A approved 2026-09-13 (owner
override of per-mode); add unit test asserting concurrent File/retry work
is aborted by Text Stop.

## Epic 4: Ops, Eval & Polish

Source: `_bmad-output/specs/spec-e4-ops-eval-polish/SPEC.md`
(SPEC-e4-ops-eval-polish). Tracked as planned; not in E1 build scope.
Closes the blueprint section-6 gates.

### Story 4.1: setup.sh for clean-machine install

Add setup.sh covering Ollama install, model pull, PortAudio/sounddevice,
ffmpeg check, and BlackHole guidance; clean-machine run completes in
<=15 min with missing BlackHole as guidance per CAP-1.

### Story 4.2: Extend harness to the full 23-language matrix

Extend services/eval_harness from the E1 5x5 gate to sample sentences by
all 23 languages by installed models, recording per-language scores and
JSON-validity to research.md with comparable rows per CAP-2. Reuse the
translation service with model as parameter; never gate UI combos on
scores.

### Story 4.3: Package macOS bundle with mic permission

Ship the installable macOS bundle (flet build macos or PyInstaller
--windowed decision recorded) carrying NSMicrophoneUsageDescription so
first Live start prompts and TCC grants mic access per CAP-3. Bundle runs
loopback-only to 127.0.0.1:11434 and 127.0.0.1:9001 after download.

### Story 4.4: Regression tests for VAD parser and whisper health

Add tests covering VAD silence-threshold and max-utterance flush paths,
JSON parser valid-plus-malformed cases, and whisper-server health; suite
passes post-setup.sh per CAP-4.

### Story 4.5: Remove cloud surface and refresh docs

Delete all langchain-openai code and secrets.toml, then refresh README and
AGENTS.md with the true Flet run, smoke, and harness commands; grep plus
absence check both return empty per CAP-5. Never commit secrets; do not
use streamlit run to verify v2.

### Story 4.6: Publish updated docs to GitHub Pages

Replace the stub hosting experiment with a real docs landing page and
publish via the static.yml Pages workflow per CAP-6. Delivered by the
MkDocs Material migration; tracked here after the audit found it missing
from sprint-status.

### Story 4.7: Fix unit CI and repair sprint tracking

Make the web-serve smoke runnable without uv, stop masking empty
collection, and reconcile stories.yaml with sprint-status.yaml. Audit
defect: the master unit run is red (FileNotFoundError 'uv').

### Story 4.8: Refresh stale v1 docs and infra

Update the parent workspace AGENTS.md, fix .devcontainer, drop the stale
pyproject "no CI" comment, and pin docs/requirements.txt. Audit hygiene;
no behavior change.
