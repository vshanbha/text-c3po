---
title: text-c3po v2 — Local-first Live Translator
status: final
created: 2026-09-08
updated: 2026-09-08
---

# PRD: text-c3po v2 — Local-first Live Translator

## 0. Document Purpose

For vshanbha (solo builder) and downstream `bmad-ux`, `bmad-architecture`, and `bmad-create-epics-and-stories`. Structure: Glossary-anchored vocabulary; Features grouped by epic (E1–E4) with globally numbered FRs; cross-cutting NFRs in §8; inferences tagged `[ASSUMPTION: …]` and indexed in §11. Builds on `brief-text-c3po-2026-09-08/brief.md`, the two `technical-*` research reports, and `blueprint.md` — it does not re-argue their evidence.

## 1. Vision

text-c3po v1 is a Streamlit + cloud-key translator; the live-translate PoC proves near-realtime speech→translate on macOS but only as terminal scripts. v2 merges both into one Flet desktop app with three modes — Text, Live, File — all running locally: type or speak or drop a file, get a structured translation, no keys, no SaaS, no browser.

After first-run model download the machine goes quiet: zero outbound traffic, loopback only to Ollama and whisper-server. The backend stays model-agnostic across 23 aspirational languages; the eval harness tells the user which model×language combos are actually good.

## 2. Target User

### 2.1 Jobs To Be Done

- Translate a sentence or paragraph right now without signing up, pasting a key, or opening a browser.
- Follow a live meeting or video in another language via running translated captions.
- Translate a recorded audio/video file with the same pipeline as live speech.
- Swap local models freely and see which one handles my languages best.

### 2.2 Non-Users (v1)

Cloud-API users, teams needing shared history/TM, anyone needing token-streaming captions, diarization, or non-macOS packaging.

### 2.3 Key User Journeys

- **UJ-1. vshanbha translates a paragraph before sending it.** At his Mac, Flet app open on Text mode, he pastes English, picks German, picks model lfm2.5, and gets formal/informal/commentary back as structured output.
- **UJ-2. vshanbha follows a live talk with captions.** In Live mode he picks BlackHole (or Built-in Mic), target language, presses Start, and watches timestamped translated utterances accumulate; he presses Stop and the session stays readable.
- **UJ-3. vshanbha translates a recorded clip.** In File mode he picks an audio/video file without any capture device present and gets the same ASR→translate captions as live.

## 3. Glossary

- **Translation** — Structured output for one input: formal, informal, commentary, origin_language (text mode) or lightweight `{text, source_lang}` (live/file utterances).
- **Utterance** — One VAD-delimited speech chunk: RMS silence threshold, flush on 2 silent frames or max-utterance length.
- **Caption** — A displayed Translation of one Utterance with timestamp in the live captions pane.
- **Session** — One Start→Stop live run; owns an ordered Caption list.
- **Source language** — Detected or selected input language code from the 23-language constant.
- **Target language** — User-selected output language code from the 23-language constant.
- **Model** — An installed Ollama model listed via `/api/tags`; suggested default lfm2.5.
- **ASR** — Transcribe-only speech recognition via whisper-server subprocess on 127.0.0.1:9001.

## 4. Features — E1 Text mode + shell

### 4.1 Flet shell and mode switching

**Description:** Single native Flet window (no webserver) with buttons/toggles for Text / Live / File. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-1: Switch modes in one window

User can switch between Text, Live, and File modes via buttons/toggles without restart. Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**

- All three mode surfaces reachable within 2 clicks/taps from launch.
- Switching modes does not kill the app process or require re-picking the Model.

#### FR-2: Check Ollama connectivity at launch

App can probe Ollama at 127.0.0.1:11434 on startup and show connected / not-running state.

**Consequences (testable):**

- With `ollama serve` stopped, UI shows not-running guidance within 5s of launch.
- With it running, state flips to connected without restart.

### 4.2 Local text translation core

**Description:** Text mode: input + Target language + Model picker → ChatOllama with JSON format enforced → Translation. Realizes UJ-1.

**Functional Requirements:**

#### FR-3: Translate typed text to structured Translation

User can submit typed text with a Target language and receive formal / informal / commentary / origin_language. Realizes UJ-1.

**Consequences (testable):**

- Valid input returns all four fields; malformed JSON from the Model never reaches the UI raw — it surfaces as a retryable error.
- Empty input is rejected client-side with a hint, no LLM call issued.

#### FR-4: Pick Model from installed list with default

User can pick any installed Ollama Model listed from `/api/tags`; default preselects lfm2.5 when present, else first available. Realizes UJ-1.

