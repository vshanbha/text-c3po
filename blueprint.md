# Blueprint — text-c3po v2: Local-first Live Translator

Status: DRAFT · Owner: vshanbha · Date: 2026-09-08
Input document for the BMAD planning flow (bmad-product-brief / bmad-spec consume this).

## 1. Vision

Merge the text-c3po translator app with the capabilities proven in the
live-translate PoC, and cut all cloud dependencies:

- **Text mode**: type text → local model via Ollama → structured translation.
- **Live mode**: speech (system audio via BlackHole or microphone) →
  Automatic Speech Recognition via whisper.cpp → local Large Language Model
  → near-realtime translated captions.
- **File mode**: audio/video file → same Automatic Speech Recognition +
  translation pipeline.
- **Zero API keys, zero SaaS.** Everything runs locally on the Mac.
  After first-run model download, zero outbound network — loopback only.
- All three modes live in a **single Graphical User Interface** with
  buttons/toggles to switch between text, live, and file — no separate
  apps or terminal windows for the end user.

The earlier live-translate proof-of-concept validated the approach. All
product code lives in text-c3po/. Patterns worth porting are re-implemented
here; no cross-imports.

## 2. Locked decisions

| Decision | Choice |
|---|---|
| Cloud LLM | Removed entirely (no langchain-openai, no secrets.toml, no API keys) |
| GUI framework | **Flet** (Flutter-rendered, Apache-2.0; pin `flet==<exact>` in requirements until 1.0 ships) |
| LLM runtime | Ollama (OpenAI-compatible at 127.0.0.1:11434) |
| LLM integration | LangChain: `langchain-ollama` → `ChatOllama` (replaces `ChatOpenAI`) |
| Model selection | User picks any installed Ollama model at runtime (list from `/api/tags`); suggested default: `lfm2.5` (langchain-ollama pulls on first use if not present) |
| Automatic Speech Recognition | whisper.cpp `whisper-server` (Metal GPU), spawned as subprocess by the app on `127.0.0.1:9001`; `transcribe` only (no `-tr`); Large Language Model handles translation |
| Audio capture | **sounddevice** (PortAudio) — device picker: Built-in Microphone, BlackHole (if installed) |
| Structured output | Live mode: lightweight `{text, source_lang}` JSON; text mode: full `Translation` pydantic schema via `JsonOutputParser`; Ollama JSON format enforced |
| Network | After first-run model download: **zero outbound.** Loopback to Ollama `:11434` and whisper-server `:9001` only |
| Scope | 100% inside text-c3po/ |

### 2.1 Aspirational language list (data constant, v1)

The backend is model-agnostic. These 23 languages ship as the default list.
Quality per language is **model-dependent** — the eval harness (Epic 1 gate)
measures model × language combos and drives recommended defaults.

Each language carries a code for whisper's `-l` flag and a display name:

```json
[
  {"code": "af", "name": "Afrikaans"},
  {"code": "ar", "name": "Arabic"},
  {"code": "bn", "name": "Bangla"},
  {"code": "zh", "name": "Chinese"},
  {"code": "da", "name": "Danish"},
  {"code": "nl", "name": "Dutch"},
  {"code": "en", "name": "English"},
  {"code": "fr", "name": "French"},
  {"code": "de", "name": "German"},
  {"code": "el", "name": "Greek"},
  {"code": "gu", "name": "Gujarati"},
  {"code": "hi", "name": "Hindi"},
  {"code": "kn", "name": "Kannada"},
  {"code": "mr", "name": "Marathi"},
  {"code": "fa", "name": "Persian"},
  {"code": "pt", "name": "Portuguese"},
  {"code": "ru", "name": "Russian"},
  {"code": "es", "name": "Spanish"},
  {"code": "sv", "name": "Swedish"},
  {"code": "ta", "name": "Tamil"},
  {"code": "te", "name": "Telugu"},
  {"code": "ur", "name": "Urdu"},
  {"code": "vi", "name": "Vietnamese"}
]
```

## 3. Architecture

```
Flet desktop app (native window, no webserver)
├── Text mode  (button/toggle)
│     input text + target language + model picker
│     → ChatOllama (selected model) → JsonOutputParser
│     → formal / informal / commentary / origin_language
├── Live mode  (button/toggle)
│     sounddevice (Built-in Microphone | BlackHole) — device picker in UI
│     → int16 PCM stream → VAD + chunking
│       (ported from the proof-of-concept:
│        RMS silence threshold, flush on 2 silent frames or max-utterance)
│     → whisper-server POST /inference (16 kHz mono s16le WAV, transcribe only)
│     → ChatOllama translation (lightweight JSON: text + source_lang)
│     → live captions pane in Flet (background thread → UI update)
└── File mode  (button/toggle)
      audio/video file picker → same ASR + translate pipeline
```

**Dependencies (requirements.txt after rewrite):**
`flet==<pinned>`, `sounddevice`, `langchain`, `langchain-ollama`, `requests`

