---
title: text-c3po v2 — Local-first Live Translator
status: draft
created: 2026-09-08
updated: 2026-09-08
source: blueprint.md
---

# Product Brief — text-c3po v2

## Problem

text-c3po v1 is a Streamlit + OpenAI cloud translator. It needs API keys, network, and a browser, and it cannot do live speech. The live-translate PoC proves near-realtime speech → translate on macOS, but as terminal scripts. Users want one local desktop app for text, live speech, and file translation with zero keys and zero SaaS.

## Vision

Single Flet desktop app (native window, no webserver) with three modes behind buttons/toggles:

- Text: type → local Ollama model → formal / informal / commentary / origin_language JSON.
- Live: mic or system audio (BlackHole) → whisper.cpp transcribe → LLM translate → live captions.
- File: audio/video picker → same ASR + translate pipeline.

After first-run model download: zero outbound, loopback to Ollama :11434 and whisper-server :9001 only.

## Users

Local-first Mac users translating live meetings, videos, or text across 23 aspirational languages (model-dependent quality). No accounts, no keys, no cloud.

## Locked choices (from blueprint §2, verified 2026-09-08)

- GUI: Flet, pin `flet==0.86.5` exact (0.x churn).
- LLM: Ollama at 127.0.0.1:11434, `langchain-ollama` ChatOllama, user picks installed model at runtime from `/api/tags`, default lfm2.5 (present, 5.2GB). ollama 0.33.3 verified.
- ASR: whisper-server Metal GPU as app subprocess on 127.0.0.1:9001, transcribe only; LLM does translation. ggml-small.bin ready in ~2s.
- Capture: sounddevice PortAudio picker (Built-in Mic, BlackHole if present). Needs `brew install portaudio`.
- Scope: 100% in text-c3po/; live-translate/ is PoC, no cross-imports.

## Evidence this run

- Flet + sounddevice + Ollama + whisper-server feasible; see `../research/technical-flet-sounddevice-2026-09-08/research.md`.
- 5-sentence × German/French smoke on lfm2.5 + mistral: 20/20 JSON-valid. lfm2.5 consistent formal-Sie (~3.5s warm), mistral faster (~1.4s) but mixed register. See `../research/technical-model-quality-2026-09-08/research.md`.

## NFRs / gates

- <3s end-to-end per utterance (ASR ~0.4s/9s audio on M4 + LLM first token).
- 5-min live soak, no unbounded memory growth.
- Clean-machine setup.sh ≤15 min.
- Zero outbound after download (loopback only).
- E1 exit gate: 5-language × 5-sentence smoke matrix in research.md, repeatable for new models.

## Out of scope (v1)

Cloud providers, token-streaming captions (utterance flush only), diarization, translation memory, history persistence, WebRTC/browser streaming, non-macOS packaging.

## Epics (draft)

E1 Flet shell + local translation core. E2 Audio capture + ASR lifecycle + file path. E3 Live captions UI + session state. E4 Ops, 23-lang eval, packaging (`flet build macos` or PyInstaller + NSMicrophoneUsageDescription), tests, README refresh, delete OpenAI code + secrets.toml.