**Consequences (testable):**

- Picker lists exactly the models `/api/tags` returns at launch (+ refresh action).
- Default selection rule holds on clean and lfm2.5-absent machines.

#### FR-5: Ship the 23-language constant

App can offer the 23 `{code, name}` languages from blueprint §2.1 as the Target language (and Source language override) list.

**Consequences (testable):**

- Picker contains all 23 codes/names verbatim; whisper `-l` flag receives the matching code.
- Selecting any listed Model with any of the 23 languages issues a translation call with no client-side block (quality is model-dependent, measured in E4). `[ASSUMPTION: model-agnostic backend — quality variance handled by eval, not by gating.]`

## 5. Features — E2 Audio capture + ASR

**Description:** sounddevice capture plus whisper-server lifecycle plus file path. Realizes UJ-2, UJ-3. `[ASSUMPTION: PortAudio present post-setup — E2 unblocked by brew install portaudio + pip sounddevice.]`

**Functional Requirements:**

#### FR-6: Pick capture device from available devices

User can choose between Built-in Microphone and BlackHole when present; when BlackHole is absent only available sounddevice devices list. Realizes UJ-2.

**Consequences (testable):**

- With BlackHole uninstalled, picker shows remaining devices and Live mode still starts on mic.
- No hard-coded device names; list comes from sounddevice query each launch.

#### FR-7: Chunk audio into Utterances (VAD)

System can segment the int16 PCM stream into Utterances via ported RMS-silence + flush-on-2-silent-frames-or-max-utterance logic. Realizes UJ-2.

**Consequences (testable):**

- Continuous speech yields ≥1 Utterance per spoken sentence cluster; 2s silence forces a flush.
- VAD unit tests cover silence-threshold and max-utterance flush paths.

#### FR-8: Manage whisper-server subprocess lifecycle

App can spawn `whisper-server` (transcribe only) on 127.0.0.1:9001 at launch, health-check it, restart on crash, and clean up on exit. Realizes UJ-2, UJ-3.

**Consequences (testable):**

- `GET /health`-equivalent check passes within ~5s of launch (ggml-small ready in ~2s per research). `[ASSUMPTION: ggml-small.bin is the default whisper model.]`
- Killing the subprocess triggers a restart attempt with visible status; app exit leaves no orphan `whisper-server`.

#### FR-9: Translate an audio/video file without capture hardware

User can pick an audio/video file and run it through the same ASR→translate pipeline as live. Realizes UJ-3.

**Consequences (testable):**

- File path works with no capture device selected and BlackHole absent.
- Unsupported container surfaces a readable error before any ASR call.

## 6. Features — E3 Live captions UI

**Description:** Captions pane, session controls, status. Realizes UJ-2.

**Functional Requirements:**

#### FR-10: Show live Captions with history and timestamps

User can watch Utterance Captions append in order with timestamps and scroll back through the Session. Realizes UJ-2.

**Consequences (testable):**

- Each Caption shows translated text + timestamp; ordering matches Utterance completion order.
- Utterance-level flush only — no token-streaming partial rendering required in v1.

#### FR-11: Start and stop a Session with visible status

User can start/stop capture→ASR→translate via toggle; UI shows capture-active, whisper latency, and active Model. Realizes UJ-2.

**Consequences (testable):**

- Stop halts capture within 2s; restart begins a new Session without app relaunch.
- Status indicators reflect actual subprocess/model state, not cached startup values.

#### FR-12: Hold Session state for the Caption list

System can retain the ordered Caption list for the active Session until the user starts a new one or closes the app. Realizes UJ-2.

**Consequences (testable):**

- Mode switch away and back does not clear the active Session list.
- No persistence across restarts required in v1 (memory-only).

## 7. Features — E4 Ops, eval, polish

**Description:** Setup, quality proof, packaging, cleanup. Serves all UJs by making v2 installable and trustworthy.

**Functional Requirements:**

#### FR-13: Guide clean-machine setup via script

New user can run `setup.sh` covering Ollama install, Model pull, PortAudio/sounddevice, and BlackHole guidance. Serves all UJs.

**Consequences (testable):**

- Clean-machine run completes in ≤15 min on broadband (measured NFR-5).
- Missing BlackHole is guidance, not a setup failure.

#### FR-14: Score models on the language matrix (repeatable harness)

Builder can run a repeatable eval harness (sample sentences × languages × installed Models) recording JSON-validity and per-language scores. Serves UJ-1.

**Consequences (testable):**

