# 🤖 Text C-3PO — Local-first Translator (v2)

Flet desktop app. Type text → local Ollama model → structured translation
(formal / informal / commentary / detected language). No API keys, no cloud:
after the first model download, everything runs on loopback.

Inspired by the Star Wars character C-3PO. Product direction lives in
[blueprint.md](blueprint.md); planning artifacts in `_bmad-output/`.

## Prerequisites

All paths below need these installed first:

- **Python 3.12** (check with `python3 --version`) including **pip**
  (`python3 -m pip --version`)
- **Ollama** ([ollama.com](https://ollama.com)) with at least one model
  pulled: `ollama pull lfm2.5` (the default; any installed model works via
  the in-app picker)

## Run

With plain pip:

```sh
pip install -r requirements.txt   # flet==0.86.5 (pinned), langchain-ollama
ollama serve                      # or the Ollama desktop app
python text-c3po/app.py           # use python3 if plain python is missing
```

Prefer `uv` (no activation step — it auto-uses the project `.venv`):

```sh
uv venv && uv pip install -r requirements.txt pytest   # one-time setup
uv run python text-c3po/app.py
```

Live speech and file modes (whisper-server + sounddevice) land in E2/E3;
their placeholders are visible in the UI.

## Testing

- Fast unit checks (no Ollama, default): `pytest` — or `uv run pytest`
- Manual Ollama-backed tests (opt-in, never CI): `pytest -m integration`
- E1 translation gate, repeatable (serial, lfm2.5-first):  
  `python text-c3po/services/eval_harness.py --models lfm2.5:latest`  
  (via uv: `uv run python text-c3po/services/eval_harness.py --models lfm2.5:latest`)
  Scores append to the model-quality `research.md` under
  `_bmad-output/planning-artifacts/research/`. Full policy (serial-only,
  memory-hog exclusions) is documented in `pyproject.toml` and the harness
  docstring — CI runs unit tests only, by design.

## Layout

- `text-c3po/` — product code: `app.py` (Flet entry), `ui/`, `services/`
  (translation + eval harness), `runtimes/` (Ollama client), `languages.py`
  (23-language constant)
- Provenance: an earlier live-translate proof-of-concept validated the
  speech-to-translation pipeline; its patterns are re-implemented here,
  never imported
- `_bmad-output/` — brief, PRD, UX, architecture spine, epic specs, eval
  research, sprint status, E1 retrospective
- `docs/` — MkDocs Material site published to GitHub Pages (sources are
  symlinks to the repo markdown; regenerate with `mkdocs build`, or
  `uv run --no-project --with mkdocs --with mkdocs-material mkdocs build`)
