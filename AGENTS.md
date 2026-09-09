<!-- bmad:context -->
<!-- Verified 2026-09-09 against E1-done tree. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## text-c3po

Local-first desktop translator per blueprint.md. Flet GUI plus Ollama ChatOllama plus whisper-server transcribe-only. Planning lives in `_bmad-output/planning-artifacts/`, implementation in `_bmad-output/implementation-artifacts/`, long-term knowledge in `docs/`.

## Policy

- Never commit secrets or any API key; v2 removes cloud LLM by design.
- Keep all product code inside `text-c3po/`; `live-translate/` is PoC only, re-implement patterns, no cross-imports.
- After first-run model download keep zero outbound; loopback to 127.0.0.1:11434 and 127.0.0.1:9001 only.

## Where things are

- Product direction: `blueprint.md`, consumed via bmad-product-brief and bmad-spec.
- App entry: `text-c3po/app.py` (Flet; Streamlit removed in E1).
- Long-term knowledge: `docs/`; BMAD outputs in `_bmad-output/`.

## Running and verifying

- Use prereqs Node >= 20.12, uv, ollama, whisper-cpp, ffmpeg; verified node v24.11.1, uv 0.12.10, ollama 0.33.3 with lfm2.5 present.
- Run the app with `python text-c3po/app.py` (needs `ollama serve`); fast checks with `pytest` (unit only, integration deselected).
- Ollama-backed tests are manual-only and serial (`pytest -m integration`, lfm2.5-first); the eval gate is `python text-c3po/services/eval_harness.py --models lfm2.5:latest`. Never run Ollama tests in CI.
- No lint or typecheck configured in this repo.

## Conventions that differ from defaults

- Pin `flet==exact` in `requirements.txt` until 1.0 ships; read the changelog before any upgrade.
- Talk to Ollama via langchain-ollama ChatOllama with JSON format enforced; list runtime models from `/api/tags`, suggested default lfm2.5.
- The translation contract is language names ("German"), never picker codes ("de"); UI layers convert via `languages.name_for_code` at call time so manual use matches the gated test path.
- Ship the 23-language code and name constant from blueprint section 2.1; keep the backend model-agnostic.
- Spawn `whisper-server` as a subprocess on 127.0.0.1:9001 with transcribe only; do the translation in the LLM.
- Capture audio via sounddevice with a picker for Built-in Microphone and BlackHole.

## Known pitfalls

- Ollama at or below 0.17.0 fails on LFM MoE models with missing tensor output_norm.weight; require Ollama at or above 0.17.1.
- Packaged macOS app without NSMicrophoneUsageDescription fails mic permission under TCC.
- BlackHole may be absent; keep the file-upload path working without it and list only available sounddevice devices.

<!-- /bmad:context -->
