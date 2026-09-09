# 🤖 Text C-3PO — Local-first Translator (v2)

Flet desktop app. Type text → local Ollama model → structured translation
(formal / informal / commentary / detected language). No API keys, no cloud:
after the first model download, everything runs on loopback.

Inspired by the Star Wars character C-3PO. Product direction lives in
`blueprint.md`; planning artifacts in `_bmad-output/`.

## Run

Prereqs: Python 3.12, [Ollama](https://ollama.com) with a model pulled
(`ollama pull lfm2.5` — the default; any installed model works via the
in-app picker).

```sh
pip install -r requirements.txt   # flet==0.86.5 (pinned), langchain-ollama
ollama serve                      # or the Ollama desktop app
python text-c3po/app.py
```

Live speech and file modes (whisper-server + sounddevice) land in E2/E3;
their placeholders are visible in the UI.

## Testing

- Fast unit checks (no Ollama, default): `pytest`
- Manual Ollama-backed tests (opt-in, never CI): `pytest -m integration`
- E1 translation gate, repeatable (serial, lfm2.5-first):  
  `python text-c3po/services/eval_harness.py --models lfm2.5:latest`  
  Scores append to the model-quality `research.md` under
  `_bmad-output/planning-artifacts/research/`. Full policy (serial-only,
  memory-hog exclusions) is documented in `pyproject.toml` and the harness
  docstring — CI runs unit tests only, by design.

## Layout

- `text-c3po/` — product code: `app.py` (Flet entry), `ui/`, `services/`
  (translation + eval harness), `runtimes/` (Ollama client), `languages.py`
  (23-language constant)
- `live-translate/` — PoC only; patterns are re-implemented, never imported
- `_bmad-output/` — brief, PRD, UX, architecture spine, epic specs, eval
  research, sprint status, E1 retrospective
- `docs/` — MkDocs Material site published to GitHub Pages (sources are
  symlinks to the repo markdown; regenerate with `mkdocs build`, or
  `uv run --no-project --with mkdocs --with mkdocs-material mkdocs build`)