**External services (spawned by app or started before):**
- `ollama serve` (or desktop app) — model: `lfm2.5` (langchain-ollama pulls automatically if absent)
- `whisper-server -m models/ggml-small.bin --port 9001 --task transcribe` — spawned as subprocess by the app on launch; cleaned up on exit

## 4. Process — BMAD Method

Prereqs: Node ≥ 20.12, uv, ollama, whisper-cpp, ffmpeg.

| Step | Skill | Artifact |
|---|---|---|
| 0 | `npx bmad-method install` (in text-c3po/) | `_bmad/`, tool integration |
| 1 | `bmad-project-context` | text-c3po/AGENTS.md |
| 2 | `bmad-deep-recon` ×2 | model-quality eval across 23 languages; Flet + sounddevice feasibility on macOS/Linux/Windows |
| 3 | `bmad-product-brief` | brief.md (from this blueprint) |
| 4 | `bmad-prd` | prd.md — NFRs: <3s caption latency, offline, zero network |
| 5 | `bmad-ux` | DESIGN.md, EXPERIENCE.md |
| 6 | `bmad-architecture` | ARCHITECTURE-SPINE.md — locks §2 decisions or revises with evidence |
| 7 | `bmad-spec` per epic + Story Breakdown | specs/spec-<slug>/SPEC.md + stories.yaml |
| 8 | `bmad-sprint-planning` | sprint-status.yaml (readiness gate) |
| 9 | `bmad-build` per story | implementation records |
| 10 | `bmad-retrospective` per epic | retro report |

## 5. Epic draft

- **E1 — Flet desktop shell + local translation core**: Flet app shell,
  Ollama connectivity check + model picker (from `/api/tags`), ChatOllama
  + JSON structured output wired into text mode, 23-language picker with
  `{code, name}` data. Single UI with buttons/toggles for mode switching.
  *Gate: 5-language × 5-sentence smoke matrix — sample sentences translated
  by each installed Ollama model; scores recorded in `research.md`; harness
  repeatable so new Ollama models can be tested against all 23 languages
  anytime.*

- **E2 — Audio capture + Automatic Speech Recognition**: sounddevice device
  picker, port VAD/chunking from PoC (RMS silence + flush logic),
  whisper-server subprocess lifecycle (start on launch, health check,
  restart on crash, cleanup on exit), file upload / file picker path.

- **E3 — Live UI**: Flet live captions pane with utterance history and
  timestamps, start/stop toggle, source/target language pickers, device
  picker, status indicators (capture active, whisper latency, model),
  session state for captions list.

- **E4 — Ops, eval & polish**: setup.sh (Ollama install + model pull,
  BlackHole guidance), full 23-language eval harness (per-language scores
  in `research.md`), packaging (`flet build macos` or PyInstaller
  `--windowed` + `NSMicrophoneUsageDescription` for TCC mic permission),
  tests (VAD logic, JSON parser, whisper-server health), README/AGENTS.md
  refresh, delete all OpenAI code + secrets.toml.

## 6. Validation gates

1. Translation quality smoke harness (E1 exit) — 5 languages × 5 sentences per candidate model, recorded in `research.md`
2. Latency budget: Automatic Speech Recognition (~0.4s / 9s audio on M4) + Large Language Model first-token → <3s end-to-end per utterance
3. Live mode soak test: 5 min continuous speech via Flet app, no unbounded memory growth
4. Clean-machine setup: setup.sh from scratch ≤ 15 min
5. Zero outbound NFR: after model download, no outbound TCP/UDP except loopback

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Flet pre-1.0 API churn (0.x releases change interfaces) | Pin `flet==<exact>` in requirements; read changelog before any upgrade; Flet 1.0 roadmap targets 2026 |
| Small local models weak on many of the 23 languages (Indic, Persian, Afrikaans…) | Backend is model-agnostic — users swap freely; eval harness produces quality matrix; languages stay as aspirational |
| Ollama MoE bug: ≤ v0.17.0 fails on LFM MoE models (`missing tensor 'output_norm.weight'`) | Default to dense 1.2B; document Ollama ≥ v0.17.1 for MoE |
| whisper + Large Language Model both on Metal | Memory budget documented in architecture; ~6–8 GB combined on 16 GB Macs |
| macOS mic permissions (TCC) for packaged app | Info.plist must include `NSMicrophoneUsageDescription`; setup.sh tests and warns |
| BlackHole not installed | Device picker shows available sounddevice devices; file upload path does not need it; setup.sh guides user |

## 8. Out of scope (v1)

- Cloud providers / API-key auth (removed by design)
- Streaming token-level captioning (utterance-level flush only, as in PoC)
- Speaker diarization, translation memory, chat history persistence
- Browser-based streaming (no WebRTC, no Streamlit)
- Non-macOS packaging (Linux/Windows guides welcome, untested)
