# Addendum — text-c3po v2 PRD overflow

## A. Mechanism decisions (not PRD normative)

- LLM integration: `langchain-ollama` ChatOllama, JSON format enforced; text mode full Translation schema via JsonOutputParser; live/file lightweight `{text, source_lang}` JSON.
- Model discovery: runtime list from Ollama `/api/tags`; suggested default lfm2.5 (present, 5.2GB, verified ollama 0.33.3).
- ASR: whisper.cpp `whisper-server -m models/ggml-small.bin --port 9001 --task transcribe`, spawned as app subprocess; LLM does translation, never `-tr`.
- VAD port: live-translate/transcribe.py RMS silence threshold, flush on 2 silent frames or max-utterance.
- Deps post-rewrite: `flet==0.86.5`, `sounddevice`, `langchain`, `langchain-ollama`, `requests`; plus `brew install portaudio`, ffmpeg, whisper-cpp, Node ≥ 20.12, uv.

## B. Evidence pointers

- Flet 0.86.5 latest stable, 1.0.0.dev0 prerelease; sounddevice absent pre-E2 (no PortAudio keg); whisper-server ggml 0.23.0 + ggml-small ready ~2s; Ollama models present (mistral 7.2B, lfm2.5, gemma4, qwen3.5, minicpm). Source: technical-flet-sounddevice research.
- 5-sentence × German/French smoke: 20/20 JSON-valid; lfm2.5 formal-Sie consistent ~3.5s warm, mistral ~1.4s mixed register. Source: technical-model-quality research.

## C. Options considered

- whisper `-tr` translate vs transcribe-only + LLM: chose transcribe-only (LLM owns translation quality + JSON contract).
- `flet build macos` vs PyInstaller `--windowed`: deferred to E4 with TCC `NSMicrophoneUsageDescription` requirement either way.
- Dense 1.2B default vs MoE: default dense; Ollama ≥ 0.17.1 required for LFM MoE (`output_norm.weight` bug ≤ 0.17.0).

## D. Risks carried from blueprint §7

Flet 0.x churn (pin + changelog gate); weak small-model quality on Indic/Persian/Afrikaans (aspirational list + eval matrix); whisper+LLM Metal memory ~6–8GB on 16GB Macs (soak test); BlackHole absent (available-devices picker + file path unaffected).
