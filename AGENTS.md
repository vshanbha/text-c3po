<!-- bmad:context -->
<!-- Verified 2026-10-08 against ornith-default tree (f4ea3c5). Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## text-c3po

Local-first desktop translator per blueprint.md. Flet GUI plus Ollama ChatOllama plus whisper-server transcribe-only. Planning and implementation live in the v7 initiative/ticket tree `_bmad-output/initiative-text-c3po/` (BMAD v7 migration 2026-11-24; v6 `epics.md`/`sprint-status.yaml` archived under `archive-v6/`), long-term knowledge in `docs/`.

## Policy

- Never commit secrets or any API key; v2 removes cloud LLM by design.
- Keep all product code inside `src/text_c3po/` (src layout, valid package name); patterns from the earlier live-translate proof-of-concept are re-implemented here, never imported.
- After first-run model download keep zero outbound; loopback to 127.0.0.1:11434 and 127.0.0.1:9001 only.

## Where things are

- Product direction: `blueprint.md`, consumed through the BMAD v7 flow (`bmad-agent-po`/Sofia turns direction into initiative tickets; v6 `bmad-product-brief`/`bmad-spec` skills were retired in the migration).
- App entry: `src/text_c3po/app.py` (Flet; Streamlit removed in E1). All run commands assume the repo root with `PYTHONPATH=src`.
- Long-term knowledge: `docs/`; BMAD outputs in `_bmad-output/`.

## Running and verifying

- Use prereqs Node >= 20.12, uv, ollama, whisper-cpp, ffmpeg; verified node v24.11.1, uv 0.12.10, ollama 0.40.1 with lfm3 present (default; ornith-1.5:9b also installed).
- Work from the repo root: the app with `PYTHONPATH=src python -m text_c3po.app` (needs `ollama serve`); fast checks with `pytest` (unit only, integration deselected; `pythonpath=src` is wired in pyproject).
- Ollama-backed tests are manual-only and serial (`pytest -m integration`, lfm3-first); the eval gate is `PYTHONPATH=src python -m text_c3po.services.eval_harness --models lfm3`. Never run Ollama tests in CI.
- Human-run checklist lives in `TEST-PLAN.md` (windows, dialogs, snackbars, hardware, subprocess timing, real speech) — run it top to bottom after any epic lands.
- No lint or typecheck configured in this repo.

## Quality pipeline (owner-mandated order — every change follows this)

architecture/design → test-first unit tests → code → run unit & other
tests → fresh-context review → **loop: code, unit tests and review
continue until all tests pass and review comments are reasonably
addressed** → **eval harness gate** → human review.

Nothing may be flagged for human testing or review until the eval
harness passes. The eval run, after every major change:

1. **Conformance:** `PYTHONPATH=src python -m text_c3po.services.eval_harness --models lfm3,ornith-1.5:9b` (5×5; `--languages all` for breadth) — JSON contract only, never a quality verdict.
2. **Language consistency:** `formal` AND `informal` must render in the target language across the matrix (wired by the informal-language ticket — the informal field previously had zero automated coverage).
3. **Probes:** `probe_echo` (script rendering), `probe_collapse` (long-input completeness, Spanish + the explicit German-long ladder check).
4. **Quality judge:** `probe_quality_pairs` scored by `tev1` via Ollama `/v1/systemone` (tier-1, milliseconds, local; agent/human tier-2 on low margin — see `research/quality-eval-2026-11-23/gate-report.md`).

Unit tests (`pytest`) stay structural: they cannot catch NLP issues by
design, which is why the eval harness is a separate mandatory gate.
`TEST-PLAN.md` rows are the final human layer and never precede a green
eval run.

### Browser testing (BrowserOS neo)

Flet apps run as native desktop windows by default. To test in a browser via BrowserOS neo:

1. Start the app as a web server: `FLET_FORCE_WEB_SERVER=true FLET_SERVER_PORT=8555 PYTHONPATH=src uv run python -m text_c3po.app`
2. Open BrowserOS neo, navigate to `http://localhost:8555`
3. The Flet web UI loads in the browser; interact via snapshot/act as with any web page

Notes:
- `FLET_FORCE_WEB_SERVER=true` is what switches `ft.run` from the native window to a real HTTP site (verified in flet 0.86.5 source); `FLET_SERVER_PORT` alone only moves the desktop client's port and serves nothing to browsers.
- No desktop client launches in this mode; nothing to kill.
- The server binds to localhost only; no external access.
- If the port is stale from a prior run, wait a few seconds for `TIME_WAIT` to clear or pick a different port.

## Conventions that differ from defaults

- Pin `flet==exact` in `requirements.txt` until 1.0 ships; read the changelog before any upgrade.
- Talk to Ollama via langchain-ollama ChatOllama with JSON format enforced; list runtime models from `/api/tags`, suggested default lfm3 (1.7 GB — switched from ornith-1.5:9b 6.6 GB on 2026-11-23 for VRAM reasons; lfm3 passed the 5x5 gate 25/25).
- Run translation with thinking disabled on the fast path (`reasoning=False`, rungs 1–2 of the ladder): the reasoning trace costs ~10–18s per call with zero translation gain on short inputs. The hybrid ladder in `translation.py` enables thinking ONLY for rung 3 (long-input partial fallback, 360s per-call timeout). Do not override `num_ctx` — the server default applies; pinning a smaller value forces a model reload whenever it differs from the loaded context. Never change either policy without re-running the gate.
- The translation contract is language names ("German"), never picker codes ("de"); UI layers convert via `languages.name_for_code` at call time so manual use matches the gated test path.
- Ship the 23-language code and name constant from blueprint section 2.1; keep the backend model-agnostic.
- Spawn `whisper-server` as a subprocess on 127.0.0.1:9001 with transcribe only; do the translation in the LLM.
- Capture audio via ffmpeg avfoundation with a picker for Built-in Microphone and BlackHole.

## Known pitfalls

- Ollama at or below 0.17.0 fails on LFM MoE models with missing tensor output_norm.weight; require Ollama at or above 0.17.1.
- Packaged macOS app without NSMicrophoneUsageDescription fails mic permission under TCC.
- BlackHole may be absent; keep the file-upload path working without it and list only available ffmpeg/avfoundation input devices.

<!-- /bmad:context -->
