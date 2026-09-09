# Deep Recon — Flet + sounddevice feasibility (technical)

Date: 2026-09-08 · Models verified this run · Target: text-c3po v2 (blueprint §2, §7)

Decision: Flet + sounddevice + Ollama + whisper-server stack is feasible on this Mac. Only missing piece is PortAudio/sounddevice install.

## Evidence (verified 2026-09-08)

- Flet latest stable 0.86.5 (`pip index versions flet`); 1.0.0.dev0 pre-release exists. Pre-1.0 churn confirmed. Pin `flet==0.86.5` exact, never `>=`. Python 3.12.10.
- sounddevice currently absent as expected: `brew list portaudio` → No such keg; `python -c "import sounddevice"` → ModuleNotFoundError. Dry-run resolves: cffi-2.1.1, pycparser-3.0, sounddevice-0.5.6. Fix: `brew install portaudio && pip install sounddevice`.
- Ollama 0.33.3 running at 127.0.0.1:11434. Models: mistral:latest (7.2B Q4_K_M), lfm2.5:latest, gemma4:e4b-mlx, qwen3.5:9b-mlx, minicpm-v4.6:latest.
- whisper-server at /opt/homebrew/bin/whisper-server (ggml 0.23.0, BLAS backend). Models present in live-translate/models/: ggml-small.bin (488MB), ggml-medium.bin (1.5GB). Test start on port 9002 with ggml-small.bin ready in ~2s, GET /health → {"status":"ok"}.
- No text-c3po/models/ yet; E2 must create it or reuse live-translate model path.

## Implications for architecture

- Lock §2 decisions stand: Flet pinned, sounddevice picker (Built-in Mic + BlackHole), whisper-server subprocess on :9001 transcribe-only, ChatOllama via /api/tags.
- E2 must handle: BlackHole absent → show only available devices; file-upload path independent of capture device.
- E4 packaging must include NSMicrophoneUsageDescription for TCC.

## Open questions

- Linux/Windows Flet + sounddevice smoke untested (blueprint §8 out of scope for v1, welcome as guides).
- whisper + LLM combined Metal memory budget (~6-8GB on 16GB Macs) needs soak-test confirmation in E3/E4.
