<!-- bmad:context -->
<!-- Verified 2026-09-09 against E1-done tree. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## text-c3po

Local-first desktop translator per blueprint.md. Flet GUI plus Ollama ChatOllama plus whisper-server transcribe-only. Planning lives in `_bmad-output/planning-artifacts/`, implementation in `_bmad-output/implementation-artifacts/`, long-term knowledge in `docs/`.

## Policy

- Never commit secrets or any API key; v2 removes cloud LLM by design.
- Keep all product code inside `src/text_c3po/` (src layout, valid package name); patterns from the earlier live-translate proof-of-concept are re-implemented here, never imported.
- After first-run model download keep zero outbound; loopback to 127.0.0.1:11434 and 127.0.0.1:9001 only.

## Where things are

- Product direction: `blueprint.md`, consumed via bmad-product-brief and bmad-spec.
- App entry: `src/text_c3po/app.py` (Flet; Streamlit removed in E1). All run commands assume the repo root with `PYTHONPATH=src`.
- Long-term knowledge: `docs/`; BMAD outputs in `_bmad-output/`.

## Running and verifying

- Use prereqs Node >= 20.12, uv, ollama, whisper-cpp, ffmpeg; verified node v24.11.1, uv 0.12.10, ollama 0.33.3 with lfm2.5 present.
- Work from the repo root: the app with `PYTHONPATH=src python -m text_c3po.app` (needs `ollama serve`); fast checks with `pytest` (unit only, integration deselected; `pythonpath=src` is wired in pyproject).
- Ollama-backed tests are manual-only and serial (`pytest -m integration`, lfm2.5-first); the eval gate is `PYTHONPATH=src python -m text_c3po.services.eval_harness --models lfm2.5:latest`. Never run Ollama tests in CI.
- No lint or typecheck configured in this repo.

### Browser testing (BrowserOS neo)

Flet apps run as native desktop windows by default. To test in a browser via BrowserOS neo:

1. Start the app as a web server: `FLET_SERVER_PORT=8555 PYTHONPATH=src uv run python -m text_c3po.app`
2. Open BrowserOS neo, navigate to `http://localhost:8555`
3. The Flet web UI loads in the browser; interact via snapshot/act as with any web page

Notes:
- The desktop Flet client also launches automatically (connected to the same port). Kill it with `pkill flet-desktop` if it gets in the way.
- The server binds to localhost only; no external access.
- If the port is stale from a prior run, wait a few seconds for `TIME_WAIT` to clear or pick a different port.

## Conventions that differ from defaults

- Pin `flet==exact` in `requirements.txt` until 1.0 ships; read the changelog before any upgrade.
- Talk to Ollama via langchain-ollama ChatOllama with JSON format enforced; list runtime models from `/api/tags`, suggested default lfm2.5.
- Run translation with thinking disabled (`reasoning=False` in the service): the reasoning trace costs ~10s per call with zero translation gain. Do not override `num_ctx` — the server default applies (lfm2.5 loads at 128K fully on GPU here); pinning a small value forces a model reload per call. Never add either back without re-running the gate.
- The translation contract is language names ("German"), never picker codes ("de"); UI layers convert via `languages.name_for_code` at call time so manual use matches the gated test path.
- Ship the 23-language code and name constant from blueprint section 2.1; keep the backend model-agnostic.
- Spawn `whisper-server` as a subprocess on 127.0.0.1:9001 with transcribe only; do the translation in the LLM.
- Capture audio via sounddevice with a picker for Built-in Microphone and BlackHole.

## Known pitfalls

- Ollama at or below 0.17.0 fails on LFM MoE models with missing tensor output_norm.weight; require Ollama at or above 0.17.1.
- Packaged macOS app without NSMicrophoneUsageDescription fails mic permission under TCC.
- BlackHole may be absent; keep the file-upload path working without it and list only available sounddevice devices.

<!-- /bmad:context -->