- E1 exit gate: 5-language × 5-sentence matrix recorded; E4: full 23-language matrix recorded.
- Re-running with a new Model appends a comparable score row without code changes.

#### FR-15: Package a signed macOS app with mic permission

User can install the Flet-built (or PyInstaller `--windowed`) macOS bundle with `NSMicrophoneUsageDescription` so TCC grants mic access. Serves UJ-2.

**Consequences (testable):**

- Packaged app prompts for mic with explanatory string on first Live start.
- Bundle runs with Ollama + whisper-server reachable on loopback only.

#### FR-16: Remove cloud dependencies and refresh docs

System contains no `langchain-openai`, no `secrets.toml`, no API-key auth; README/AGENTS.md describe Flet run + smoke commands.

**Consequences (testable):**

- `grep -ri openai` over product code and `secrets.toml` presence check both return empty.
- README documents the v2 run command and the eval-harness command actually wired in E1/E4.

## 8. Cross-Cutting NFRs

- **NFR-1 Caption latency:** <3s end-to-end per Utterance (ASR ~0.4s/9s audio on M4 `[ASSUMPTION: Apple-silicon reference hardware]` + LLM first token), utterance-flush granularity.
- **NFR-2 Offline:** Zero outbound network after first-run Model download; all inference local.
- **NFR-3 Loopback-only:** After download, only loopback traffic to Ollama at 127.0.0.1:11434 and whisper-server at 127.0.0.1:9001; verified by loopback-only check in E4.
- **NFR-4 Soak stability:** 5-min continuous live speech with no unbounded memory growth.
- **NFR-5 Setup budget:** Clean-machine `setup.sh` ≤15 min.
- **NFR-6 Dependency pin:** `flet==0.86.5` exact in requirements until 1.0; changelog read before any upgrade.

## 9. Non-Goals (Explicit)

- Cloud LLM providers, API keys, SaaS accounts — removed by design.
- Token-streaming captions; v1 flushes per Utterance only.
- Diarization, translation memory, persisted chat history.
- WebRTC / browser streaming; no Streamlit, no webserver.
- Non-macOS packaging (Linux/Windows guides welcome, untested).

## 10. MVP Scope

### 10.1 In Scope

- Flet shell with Text/Live/File switching, Ollama check, Model + 23-language pickers.
- Text translation to formal/informal/commentary/origin_language via ChatOllama JSON mode.
- Mic/BlackHole capture, VAD chunking, whisper-server subprocess lifecycle, file-picker path.
- Live captions pane with timestamps, Start/Stop, status indicators, in-memory Session.
- setup.sh, eval harness (5×5 gate → 23-language matrix), macOS packaging with mic string, VAD/parser/health tests, OpenAI removal + docs refresh.

### 10.2 Out of Scope for MVP

- Cloud fallback or key-based models (by design; never).
- Streaming captions, diarization, TM, history persistence (deferred to v2+; persistence is the most likely revisit `[NOTE FOR PM]`).
- Non-macOS bundles (deferred; guides accepted).

## 11. Success Metrics

Success: vshanbha uses the local app weekly for real text/live/file translation and never re-adds a cloud key. Validates FR-3, FR-10, FR-16.

- **SM-1:** E1 smoke matrix 5×5 passes with ≥95% JSON-valid per Model. Validates FR-3, FR-14.
- **SM-2:** Median utterance end-to-end <3s on M4 reference path. Validates FR-7, FR-8, FR-10.
- **SM-C1 (do not optimize):** Language breadth — do not chase 23-language parity at the cost of latency or offline purity. Counterbalances SM-1.

## 12. Open Questions

1. Confirm `flet==0.86.5` stays the pin at E1 kickoff, or re-pin to newer stable with changelog note?
2. File-mode scope: which containers must pass E2 (mp3/wav/m4a/mp4 minimum set)?
3. Source-language UX in live mode: auto-detect default vs explicit picker default?

## 13. Assumptions Index

- §4–§6 `[ASSUMPTION: solo/hobby rigor]` — light single-sentence UJs and memory-only sessions suffice; no multi-user/auth needs.
- §5 `[ASSUMPTION: PortAudio present post-setup]` — `brew install portaudio` + pip sounddevice unblocks capture; verified absent pre-E2.
- §7 `[ASSUMPTION: ggml-small default]` — whisper default model ggml-small.bin (≈2s ready); medium optional via flag.
- §8 `[ASSUMPTION: M4 reference hardware]` — latency/soak budgets measured on Apple-silicon Mac with Metal GPU.
